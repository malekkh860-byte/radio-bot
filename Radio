import asyncio
from datetime import datetime
import json
import os
import queue
import re
import socket
import threading
import logging
from flask import Flask, Response, render_template_string, request, jsonify
from telethon import Button, TelegramClient, events
from telethon.errors.rpcerrorlist import FloodWaitError, UserNotParticipantError
from telethon.tl.functions.channels import GetParticipantRequest
from telethon.tl.types import KeyboardButtonWebView, MessageMediaWebPage

# محاولة استيراد phonenumbers والـ geocoder
try:
  import phonenumbers
  from phonenumbers import geocoder
except ImportError:
  phonenumbers = None
  geocoder = None

# =======================================================
# [ MULTI-CLIENT HTTP FLASK RADIO SERVER (ADVANCED CALL-IN UI) ]
# =======================================================
flask_app = Flask(__name__)
listeners = []

# قوائم إدارة طلبات الاتصال والمداخلات الصوتية للمستمعين
pending_callers = {}  # {caller_id: {"name": str, "status": "pending/approved"}}
approved_caller_id = None

LISTEN_PAGE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>محطة الراديو المملوكة لمالك خلوف</title>
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: system-ui, -apple-system, sans-serif;
            background: linear-gradient(135deg, #09090e, #1a153b, #0f0c29);
            color: #fff;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            margin: 0;
            padding: 20px;
        }
        .card {
            background: rgba(255, 255, 255, 0.04);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 25px;
            padding: 30px 20px;
            max-width: 420px;
            width: 100%;
            text-align: center;
            box-shadow: 0 20px 40px rgba(0,0,0,0.6);
        }
        .vinyl-container {
            position: relative;
            width: 90px;
            height: 90px;
            margin: 0 auto 15px auto;
        }
        .vinyl {
            width: 100%;
            height: 100%;
            background: radial-gradient(circle, #222 30%, #111 31%, #000 70%);
            border-radius: 50%;
            border: 3px solid #00d2ff;
            display: flex;
            justify-content: center;
            align-items: center;
            box-shadow: 0 0 15px rgba(0, 210, 255, 0.4);
            animation: spin 4s linear infinite;
            animation-play-state: paused;
        }
        .vinyl::after {
            content: '';
            position: absolute;
            width: 22px;
            height: 22px;
            background: #ff4757;
            border-radius: 50%;
            border: 2px solid #fff;
        }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        
        h1 { font-size: 19px; color: #00d2ff; margin-bottom: 5px; }
        .owner { font-size: 12px; color: #a4b0be; margin-bottom: 15px; }

        .equalizer {
            display: flex;
            justify-content: center;
            align-items: flex-end;
            gap: 5px;
            height: 35px;
            margin: 15px 0;
        }
        .bar {
            width: 5px;
            background: linear-gradient(to top, #ff4757, #ff6b81, #2ed573);
            border-radius: 4px;
            animation: bounce 1.2s infinite ease-in-out alternate;
            animation-play-state: paused;
        }
        .bar:nth-child(1) { animation-delay: 0.1s; height: 15px; }
        .bar:nth-child(2) { animation-delay: 0.3s; height: 30px; }
        .bar:nth-child(3) { animation-delay: 0.2s; height: 22px; }
        .bar:nth-child(4) { animation-delay: 0.4s; height: 35px; }
        .bar:nth-child(5) { animation-delay: 0.15s; height: 18px; }

        @keyframes bounce { 0% { transform: scaleY(0.2); } 100% { transform: scaleY(1); } }

        audio { width: 100%; margin-top: 10px; border-radius: 30px; outline: none; }
        
        .status-box {
            background: rgba(0,0,0,0.3);
            padding: 8px;
            border-radius: 10px;
            font-size: 13px;
            color: #2ed573;
            margin-top: 10px;
            border: 1px solid rgba(46, 213, 115, 0.2);
        }
        .live-indicator {
            display: inline-block;
            width: 8px;
            height: 8px;
            background-color: #ff4757;
            border-radius: 50%;
            margin-left: 6px;
            animation: blink 1s infinite;
        }
        @keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.3; } 100% { opacity: 1; } }

        .call-section {
            margin-top: 20px;
            border-top: 1px solid rgba(255,255,255,0.1);
            padding-top: 15px;
        }
        .call-btn {
            background: linear-gradient(135deg, #ff4757, #ff6b81);
            color: white;
            border: none;
            padding: 10px 18px;
            border-radius: 10px;
            font-size: 14px;
            cursor: pointer;
            font-weight: bold;
            box-shadow: 0 4px 15px rgba(255,71,87,0.3);
            width: 100%;
        }
        .call-btn:hover { opacity: 0.9; }
        #callStatus {
            margin-top: 10px;
            font-size: 13px;
            color: #eccc68;
        }
    </style>
</head>
<body>
    <div class="card">
        <div class="vinyl-container">
            <div class="vinyl" id="vinylDisc"></div>
        </div>
        
        <h1>محطة الراديو المملوكة لمالك خلوف</h1>
        <div class="owner">بث مباشر فوري وعالي الجودة</div>
        
        <div class="equalizer" id="eqBars">
            <span class="bar"></span><span class="bar"></span><span class="bar"></span><span class="bar"></span><span class="bar"></span>
        </div>

        <div class="status-box">
            <span class="live-indicator"></span> البث المباشر يعمل الآن
        </div>

        <audio id="audioPlayer" controls autoplay src="/stream"></audio>

        <!-- قسم طلب المداخلة الصوتية للمستمع -->
        <div class="call-section">
            <button class="call-btn" id="callBtn" onclick="requestCall()">🎙️ طلب مداخلة صوتية على الهواء</button>
            <div id="callStatus">انقر لطلب التحدث مع المذيع</div>
        </div>
    </div>

    <script>
        const audio = document.getElementById('audioPlayer');
        const vinyl = document.getElementById('vinylDisc');
        const bars = document.querySelectorAll('.bar');
        
        const clientId = 'user_' + Math.random().toString(36).substring(2, 9);
        let myName = prompt("أدخل اسمك الكريم للانضمام للراديو:", "مستمع كريم") || "مستمع";
        let callRecorder;
        let isCalling = false;

        audio.onplay = () => {
            vinyl.style.animationPlayState = 'running';
            bars.forEach(bar => bar.style.animationPlayState = 'running');
        };
        audio.onpause = () => {
            vinyl.style.animationPlayState = 'paused';
            bars.forEach(bar => bar.style.animationPlayState = 'paused');
        };

        async function requestCall() {
            const btn = document.getElementById('callBtn');
            const statusDiv = document.getElementById('callStatus');

            if (!isCalling) {
                // إرسال طلب للمذيع
                let res = await fetch('/request-call', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({id: clientId, name: myName})
                });
                let data = await res.json();
                if(data.status === 'success') {
                    isCalling = true;
                    btn.innerText = "⏳ بانتظار موافقة المذيع...";
                    btn.style.background = "#eccc68";
                    statusStatusChecker();
                }
            }
        }

        function statusStatusChecker() {
            const interval = setInterval(async () => {
                let res = await fetch('/check-call-status?id=' + clientId);
                let data = await res.json();
                
                if (data.status === 'approved') {
                    clearInterval(interval);
                    document.getElementById('callStatus').innerText = "🟢 تم قبولك! أنت الآن تتحدث على الهواء مباشرة.";
                    document.getElementById('callBtn').innerText = "🔴 إنهاء المداخلة";
                    document.getElementById('callBtn').style.background = "#ff4757";
                    startSpeakingMic();
                } else if (data.status === 'rejected') {
                    clearInterval(interval);
                    document.getElementById('callStatus').innerText = "❌ عذراً، رفض المذيع الطلب حالياً.";
                    resetCallUI();
                }
            }, 3000);
        }

        async function startSpeakingMic() {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                callRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
                callRecorder.ondataavailable = e => {
                    if (e.data.size > 0) {
                        fetch('/caller-upload?id=' + clientId, { method: 'POST', body: e.data });
                    }
                };
                callRecorder.start(100);
            } catch(e) {
                alert("خطأ في تشغيل الميكروفون: " + e.message);
                resetCallUI();
            }
        }

        function resetCallUI() {
            isCalling = false;
            if(callRecorder) callRecorder.stop();
            document.getElementById('callBtn').innerText = "🎙️ طلب مداخلة صوتية على الهواء";
            document.getElementById('callBtn').style.background = "linear-gradient(135deg, #ff4757, #ff6b81)";
        }
    </script>
