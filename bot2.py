import telebot
import asyncio
import tempfile
import os
import requests
import time
from playwright.async_api import async_playwright

# === KONFIGURASI BOT TELEGRAM ===
BOT_TOKEN = "8368820938:AAHvxOy_XeXudehOD3TFjLHQ_uidzy50PCc"
bot = telebot.TeleBot(BOT_TOKEN)

# === SCRAPER IGRAM ===
async def scrape_igram(reel_url: str):
    """Ambil link video & caption dari igram.world"""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://igram.world", timeout=60000)

        # Isi input link
        await page.fill("#search-form-input", reel_url)
        await page.keyboard.press("Enter")

        # Tunggu hasil muncul
        await asyncio.sleep(12)

        # Ambil link video
        try:
            download_link = await page.get_attribute(
                "a.button__download[href*='.mp4']", "href"
            )
        except Exception:
            download_link = None

        # Ambil caption
        try:
            caption = await page.text_content("#app div.output-list__caption > p")
        except Exception:
            caption = None

        await browser.close()

        if not download_link:
            return None, None, "❌ Tidak ditemukan tautan video."

        return download_link, caption or "Tanpa caption.", None

# === DOWNLOAD DAN KIRIM ===
def download_and_send(chat_id, video_url, caption):
    """Download video dari URL dan kirim ke user"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
        path = tmp.name
        with requests.get(video_url, stream=True) as r:
            r.raise_for_status()
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    tmp.write(chunk)

    bot.send_video(chat_id, open(path, "rb"), caption=caption)
    os.remove(path)

# === ANIMASI PROGRESS (⏳) ===
async def show_progress(chat_id):
    """Tampilkan animasi ⏳ sementara proses berjalan"""
    symbols = ["⏳", "⌛", "🕐", "🕓", "🕗"]
    message = bot.send_message(chat_id, "⏳ Memproses video Reels...")
    msg_id = message.message_id

    for i in range(30):  # Maks 30 detik animasi
        await asyncio.sleep(2)
        symbol = symbols[i % len(symbols)]
        try:
            bot.edit_message_text(f"{symbol} Memproses video Reels...", chat_id, msg_id)
        except Exception:
            pass
    return msg_id

# === HANDLER PESAN ===
@bot.message_handler(func=lambda m: True)
def handle_message(msg):
    text = msg.text.strip()

    if "instagram.com/reel/" not in text:
        bot.reply_to(msg, "📎 Kirim link Reels Instagram valid.\nContoh: https://www.instagram.com/reel/xxxx/")
        return

    async def process():
        progress_task = asyncio.create_task(show_progress(msg.chat.id))

        try:
            link, caption, err = await scrape_igram(text)
            if err:
                bot.send_message(msg.chat.id, err)
                return

            # Hapus pesan progress
            try:
                bot.delete_message(msg.chat.id, progress_task.result())
            except Exception:
                pass

            # Kirim video
            download_and_send(msg.chat.id, link, caption)

        except Exception as e:
            try:
                bot.delete_message(msg.chat.id, progress_task.result())
            except Exception:
                pass
            bot.send_message(msg.chat.id, f"⚠️ Terjadi kesalahan:\n{e}")

    asyncio.run(process())

# === JALANKAN BOT ===
print("🤖 BOT IGRAM (Playwright + Caption + Progress) berjalan ...")
bot.infinity_polling()
