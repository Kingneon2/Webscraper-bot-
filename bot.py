import os
import asyncio
import threading
import requests
from bs4 import BeautifulSoup
import trafilatura
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# --- Flask app ---
app = Flask(__name__)
PORT = int(os.environ.get("PORT", 10000))

@app.route('/')
def health():
    return "Bot is running!", 200

# --- Telegram setup ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not set")

bot_app = Application.builder().token(TELEGRAM_TOKEN).build()

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 **Smart Scraper Bot**\n\n"
        "Send /scrape https://example.com\n\n"
        "I'll return:\n"
        "• Page title\n"
        "• Meta description\n"
        "• First 5 links\n"
        "• First 3 images\n"
        "• Clean article text (no ads/nav/sidebars)\n\n"
        "⚡ Fast & lightweight — runs on Render free tier."
    )

async def scrape(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /scrape https://example.com")
        return

    url = context.args[0]
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    await update.message.reply_text(f"🔍 Scraping {url}...")

    try:
        # --- Fetch the page ---
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        html = response.text

        # --- BeautifulSoup parsing ---
        soup = BeautifulSoup(html, 'html.parser')

        # Title
        title = soup.title.string.strip() if soup.title else "No title found"

        # Meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        description = meta_desc.get('content', 'No description') if meta_desc else "No description"

        # Links (first 5)
        links = []
        for a in soup.find_all('a', href=True)[:5]:
            href = a['href']
            if href.startswith('http'):
                links.append(href)
            elif href.startswith('/'):
                links.append(url.rstrip('/') + href)
            else:
                links.append(url.rstrip('/') + '/' + href)

        # Images (first 3)
        images = []
        for img in soup.find_all('img', src=True)[:3]:
            src = img['src']
            if src.startswith('http'):
                images.append(src)
            elif src.startswith('/'):
                images.append(url.rstrip('/') + src)
            else:
                images.append(url.rstrip('/') + '/' + src)

        # --- Trafilatura clean text extraction ---
        clean_text = trafilatura.extract(html, include_comments=False, include_tables=False)
        if clean_text:
            clean_preview = clean_text[:600] + "..." if len(clean_text) > 600 else clean_text
        else:
            clean_preview = "No clean text extracted (page may be JavaScript-heavy)."

        # --- Build response ---
        response = f"📄 **Title:** {title}\n"
        response += f"📝 **Meta Description:** {description[:200]}\n\n"
        response += f"🔗 **Links ({len(links)} found):**\n" + "\n".join([f"{i+1}. {l[:80]}..." if len(l) > 80 else f"{i+1}. {l}" for i, l in enumerate(links)]) + "\n\n"
        response += f"🖼️ **Images ({len(images)} found):**\n" + "\n".join([f"{i+1}. {img[:80]}..." if len(img) > 80 else f"{i+1}. {img}" for i, img in enumerate(images)]) + "\n\n"
        response += f"📝 **Clean Article Text:**\n{clean_preview}"

        if len(response) > 4096:
            response = response[:4096] + "... (truncated)"

        await update.message.reply_text(response)

    except requests.exceptions.Timeout:
        await update.message.reply_text("❌ Timeout: Page took too long to respond.")
    except requests.exceptions.RequestException as e:
        await update.message.reply_text(f"❌ Fetch error: {str(e)[:150]}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)[:150]}")

# --- Register handlers ---
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("scrape", scrape))

# --- Webhook route ---
@app.route('/webhook', methods=['POST'])
async def webhook():
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, bot_app.bot)
        await bot_app.process_update(update)
        return "OK", 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- Main ---
def main():
    hostname = os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'webscraper-bot-eo90.onrender.com')
    webhook_url = f"https://{hostname}/webhook"

    async def setup():
        await bot_app.initialize()
        await bot_app.start()
        await bot_app.bot.delete_webhook(drop_pending_updates=True)
        await bot_app.bot.set_webhook(url=webhook_url)
        print(f"✅ Webhook set to: {webhook_url}")

    asyncio.run(setup())

    def run_flask():
        app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)

    t = threading.Thread(target=run_flask)
    t.start()
    print(f"🚀 Flask running on port {PORT}")
    t.join()

if __name__ == "__main__":
    main()