</body>
</html>
"""

HOST_PAGE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>لوحة تحكم المذيع - محطة مالك خلوف</title>
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: system-ui, -apple-system, sans-serif;
            background: linear-gradient(135deg, #141414, #1f1c2c);
            color: #fff;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            margin: 0;
            padding: 20px;
        }
        .card {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(15px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 30px 20px;
            max-width: 450px;
            width: 100%;
            text-align: center;
            box-shadow: 0 15px 35px rgba(0,0,0,0.6);
        }
        h1 { font-size: 19px; color: #ff4757; margin-bottom: 5px; }
        .subtitle { font-size: 13px; color: #a4b0be; margin-bottom: 20px; }
        
        .btn-group { display: flex; gap: 10px; justify-content: center; margin-top: 15px; }
        button {
            padding: 12px 18px;
            font-size: 14px;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            font-weight: bold;
            flex: 1;
        }
        .start { background: #2ed573; color: white; }
        .stop { background: #ff4757; color: white; }
        
        #status {
            margin-top: 20px;
            font-size: 14px;
            color: #eccc68;
            padding: 10px;
            background: rgba(0,0,0,0.3);
            border-radius: 8px;
        }
        .callers-box {
            margin-top: 20px;
            background: rgba(0,0,0,0.4);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 10px;
            padding: 12px;
            text-align: right;
            max-height: 200px;
            overflow-y: auto;
        }
        .caller-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: rgba(255,255,255,0.05);
            padding: 8px 12px;
            border-radius: 6px;
            margin-bottom: 8px;
        }
        .approve-btn { background: #2ed573; color: #fff; padding: 5px 10px; border-radius: 6px; border: none; cursor: pointer; font-size: 12px; }
    </style>
</head>
<body>
    <div class="card">
        <h1>🎙️ لوحة تحكم المذيع (مالك خلوف)</h1>
        <div class="subtitle">بث مباشر وإدارة المداخلات الصوتية للمستمعين</div>
        
        <div class="btn-group">
            <button class="start" onclick="startMic()">بدء البث 🟢</button>
            <button class="stop" onclick="stopMic()">إيقاف 🔴</button>
        </div>
        
        <div id="status">الحالة: متوقف تماماً</div>

        <div class="callers-box">
            <h4 style="margin: 0 0 10px 0; color: #00d2ff; font-size: 14px;">👥 طلبات المداخلات الصوتية:</h4>
            <div id="callersList">لا توجد طلبات معلقة حالياً</div>
        </div>
    </div>

    <script>
        let mediaRecorder;
        async function startMic() {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                let mimeType = 'audio/webm';
                if (!MediaRecorder.isTypeSupported(mimeType)) mimeType = 'audio/mp4';

                mediaRecorder = new MediaRecorder(stream, { mimeType: mimeType, audioBitsPerSecond: 128000 });
                mediaRecorder.ondataavailable = e => {
                    if (e.data.size > 0) {
                        fetch('/upload', { method: 'POST', body: e.data });
                    }
                };
                mediaRecorder.start(50); 
                document.getElementById('status').innerText = 'الحالة: 🔴 جاري البث المباشر على الهواء...';
                document.getElementById('status').style.color = '#2ed573';
            } catch (err) {
                alert('خطأ في تشغيل الميكروفون: ' + err.message);
            }
        }

        function stopMic() {
            if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                mediaRecorder.stop();
                document.getElementById('status').innerText = 'الحالة: ⚪ متوقف';
                document.getElementById('status').style.color = '#eccc68';
            }
        }

        // جلب قائمة طالبي المداخلة دورياً للمذيع
        setInterval(async () => {
            let res = await fetch('/get-pending-callers');
            let callers = await res.json();
            let listDiv = document.getElementById('callersList');
            
            if (Object.keys(callers).length === 0) {
                listDiv.innerHTML = 'لا توجد طلبات معلقة حالياً';
                return;
            }

            let html = '';
            for (let id in callers) {
                html += `<div class="caller-item">
                    <span>👤 ${callers[id].name}</span>
                    <button class="approve-btn" onclick="approveCaller('${id}')">موافقة 🟢</button>
                </div>`;
            }
            listDiv.innerHTML = html;
        }, 2000);

        async function approveCaller(id) {
            await fetch('/approve-caller?id=' + id, {method: 'POST'});
            alert("تم قبول المستمع، صوته الآن يذاع على الهواء مع المذيع!");
        }
    </script>
</body>
</html>
"""

