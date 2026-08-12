import os
import threading
import asyncio
import tracemalloc

# تفعيل تتبع الذاكرة للتخلص من التحذير
tracemalloc.start()

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler

app = Flask(__name__)
app.config['SECRET_KEY'] = 'malek_khalouf_secure_key'
socketio = SocketIO(app, cors_allowed_origins="*")

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OWNER_CHAT_ID = os.environ.get("OWNER_CHAT_ID")

LANGS = {
    'ar': {'title': 'محطة مالك خلوف الإذاعية', 'btn_open': 'استمع الآن 📻', 'btn_talk': 'طلب التكلم 🎤'},
    'en': {'title': 'Malek Khalouf Radio Station', 'btn_open': 'Listen Now 📻', 'btn_talk': 'Request to Talk 🎤'},
    'zh': {'title': '马利克·哈卢夫广播电台', 'btn_open': '现在收听 📻', 'btn_talk': '请求发言 🎤'}
}

@app.route('/')
def receiver():
    lang = request.args.get('lang', 'ar')
    return render_template('receiver.html', lang=lang)

@app.route('/broadcast')
def broadcaster():
    return render_template('broadcaster.html')

@app.route('/api/request-talk', methods=['POST'])
def api_request_talk():
    return jsonify({"status": "success"})

@socketio.on('audio_data')
def handle_audio(data):
    emit('audio_stream', data, broadcast=True, include_self=False)

@socketio.on('send_message')
def handle_message(data):
    emit('receive_message', data, broadcast=True)

# --- منطق البوت ---
async def start(update, context):
    kb = [[InlineKeyboardButton("العربية 🇸🇦", callback_data="lang_ar"),
           InlineKeyboardButton("English 🇬🇧", callback_data="lang_en"),
           InlineKeyboardButton("中文 🇨🇳", callback_data="lang_zh")]]
    await update.message.reply_text("مرحباً! اختر لغتك / Hello! Choose your language:", reply_markup=InlineKeyboardMarkup(kb))

async def lang_handler(update, context):
    query = update.callback_query
    lang = query.data.split('_')[1]
    webapp_url = f"https://{request.host}/?lang={lang}"
    kb = [[InlineKeyboardButton(LANGS[lang]['btn_open'], web_app=WebAppInfo(url=webapp_url))]]
    await query.edit_message_text(text="تم اختيار اللغة! / Language selected!", reply_markup=InlineKeyboardMarkup(kb))

def run_bot_thread():
    if not TELEGRAM_TOKEN:
        return
    # تعيين Event Loop مستقرة ومستقلة للخيط الجانبي
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(lang_handler, pattern="^lang_"))
    
    # تشغيل الاستعلام بدون ربط إشارات النظام لمنع الأخطاء
    application.run_polling(stop_signals=None, close_loop=False)

if __name__ == '__main__':
    if TELEGRAM_TOKEN:
        bot_thread = threading.Thread(target=run_bot_thread, daemon=True)
        bot_thread.start()
    
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)
    
