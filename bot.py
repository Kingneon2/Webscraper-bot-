import os
import threading
import requests
from bs4 import BeautifulSoup
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# --- Flask for health check ---
app = Flask(__name__)

@app.route('/')
def health():
    return "Bot is running!", 200

# --- Telegram bot ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send /scrape followed by a URL")

async def scrape(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /scrape https://example.com")
        return
    url = context.args[0]
    await update.message.reply_text(f"Scraping {url}...")
    try:
        response = requests.get(url, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.title.string if soup.title else "No title found"
        await update.message.reply_text(f"Page title: {title}")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)[:200]}")

def main():
    # Start Flask in background thread (for Render health check)
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8000, debug=False, use_reloader=False)).start()
    
    # Build bot application
    bot_app = Application.builder().token(TELEGRAM_TOKEN).connect_timeout(60).read_timeout(60).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("scrape", scrape))
    
    print("Bot started. Polling for updates...")
    bot_app.run_polling()

if __name__ == "__main__":
    main()
