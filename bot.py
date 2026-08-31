import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, Dispatcher
from playwright.async_api import async_playwright

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

@app.route('/webhook', methods=['POST'])
async def webhook():
    update = Update.de_json(request.get_json(), bot_app.bot)
    await dispatcher.process_update(update)
    return "OK", 200

@app.route('/')
def health():
    return "Bot is running!", 200

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send /scrape followed by a URL")

async def scrape(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /scrape https://example.com")
        return
    url = context.args[0]
    await update.message.reply_text(f"Scraping {url}...")
    try:
        # Force Playwright to use the correct browser path
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                executable_path=os.environ.get("PLAYWRIGHT_CHROME_EXECUTABLE_PATH")
            )
            page = await browser.new_page()
            await page.goto(url, timeout=30000)
            title = await page.title()
            await browser.close()
        await update.message.reply_text(f"Page title: {title}")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)[:200]}")

# Create bot app and dispatcher
bot_app = Application.builder().token(TELEGRAM_TOKEN).build()
dispatcher = Dispatcher(bot_app.bot, None)
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("scrape", scrape))

def main():
    # Set webhook
    webhook_url = os.environ.get("RENDER_EXTERNAL_URL") + "/webhook"
    bot_app.bot.set_webhook(webhook_url)
    print(f"Webhook set to: {webhook_url}")
    app.run(host='0.0.0.0', port=8000)

if __name__ == "__main__":
    main()