# مسارات إدارة الاتصالات في الفلاسك
@flask_app.route('/request-call', methods=['POST'])
def request_call():
    data = request.json
    cid = data.get('id')
    name = data.get('name')
    pending_callers[cid] = {"name": name, "status": "pending"}
    return jsonify({"status": "success"})

@flask_app.route('/check-call-status')
def check_call_status():
    cid = request.args.get('id')
    if cid in pending_callers:
        return jsonify({"status": pending_callers[cid]["status"]})
    return jsonify({"status": "not_found"})

@flask_app.route('/get-pending-callers')
def get_pending_callers():
    # إرجاع فقط الطلبات التي حالتها معلقة
    active = {k: v for k, v in pending_callers.items() if v["status"] == "pending"}
    return jsonify(active)

@flask_app.route('/approve-caller', methods=['POST'])
def approve_caller():
    global approved_caller_id
    cid = request.args.get('id')
    if cid in pending_callers:
        pending_callers[cid]["status"] = "approved"
        approved_caller_id = cid
    return ('', 204)

@flask_app.route('/caller-upload', methods=['POST'])
def caller_upload():
    cid = request.args.get('id')
    if cid == approved_caller_id:
        data = request.data
        # بث صوت المستمع الموافق عليه لجميع المستمعين والمذيع
        for q in listeners[:]:
            if q.full():
                try: q.get_nowait()
                except queue.Empty: pass
            q.put(data)
    return ('', 204)

