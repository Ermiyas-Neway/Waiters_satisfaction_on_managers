import logging
import io
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    PollAnswerHandler,
    ContextTypes,
)
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Google Sheets setup
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SPREADSHEET_ID = "1W1HlZ4Pw377pekVlNWJu9wTXCV6zgqE3XWdt7OyixPQ"  # Replace with your Google Sheet ID
RANGE_NAME = "Sheet1!A:D"  # Columns: Username, Branch, Answer, Timestamp

# List of 30 branches (customize as needed)
BRANCHES = [f"Branch {i}" for i in range(1, 31)]  # Replace with actual branch names

# Poll question and options in Amharic
POLL_QUESTION = "በሚመሯችሁ ኃላፊዎች ምን ያህል ደስተኛ ነህ/ሽ"
POLL_OPTIONS = [
    "በጣም ደስተኛ ነኝ",
    "ደስተኛ ነኝ",
    "ደህና ነኝ",
    "ደስተኛ አይደለሁም",
]

def get_sheets_service():
    """Authenticate and return Google Sheets API service."""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('sheets', 'v4', credentials=creds)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the poll by showing branch selection."""
    keyboard = [
        [InlineKeyboardButton(branch, callback_data=f"branch_{branch}")]
        for branch in BRANCHES
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Please select your branch:", reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle branch selection and send the poll."""
    query = update.callback_query
    await query.answer()
    
    branch = query.data.replace("branch_", "")
    user = query.from_user
    username = user.username or str(user.id)  # Fallback to user ID if no username
    
    # Store temporary data in context
    context.user_data["branch"] = branch
    context.user_data["username"] = username
    
    # Send the poll
    message = await query.message.reply_poll(
        question=POLL_QUESTION,
        options=POLL_OPTIONS,
        is_anonymous=False,  # Non-anonymous to capture usernames
        allows_multiple_answers=False,
    )
    
    # Store poll ID for response tracking
    context.user_data["poll_id"] = message.poll.id

async def receive_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle poll responses and append to Google Sheets."""
    answer = update.poll_answer
    poll_id = answer.poll_id
    user_id = answer.user.id
    username = answer.user.username or str(user_id)
    
    if poll_id in context.user_data.get("poll_id", {}):
        branch = context.user_data.get("branch")
        selected_option_ids = answer.option_ids
        
        if selected_option_ids:
            selected_answer = POLL_OPTIONS[selected_option_ids[0]]
            
            # Append response to Google Sheets
            service = get_sheets_service()
            values = [[username, branch, selected_answer, str(update.effective_message.date)]]
            body = {'values': values}
            try:
                service.spreadsheets().values().append(
                    spreadsheetId=SPREADSHEET_ID,
                    range=RANGE_NAME,
                    valueInputOption="RAW",
                    insertDataOption="INSERT_ROWS",
                    body=body
                ).execute()
                logger.info(f"Appended response: {username}, {branch}, {selected_answer}")
            except Exception as e:
                logger.error(f"Error appending response: {e}")
        
        # Clear user data
        context.user_data.clear()

def main():
    """Run the bot."""
    # Replace with your bot token
    application = Application.builder().token("7760430928:AAFgCHYxnyLC3TKbJawWSPqfsb5KX5uig2g").build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_callback, pattern="^branch_"))
    application.add_handler(PollAnswerHandler(receive_poll_answer))
    
    # Start the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
