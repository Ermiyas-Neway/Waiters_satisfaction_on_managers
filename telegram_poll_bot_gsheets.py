import os
import logging
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    PollAnswerHandler,
    ContextTypes,
)
from telegram.error import Conflict
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from datetime import datetime, timezone, timedelta

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Google Sheets API setup
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SPREADSHEET_ID = "1W1HlZ4Pw377pekVlNWJu9wTXCV6zgqE3XWdt7OyixPQ"  # Replace with your Google Sheet ID

def get_sheets_service():
    """Authenticate and return Google Sheets API service."""
    creds = None
    token_path = "token.json"
    credentials_path = "credentials.json"

    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        except Exception as e:
            logger.error(f"Error loading token.json: {e}")

    if creds and creds.valid:
        return build("sheets", "v4", credentials=creds)

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open(token_path, "w") as token:
                token.write(creds.to_json())
            return build("sheets", "v4", credentials=creds)
        except Exception as e:
            logger.error(f"Error refreshing token: {e}")

    raise RuntimeError(
        "No valid credentials available. Ensure credentials.json and token.json "
        "are in the src directory."
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message with branch selection buttons when /start is issued."""
    branches = ['Adama German', 'Addisu Gebya', 'Airport','Betel Adebaby','Betel  Bicha Foq','Bishoftu',
               'Bole DH', 'Bulbula Medhanialem', 'Bole Oromiya', 'Bole Medhanialem',
               'Bulbula 93', 'ECA', 'Entoto Park', 'Grand Palace', 'Gulele Medhaniyalem',
               'Gurdshola', 'Imperial', 'Jemo', 'Kality Sheger', 'Kera', 'Lancha',
               'Lebu', 'Megenaga', 'Mexico', 'Old Airport', 'Sarbet', 'Semen Hotel',
               'Torhailoch', 'Semit Figa']  # 30 branches
    keyboard = [
        [InlineKeyboardButton(branch, callback_data=branch)] for branch in branches
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Please select your branch:", reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle branch selection and send a poll."""
    query = update.callback_query
    await query.answer()
    branch = query.data
    context.user_data["branch"] = branch

    question = "በሚመሯችሁ ኃላፊዎች መንገድ ምን ያፈ ደስተኛ ነህ/ሽ"
    options = [
        "በጣም ደስተኛ ነ",
        "ደስተኛ ነ",
        "ደህና ነ",
        "ደስ�ተ አይደለም",
    ]
    poll = await query.message.reply_poll(
        question=question,
        options=options,
        is_anonymous=True,
        allows_multiple_answers=False,
    )
    # Store poll options and creation time
    context.bot_data[poll.poll.id] = {
        "options": {i: option for i, option in enumerate(options)},
        "created_at": datetime.now(timezone(timedelta(hours=3))).strftime("%Y-%m-%d %H:%M:%S")
    }

async def receive_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle poll answers and append to Google Sheet."""
    answer = update.poll_answer
    poll_id = answer.poll_id
    user = answer.user
    option_ids = answer.option_ids
    branch = context.user_data.get("branch", "Unknown")

    username = user.username if user else "Anonymous"
    selected_answer = context.bot_data.get(poll_id, {}).get("options", {}).get(option_ids[0], "Pending")
    
    # Use poll creation time or current time in EAT
    timestamp = context.bot_data.get(poll_id, {}).get("created_at")
    if not timestamp:
        timestamp = datetime.now(timezone(timedelta(hours=3))).strftime("%Y-%m-%d %H:%M:%S")

    # Append to Google Sheet
    try:
        service = get_sheets_service()
        values = [[username, branch, selected_answer, timestamp]]
        body = {"values": values}
        result = (
            service.spreadsheets()
            .values()
            .append(
                spreadsheetId=SPREADSHEET_ID,
                range="Sheet1!A:D",
                valueInputOption="RAW",
                body=body,
            )
            .execute()
        )
        logger.info(f"Appended data to Google Sheet: {values}")
    except Exception as e:
        logger.error(f"Error appending to Google Sheet: {e}")

def main() -> None:
    """Run the bot with retry logic for conflicts."""
    token = os.getenv("YOUR_BOT_TOKEN")
    if not token:
        raise RuntimeError("Bot token not found in environment variable YOUR_BOT_TOKEN")
    
    max_retries = 3
    retry_delay = 10  # Seconds between retries

    for attempt in range(max_retries):
        try:
            application = Application.builder().token(token).build()

            application.add_handler(CommandHandler("start", start))
            application.add_handler(CallbackQueryHandler(button_callback))
            application.add_handler(PollAnswerHandler(receive_poll_answer))

            application.run_polling(allowed_updates=Update.ALL_TYPES)
            break  # Exit loop if polling starts successfully
        except Conflict as e:
            logger.error(f"Conflict detected: {e}. Retrying in {retry_delay} seconds... (Attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                logger.error("Max retries reached. Exiting.")
                raise

if __name__ == "__main__":
    main()