@flask_app.route('/')
def listener():
    return render_template_string(LISTEN_PAGE)

@flask_app.route('/host')
def host():
    return render_template_string(HOST_PAGE)

@flask_app.route('/upload', methods=['POST'])
def upload():
    data = request.data
    for q in listeners[:]:
        if q.full():
            try: q.get_nowait()
            except queue.Empty: pass
        q.put(data)
    return ('', 204)

def generate_audio(client_queue):
    try:
        while True:
            chunk = client_queue.get()
            yield chunk
    finally:
        if client_queue in listeners:
            listeners.remove(client_queue)

@flask_app.route('/stream')
def stream():
    client_queue = queue.Queue(maxsize=5)
    listeners.append(client_queue)
    return Response(generate_audio(client_queue), mimetype='audio/webm')

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def run_flask_server():
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# =======================================================
# [ TELEGRAM BOT CONFIGURATION ]
# =======================================================
API_ID = 35522856
API_HASH = '8cf9c2d13140fdee3e902d62b6bb987d'
TOKEN_SYTC_BOT = '8660058763:AAFPQZ2oKw37qRamSRyObLBvfVGsj-0CHoQ'
WEB_APP_URL = 'https://malekkh860.pythonanywhere.com'
TRUECALLER_BOT = '@TrueCalleRobot'
ADMIN_ID = 8262756069
ADMIN_USERNAME = 'almadarsy'

