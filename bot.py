import os
import threading
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from playwright.async_api import async_playwright

app = Flask(__name__)

@app.route('/')
def health():
    return "Bot is running!", 200

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
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=30000)
            title = await page.title()
            await browser.close()
        await update.message.reply_text(f"Page title: {title}")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)[:200]}")

def main():
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8000, debug=False, use_reloader=False)).start()
    
    bot_app = Application.builder().token(TELEGRAM_TOKEN).connect_timeout(60).read_timeout(60).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("scrape", scrape))
    print("Bot started with 60s timeout...")
    bot_app.run_polling()

if __name__ == "__main__":
    main()
