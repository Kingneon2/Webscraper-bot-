import os
import asyncio
import threading
import requests
from bs4 import BeautifulSoup
import trafilatura
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# --- Flask app ---
app = Flask(__name__)
PORT = int(os.environ.get("PORT", 10000))

@app.route('/')
def health():
    return "Bot is running!", 200

# --- Telegram setup ---
TELEGRAM_TOKEN = os.environ.get("8696552585:AAHAtPXFCd0WW8tcED1sMuO4wwXCDw0wBHw")
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
        "• Clean article text (no ads/nav/sidebars)"
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
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        html = response.text

        soup = BeautifulSoup(html, 'html.parser')

        title = soup.title.string.strip() if soup.title else "No title found"

        meta_desc = soup.find('meta', attrs={'name': 'description'})
        description = meta_desc.get('content', 'No description') if meta_desc else "No description"

        links = []
        for a in soup.find_all('a', href=True)[:5]:
            href = a['href']
            if href.startswith('http'):
                links.append(href)
            elif href.startswith('/'):
                links.append(url.rstrip('/') + href)
            else:
                links.append(url.rstrip('/') + '/' + href)

        images = []
        for img in soup.find_all('img', src=True)[:3]:
            src = img['src']
            if src.startswith('http'):
                images.append(src)
            elif src.startswith('/'):
                images.append(url.rstrip('/') + src)
            else:
                images.append(url.rstrip('/') + '/' + src)

        clean_text = trafilatura.extract(html, include_comments=False, include_tables=False)
        clean_preview = clean_text[:600] + "..." if clean_text and len(clean_text) > 600 else clean_text or "No clean text extracted."

        response_text = f"📄 **Title:** {title}\n"
        response_text += f"📝 **Meta Description:** {description[:200]}\n\n"
        response_text += f"🔗 **Links ({len(links)} found):**\n" + "\n".join([f"{i+1}. {l[:80]}..." if len(l) > 80 else f"{i+1}. {l}" for i, l in enumerate(links)]) + "\n\n"
        response_text += f"🖼️ **Images ({len(images)} found):**\n" + "\n".join([f"{i+1}. {img[:80]}..." if len(img) > 80 else f"{i+1}. {img}" for i, img in enumerate(images)]) + "\n\n"
        response_text += f"📝 **Clean Article Text:**\n{clean_preview}"

        if len(response_text) > 4096:
            response_text = response_text[:4096] + "... (truncated)"

        await update.message.reply_text(response_text)

    except requests.exceptions.Timeout:
        await update.message.reply_text("❌ Timeout: Page took too long to respond.")
    except requests.exceptions.RequestException as e:
        await update.message.reply_text(f"❌ Fetch error: {str(e)[:150]}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)[:150]}")

# --- Register handlers ---
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("scrape", scrape))

# --- Main ---
def main():
    # Start Flask in a background thread
    def run_flask():
        app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)

    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print(f"🚀 Flask running on port {PORT}")

    # Start bot polling
    print("🤖 Bot started polling...")
    bot_app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