SOURCES = ['@TelevisionSyria', '@syp2day', '@syriaST', '@ShamCashn']
TARGET_CHANNEL = 'https://t.me/almadaralakbariyasy'
CHANNEL_USERNAME = 'almadaralakbariyasy'
PREMIUM_URL = 'https://traidmode.com/telegram-premium/get/?urls=https://s1.litemode.org/get/App/Telegram/Telegram-v12.4.3-YalaMod.Com.apk&names=%D8%AA%D8%AD%D9%8D%D9%85%D9%8A%D9%84%20%D8%AA%D9%8D%D9%84%D9%8A%D8%AC%D8%B1%D8%A7%D9%85%20%D8%A7%D9%84%D9%85%D9%8A%D8%B2%20%D8%A7%D9%84%D8%A5%D8%B5%D8%AF%D8%A7%D8%B5%20:%20v12.4.3%20%E2%9A%A1%F0%9F%94%A5%E2%9C%85'

STATE_FILE = 'last_messages.json'
USERS_FILE = 'bot_users.json'

CUSTOM_RESPONSES = {
    '+963996131559': (
        '👑 **معلومات خاصة (رقم المطور):**\n'
        '👤 **الاسم:** مالك خلوف\n'
        '📱 **الرقم:** +963996131559\n'
        '📧 **الإيميل:** malekkh860@gmail.com\n'
        '💻 **الصفة:** صانع ومطور البوت الرسمي.\n'
        '🌐 **قناة الهدف:** https://t.me/almadaralakbariyasy'
    )
}

CLIENT_PARAMS = {'connection_retries': None, 'retry_delay': 3, 'auto_reconnect': True}

client = TelegramClient('session_user', API_ID, API_HASH, **CLIENT_PARAMS)
sytc_bot = TelegramClient('session_sytcbot', API_ID, API_HASH, **CLIENT_PARAMS)

USER_MODES = {}
file_lock = asyncio.Lock()
truecaller_lock = asyncio.Lock()
truecaller_queue = asyncio.Queue()

FOOTER_TEXT = (
    '━━━━━━━━━━━━━━━\n'
    '📢 **فضلاً الاشتراك بقناتنا لنستمر:** 👉 https://t.me/almadaralakbariyasy\n'
    f'👑 **صانع البوت:** مالك خلوف (@{ADMIN_USERNAME})'
)

WELCOME_TEXT = (
    '✨ **أهلاً بك في محطة الراديو والبوت الخاص بنا!** ✨\n\n'
    '🔥 **جرب هذه الخدمات الرائعة:**\n'
    '1️⃣ البحث عن معلومات أي رقم 🔎\n'
    '2️⃣ الحصول على تلجرام مميز مجاناً 💎\n'
    '3️⃣ معرفة الدولة ومزود الشبكة الخاص بك 🌍\n'
    '4️⃣ معرفة إن كان هناك عقوبات على حسابك بتلجرام 🚫\n'
    '5️⃣ طلب محادثة مباشرة مع المذيع/المطور 💬\n\n'
    '💡 **صانع البوت ومحطة الراديو:** مالك خلوف\n'
    f'👤 **اسم المستخدم الخاص بي:** @{ADMIN_USERNAME}\n\n'
    f'{FOOTER_TEXT}'
)

def get_country_name(phone_input: str) -> str:
    if not phone_input: return 'غير محدد'
    if phonenumbers and geocoder:
        try:
            parsed = phonenumbers.parse(phone_input if phone_input.startswith('+') else '+' + phone_input, None)
            c_name = geocoder.description_for_number(parsed, 'ar')
            if c_name: return c_name
        except Exception: pass
    return 'سوريا 🇸🇾' if '+963' in phone_input else 'دولي / غير معروف 🌍'

