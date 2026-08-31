import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

# --- Build the Telegram Application ---
bot_app = Application.builder().token(TELEGRAM_TOKEN).build()

# --- Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send /scrape followed by a URL")

async def scrape(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /scrape https://example.com")
        return
    url = context.args[0]
    await update.message.reply_text(f"Scraping {url}...")
    try:
        # Use BeautifulSoup instead of Playwright to avoid browser issues
        import requests
        from bs4 import BeautifulSoup
        response = requests.get(url, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.title.string if soup.title else "No title found"
        await update.message.reply_text(f"Page title: {title}")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)[:200]}")

# Register handlers
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("scrape", scrape))

# --- Flask Webhook Route ---
@app.route('/webhook', methods=['POST'])
def webhook():
    # Get the update data
    json_data = request.get_json()
    if not json_data:
        return "Bad request", 400
    
    # Process the update asynchronously
    update = Update.de_json(json_data, bot_app.bot)
    # Run the update processing in the same event loop
    asyncio.run(bot_app.process_update(update))
    return "OK", 200

@app.route('/')
def health():
    return "Bot is running!", 200

# --- Main ---
def main():
    # Set webhook on startup
    webhook_url = os.environ.get("RENDER_EXTERNAL_URL") + "/webhook"
    bot_app.bot.set_webhook(webhook_url)
    print(f"Webhook set to: {webhook_url}")
    # Start Flask server (gunicorn will run this)
    app.run(host='0.0.0.0', port=8000)

if __name__ == "__main__":
    main()
