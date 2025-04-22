import os
from PIL import Image
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes,
    ConversationHandler, filters
)
from yt_dlp import YoutubeDL

# Telegram bot token from env
BOT_TOKEN = os.environ.get("7775636547:AAET4bIKf2PMf5CfTj1hHlrHWJ5O3y1XWMU")
CHOOSING, MUSIC, VIDEO, IMAGE = range(4)

reply_keyboard = [
    ['Download Music', 'Download Video'],
    ['Image to Sticker', 'Help']
]
markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)

# === Flask App for Webhook ===
flask_app = Flask(__name__)
telegram_app = ApplicationBuilder().token("7775636547:AAET4bIKf2PMf5CfTj1hHlrHWJ5O3y1XWMU").build()

@flask_app.route('/')
def home():
    return 'Bot is alive!'

@flask_app.route(f"/webhook", methods=["POST"])
async def webhook():
    await telegram_app.update_queue.put(Update.de_json(request.get_json(force=True), telegram_app.bot))
    return 'OK'

# === Bot Handlers ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hi! I'm your media assistant bot.\n\nChoose one of the options below:",
        reply_markup=markup
    )
    return CHOOSING

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Here's what I can do:\n"
        "- Download Music: Send song name\n"
        "- Download Video: Send YouTube link\n"
        "- Image to Sticker: Send any photo\n\n"
        "Just tap a button to begin!"
    )
    return CHOOSING

async def choose_music(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send the name of the song you want:")
    return MUSIC

async def get_music(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    await update.message.reply_text(f"Searching for: {query}...")

    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'ffmpeg_location': '/usr/bin/ffmpeg',
            'quiet': True,
            'noplaylist': True,
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch1:{query}", download=True)
            filename = ydl.prepare_filename(info['entries'][0])
            mp3_file = filename.rsplit(".", 1)[0] + ".mp3"

        with open(mp3_file, 'rb') as f:
            await update.message.reply_audio(f)

        os.remove(mp3_file)

    except Exception as e:
        await update.message.reply_text(f"Error downloading song: {str(e)}")

    return CHOOSING

async def choose_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send a YouTube video link:")
    return VIDEO

async def get_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if "youtu" not in url:
        await update.message.reply_text("That doesn’t look like a YouTube link.")
        return VIDEO

    await update.message.reply_text("Downloading video...")

    try:
        ydl_opts = {
            'format': 'mp4',
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'quiet': True,
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        with open(filename, 'rb') as f:
            await update.message.reply_video(f)

        os.remove(filename)

    except Exception as e:
        await update.message.reply_text(f"Error downloading video: {str(e)}")

    return CHOOSING

async def ask_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send me a photo and I’ll turn it into a sticker!")
    return IMAGE

async def convert_image_to_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file = await photo.get_file()
    file_path = "downloads/temp.jpg"
    await file.download_to_drive(file_path)

    im = Image.open(file_path).convert("RGBA")
    im.thumbnail((512, 512))
    webp_path = "downloads/sticker.webp"
    im.save(webp_path, "WEBP")

    with open(webp_path, 'rb') as f:
        await update.message.reply_sticker(f)

    os.remove(file_path)
    os.remove(webp_path)

    return CHOOSING

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("I didn’t understand. Use the buttons below:", reply_markup=markup)
    return CHOOSING

# === Add Bot Handlers ===
conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        CHOOSING: [
            MessageHandler(filters.Regex("^Download Music$"), choose_music),
            MessageHandler(filters.Regex("^Download Video$"), choose_video),
            MessageHandler(filters.Regex("^Image to Sticker$"), ask_image),
            MessageHandler(filters.Regex("^Help$"), help_command),
        ],
        MUSIC: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_music)],
        VIDEO: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_video)],
        IMAGE: [MessageHandler(filters.PHOTO, convert_image_to_sticker)],
    },
    fallbacks=[MessageHandler(filters.ALL, cancel)],
)
telegram_app.add_handler(conv_handler)

# === Start Bot Webhook ===
if __name__ == "__main__":
    import asyncio
    async def run_bot():
        await telegram_app.initialize()
        await telegram_app.bot.set_webhook(url="https://your-bot-name.onrender.com/webhook")
        await telegram_app.start()
    asyncio.run(run_bot())
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