async def notify_admin(sender_id, username, first_name, action_info, country='غير محدد', ip_address=None):
    if sender_id == ADMIN_ID: return
    user_link = f'[{first_name}](tg://user?id={sender_id})'
    user_ref = f'@{username}' if username else 'بدون معرف'
    notification_text = (
        f'🔔 **إشعار استخدام جديد للبوت!**\n\n'
        f'👤 **المستخدم:** {user_link} ({user_ref})\n'
        f'🆔 **الآيدي:** `{sender_id}`\n'
        f'🌍 **الدولة:** {country}\n'
        f'📌 **الإجراء:** {action_info}\n'
        f'⏰ **الوقت:** `{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}`'
    )
    try: await sytc_bot.send_message(ADMIN_ID, notification_text, parse_mode='md')
    except Exception: pass

async def check_subscription(user_id):
    try:
        participant = await sytc_bot(GetParticipantRequest(channel=CHANNEL_USERNAME, participant=user_id))
        status = type(participant.participant).__name__
        return status not in ['ChannelParticipantLeft', 'ChannelParticipantBanned', 'Error']
    except Exception: return False

def normalize_phone(phone_input: str) -> str:
    cleaned = re.sub(r'[\s\-\(\)]', '', phone_input.strip())
    digits_only = re.sub(r'[^\d]', '', cleaned)
    if cleaned.startswith('+'): return cleaned
    if digits_only.startswith('09') and len(digits_only) == 10: return '+963' + digits_only[1:]
    return '+' + digits_only

def remove_telegram_usernames(text):
    if not text: return ''
    pattern = r'https?://(?:t\.me|telegram\.me|telegram\.dog)/(?:televisionsyria|syriast|almadaralakbariyasy)/?|t\.me/(?:televisionsyria|syriast|almadaralakbariyasy)/?'
    return re.sub(pattern, '', text, flags=re.IGNORECASE).strip()

async def load_state():
    if os.path.exists(STATE_FILE):
        try: return await asyncio.to_thread(lambda: json.load(open(STATE_FILE, 'r', encoding='utf-8')))
        except Exception: return {}
    return {}

async def save_state(state):
    async with file_lock:
        await asyncio.to_thread(lambda: json.dump(state, open(STATE_FILE, 'w', encoding='utf-8'), ensure_ascii=False, indent=4))

async def save_bot_user(user_id, username, first_name='', country='غير محدد', ip_address=None):
    async with file_lock:
        def _save():
            users = {}
            if os.path.exists(USERS_FILE):
                try: users = json.load(open(USERS_FILE, 'r', encoding='utf-8'))
                except Exception: users = {}
            str_id = str(user_id)
            if str_id not in users:
                users[str_id] = {'user_id': user_id, 'username': username, 'first_name': first_name, 'country': country, 'first_seen': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            json.dump(users, open(USERS_FILE, 'w', encoding='utf-8'), ensure_ascii=False, indent=4)
        await asyncio.to_thread(_save)

def get_main_keyboard():
    return [
        [Button.inline('💎 احصل على تلجرام مميز', b'btn_premium')],
        [Button.inline('🔍 البحث عن معلومات رقم', b'btn_truecaller')],
        [Button.inline('💬 طلب محادثة مع المذيع / المطور', b'btn_request_chat')],
        [KeyboardButtonWebView('🌐 كشف عنوان الـ IP ومعلوماتك', WEB_APP_URL)],
        [Button.url('🚫 معرفة العقوبات على حسابك بتلجرام', 'https://t.me/SpamBot?start=start')],
        [Button.url('👨‍💻 التواصل المباشر مع المطور', f'https://t.me/{ADMIN_USERNAME}')]
    ]

async def process_truecaller_queue():
    while True:
        phone_number, fut = await truecaller_queue.get()
        async with truecaller_lock:
            try:
                if not client.is_connected(): await client.connect()
                loop = asyncio.get_running_loop()
                handler_fut = loop.create_future()
                @client.on(events.MessageEdited(chats=TRUECALLER_BOT))
                @client.on(events.NewMessage(chats=TRUECALLER_BOT))
                async def truecaller_handler(event):
                    text = event.message.text or ''
                    if any(w in text.lower() for w in ['searching', 'جاري البحث', 'انتظر', 'loading']): return
                    if not handler_fut.done(): handler_fut.set_result(text)
                client.add_event_handler(truecaller_handler)
                try:
                    await client.send_message(TRUECALLER_BOT, phone_number)
                    res = await asyncio.wait_for(handler_fut, timeout=12)
                    fut.set_result(res)
                except Exception: fut.set_result(None)
                finally: client.remove_event_handler(truecaller_handler)
                await asyncio.sleep(2)
            except Exception:
                if not fut.done(): fut.set_result(None)
            finally: truecaller_queue.task_done()

async def fetch_truecaller_info_queued(phone_number: str) -> str:
    loop = asyncio.get_running_loop()
    fut = loop.create_future()
    await truecaller_queue.put((phone_number, fut))
    return await fut

async def catch_up_missed_messages():
    last_ids = await load_state()
    for source in SOURCES:
        try:
            entity = await client.get_entity(source)
            source_key = f'@{entity.username}' if getattr(entity, 'username', None) else str(entity.id)
            last_id = last_ids.get(source_key)
            if last_id:
                async for message in client.iter_messages(entity, min_id=last_id, reverse=True):
                    original_text = message.text or ''
                    cleaned_text = remove_telegram_usernames(original_text) or original_text
                    if message.media:
                        if isinstance(message.media, MessageMediaWebPage):
                            await client.send_message(TARGET_CHANNEL, cleaned_text or '[رابط]')
                        else:
                            await client.send_file(TARGET_CHANNEL, message.media, caption=cleaned_text or None)
                    elif cleaned_text:
                        await client.send_message(TARGET_CHANNEL, cleaned_text)
                    last_ids[source_key] = message.id
                    await save_state(last_ids)
                    await asyncio.sleep(0.5)
            else:
                async for message in client.iter_messages(entity, limit=1):
                    last_ids[source_key] = message.id
                    await save_state(last_ids)
        except Exception: pass

@client.on(events.NewMessage(chats=SOURCES))
async def copy_logic(event):
    try:
        original_text = event.message.text or ''
        cleaned_text = remove_telegram_usernames(original_text) or original_text
        if event.message.media:
            if isinstance(event.message.media, MessageMediaWebPage):
                await client.send_message(TARGET_CHANNEL, cleaned_text or '[رابط]')
            else:
                await client.send_file(TARGET_CHANNEL, event.message.media, caption=cleaned_text or None)
        elif cleaned_text:
            await client.send_message(TARGET_CHANNEL, cleaned_text)
        source_key = f'@{event.chat.username}' if event.chat.username else str(event.chat_id)
        last_ids = await load_state()
        last_ids[source_key] = event.message.id
        await save_state(last_ids)
    except Exception: pass

@sytc_bot.on(events.CallbackQuery)
async def callback_handler(event):
    sender_id = event.sender_id
    sender = await event.get_sender()
    username = getattr(sender, 'username', None)
    first_name = getattr(sender, 'first_name', '')
    data = event.data

    if data == b'main_menu':
        USER_MODES.pop(sender_id, None)
        await event.edit(WELCOME_TEXT, buttons=get_main_keyboard())
    elif data == b'btn_premium':
        asyncio.create_task(notify_admin(sender_id, username, first_name, 'طلب تلجرام مميز', get_country_name(str(sender_id))))
        is_subbed = await check_subscription(sender_id)
        if is_subbed:
            await event.edit(f'🎉 **تهانينا! تم التحقق من اشتراكك.**\n\n{FOOTER_TEXT}', buttons=[[Button.url('💎 تحميل تلجرام المميز ⚡', PREMIUM_URL)], [Button.inline('🔙 القائمة الرئيسية', b'main_menu')]])
        else:
            await event.edit(f'⚠️ **يجب عليك الاشتراك بقناتنا أولاً!**\n\n{FOOTER_TEXT}', buttons=[[Button.url('📢 الاشتراك بالقناة', f'https://t.me/{CHANNEL_USERNAME}')], [Button.inline('🔄 تحقق من الاشتراك', b'btn_premium')], [Button.inline('🔙 القائمة الرئيسية', b'main_menu')]])
    elif data == b'btn_truecaller':
        USER_MODES[sender_id] = 'waiting_for_truecaller_num'
        await event.edit(f'🔍 **أرسل الرقم للبحث عنه الآن...**\n\n{FOOTER_TEXT}', buttons=[[Button.inline('🔙 القائمة الرئيسية', b'main_menu')]])
    elif data == b'btn_request_chat':
        USER_MODES[sender_id] = 'waiting_for_chat_message'
        await event.edit(f'💬 **أرسل رسالتك أو استفسارك للمذيع والمطور (مالك خلوف):**\n\n{FOOTER_TEXT}', buttons=[[Button.inline('🔙 القائمة الرئيسية', b'main_menu')]])

@sytc_bot.on(events.NewMessage(incoming=True))
async def sytc_bot_message_handler(event):
    if not event.is_private: return
    sender_id = event.sender_id
    sender = await event.get_sender()
    username = getattr(sender, 'username', None)
    first_name = getattr(sender, 'first_name', '')
    text = event.text or ''

    if text.startswith('/start'):
        USER_MODES.pop(sender_id, None)
        asyncio.create_task(save_bot_user(sender_id, username, first_name))
        await event.respond(WELCOME_TEXT, buttons=get_main_keyboard())
        return

    if USER_MODES.get(sender_id) == 'waiting_for_chat_message':
        USER_MODES.pop(sender_id, None)
        forward_text = f'📩 **رسالة جديدة:**\n👤 [{first_name}](tg://user?id={sender_id}) (@{username or "بدون"})\n🆔 `{sender_id}`\n\n💬 {text}'
        try: await sytc_bot.send_message(ADMIN_ID, forward_text, parse_mode='md')
        except Exception: pass
        await event.respond(f'✅ **تم إرسال رسالتك إلى المذيع مالك خلوف بنجاح!**\n\n{FOOTER_TEXT}', buttons=get_main_keyboard())
        return

    if USER_MODES.get(sender_id) == 'waiting_for_truecaller_num':
        USER_MODES.pop(sender_id, None)
        norm_p = normalize_phone(text)
        if norm_p in CUSTOM_RESPONSES:
            await event.respond(CUSTOM_RESPONSES[norm_p])
            return
        msg = await event.respond('⏳ **جاري الاستعلام عن الرقم...**')
        res = await fetch_truecaller_info_queued(norm_p)
        if res: await msg.edit(f'🔍 **النتيجة لـ ({norm_p}):**\n\n{res}\n\n{FOOTER_TEXT}')
        else: await msg.edit('❌ **لم يتم العثور على نتائج.**')

async def main():
    threading.Thread(target=run_flask_server, daemon=True).start()
    ip = get_local_ip()
    print('📻 محطة الراديو المملوكة لمالك خلوف تعمل بنجاح:')
    print(f'🎙️ لوحة تحكم المذيع: http://127.0.0.1:5000/host')
    print(f'🎧 صفحة المستمعين: http://{ip}:5000')
    
    await client.start()
    await sytc_bot.start(bot_token=TOKEN_SYTC_BOT)
    asyncio.create_task(process_truecaller_queue())
    await catch_up_missed_messages()
    await asyncio.gather(client.run_until_disconnected(), sytc_bot.run_until_disconnected())

if __name__ == '__main__':
    asyncio.run(main())
