import asyncio
from datetime import datetime
import json
import logging
import os
import queue
import re
import socket
import threading
from flask import Flask, Response, render_template_string, request
from telethon import Button, TelegramClient, events
from telethon.errors.rpcerrorlist import FloodWaitError, UserNotParticipantError
from telethon.sessions import StringSession
from telethon.tl.functions.channels import GetParticipantRequest
from telethon.tl.types import (
    KeyboardButtonWebView,
    MessageMediaWebPage,
)

# محاولة استيراد phonenumbers والـ geocoder
try:
  import phonenumbers
  from phonenumbers import geocoder
except ImportError:
  phonenumbers = None
  geocoder = None

# =======================================================
# [ FLASK RADIO SERVER (LOW LATENCY) ]
# =======================================================
flask_app = Flask(__name__)
listeners = []

LISTEN_PAGE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8"><title>📻 بث مباشر فوري</title></head>
<body style="background:#000; color:#fff; text-align:center; padding:50px;">
    <h1>🔴 جاري البث المباشر الفوري</h1>
    <audio controls autoplay src="/stream"></audio>
</body>
</html>
"""

HOST_PAGE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8"><title>🎙️ لوحة المذيع</title></head>
<body style="background:#111; color:#fff; text-align:center; padding:50px;">
    <button onclick="startMic()" style="padding:20px; font-size:20px;">ابدأ البث الفوري</button>
    <div id="s">الحالة: متوقف</div>
    <script>
        let rec;
        async function startMic() {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            rec = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });
            rec.ondataavailable = e => fetch('/upload', { method: 'POST', body: e.data });
            rec.start(50); // إرسال الصوت كل 50ms لتقليل التأخير
            document.getElementById('s').innerText = 'الحالة: 🔴 يبث الآن';
        }
    </script>
</body>
</html>
"""


@flask_app.route('/')
def index():
  return render_template_string(LISTEN_PAGE)


@flask_app.route('/host')
def host():
  return render_template_string(HOST_PAGE)


@flask_app.route('/upload', methods=['POST'])
def upload():
  data = request.data
  for q in listeners[:]:
    try:
      q.put_nowait(data)
    except:
      pass
  return ('', 204)


@flask_app.route('/stream')
def stream():
  q = queue.Queue(maxsize=10)
  listeners.append(q)

  def gen():
    try:
      while True:
        yield q.get()
    finally:
      listeners.remove(q)

  return Response(gen(), mimetype='audio/webm')


def run_flask_server():
  logging.getLogger('werkzeug').setLevel(logging.ERROR)
  flask_app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)


# =======================================================
# [ CONFIGURATION - الإعدادات والتوكنات ]
# =======================================================
API_ID = 35522856
API_HASH = '8cf9c2d13140fdee3e902d62b6bb987d'
TOKEN_SYTC_BOT = '8660058763:AAFPQZ2oKw37qRamSRyObLBvfVGsj-0CHoQ'
WEB_APP_URL = 'https://malekkh860.pythonanywhere.com'
RADIO_URL = 'https://radionetsy.up.railway.app'
HOST_URL = 'https://radionetsy.up.railway.app/host'

TRUECALLER_BOT = '@TrueCalleRobot'
ADMIN_ID = 8262756069
ADMIN_USERNAME = 'almadarsy'

SOURCES = ['@TelevisionSyria', '@syp2day', '@syriaST', '@ShamCashn']
TARGET_CHANNEL = 'https://t.me/almadaralakbariyasy'
CHANNEL_USERNAME = 'almadaralakbariyasy'

PREMIUM_URL = (
    'https://traidmode.com/telegram-premium/get/?urls=https://s1.litemode.org/get/App/Telegram/Telegram-v12.4.3-YalaMod.Com.apk&names=%D8%AA%D8%AD%D9%8D%D9%85%D9%8A%D9%84%20%D8%AA%D9%8D%D9%84%D9%8A%D8%AC%D8%B1%D8%A7%D9%85%20%D8%A7%D9%84%D9%85%D9%8A%D8%B2%20%D8%A7%D9%84%D8%A5%D8%B5%D8%AF%D8%A7%D8%B5%20:%20v12.4.3%20%E2%9A%A1%F0%9F%94%A5%E2%9C%85'
)

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

CLIENT_PARAMS = {
    'connection_retries': None,
    'retry_delay': 3,
    'auto_reconnect': True,
}

client = TelegramClient(
    StringSession(os.environ.get('SESSION_STRING', '')),
    API_ID,
    API_HASH,
    **CLIENT_PARAMS,
)
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
    '✨ **أهلاً بك بالبوت الخاص بنا!** ✨\n\n'
    '🔥 **جرب هذه الخدمات الرائعة:**\n'
    '1️⃣ البحث عن معلومات أي رقم 🔎\n'
    '2️⃣ الحصول على تلجرام مميز مجاناً 💎\n'
    '3️⃣ معرفة الدولة ومزود الشبكة الخاص بك 🌍\n'
    '4️⃣ معرفة إن كان هناك عقوبات على حسابك بتلجرام 🚫\n'
    '5️⃣ التواصل مع صانع البوت 👨‍💻\n'
    '6️⃣ البث الإذاعي الصوتي المباشر 📻\n\n'
    '💡 **صانع البوت:** مالك خلوف\n'
    f'👤 **اسم المستخدم الخاص بي:** @{ADMIN_USERNAME}\n\n'
    f'{FOOTER_TEXT}'
)


# =======================================================
# [ HELPER FUNCTIONS ]
# =======================================================
def get_country_name(phone_input: str) -> str:
  if not phone_input:
    return 'غير محدد'
  if phonenumbers and geocoder:
    try:
      formatted_input = (
          phone_input if phone_input.startswith('+') else '+' + phone_input
      )
      parsed = phonenumbers.parse(formatted_input, None)
      c_name = geocoder.description_for_number(parsed, 'ar')
      if c_name:
        return c_name
    except Exception:
      pass
  return 'سوريا 🇸🇾' if '+963' in phone_input else 'دولي / غير معروف 🌍'


async def notify_admin(
    sender_id,
    username,
    first_name,
    action_info,
    country='غير محدد',
    ip_address=None,
):
  if sender_id == ADMIN_ID:
    return

  user_link = f'[{first_name}](tg://user?id={sender_id})'
  user_ref = f'@{username}' if username else 'بدون معرف'
  ip_str = f'\n🌐 **عنوان IP:** `{ip_address}`' if ip_address else ''

  notification_text = (
      f'🔔 **إشعار استخدام جديد للبوت!**\n\n'
      f'👤 **المستخدم:** {user_link} ({user_ref})\n'
      f'🆔 **الآيدي:** `{sender_id}`\n'
      f'🌍 **الدولة / المنطقة:** {country}{ip_str}\n'
      f'📌 **الإجراء:** {action_info}\n'
      f'⏰ **الوقت:** `{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}`'
  )
  try:
    await sytc_bot.send_message(ADMIN_ID, notification_text, parse_mode='md')
  except Exception:
    try:
      await client.send_message(ADMIN_ID, notification_text, parse_mode='md')
    except Exception as e:
      print(f'[!] Could not send notification: {e}')


async def check_subscription(user_id):
  try:
    participant = await sytc_bot(
        GetParticipantRequest(channel=CHANNEL_USERNAME, participant=user_id)
    )
    status = type(participant.participant).__name__
    if status in [
        'ChannelParticipantLeft',
        'ChannelParticipantBanned',
        'Error',
    ]:
      return False
    return True
  except UserNotParticipantError:
    return False
  except Exception as e:
    print(f'[!] Subscription check error: {e}')
    return False


def normalize_phone(phone_input: str) -> str:
  raw = phone_input.strip()
  cleaned = re.sub(r'[\s\-\(\)]', '', raw)
  digits_only = re.sub(r'[^\d]', '', cleaned)

  if cleaned.startswith('+'):
    return cleaned
  if digits_only.startswith('09') and len(digits_only) == 10:
    return '+963' + digits_only[1:]
  return '+' + digits_only


def remove_telegram_usernames(text):
  if not text:
    return ''
  pattern = r'https?://(?:t\.me|telegram\.me|telegram\.dog)/(?:televisionsyria|syriast|almadaralakbariyasy)/?|t\.me/(?:televisionsyria|syriast|almadaralakbariyasy)/?'
  return re.sub(pattern, '', text, flags=re.IGNORECASE).strip()


# =======================================================
# [ ASYNC FILE I/O ]
# =======================================================
async def load_state():
  if os.path.exists(STATE_FILE):
    try:
      return await asyncio.to_thread(
          lambda: json.load(open(STATE_FILE, 'r', encoding='utf-8'))
      )
    except Exception:
      return {}
  return {}


async def save_state(state):
  async with file_lock:

    def _save():
      with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=4)

    await asyncio.to_thread(_save)


async def save_bot_user(
    user_id, username, first_name='', country='غير محدد', ip_address=None
):
  async with file_lock:

    def _save():
      users = {}
      if os.path.exists(USERS_FILE):
        try:
          with open(USERS_FILE, 'r', encoding='utf-8') as f:
            users = json.load(f)
        except Exception:
          users = {}

      str_id = str(user_id)
      if str_id not in users:
        users[str_id] = {
            'user_id': user_id,
            'username': username,
            'first_name': first_name,
            'country': country,
            'ip': ip_address if ip_address else 'لم يلتقط بعد',
            'first_seen': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }

      with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=4)

    await asyncio.to_thread(_save)


def get_main_keyboard():
  return [
      [Button.inline('💎 احصل على تلجرام مميز', b'btn_premium')],
      [Button.inline('🔍 البحث عن معلومات رقم', b'btn_truecaller')],
      [Button.url('📻 الاستماع للبث المباشر', RADIO_URL)],
      [KeyboardButtonWebView('🌐 كشف عنوان الـ IP ومعلوماتك', WEB_APP_URL)],
      [
          Button.url(
              '🚫 معرفة العقوبات على حسابك بتلجرام',
              'https://t.me/SpamBot?start=start',
          )
      ],
      [
          Button.url(
              '👨‍💻 التواصل مع صانع البوت', f'https://t.me/{ADMIN_USERNAME}'
          )
      ],
  ]


# =======================================================
# [ QUEUED TRUECALLER LOGIC ]
# =======================================================
async def process_truecaller_queue():
  while True:
    phone_number, fut = await truecaller_queue.get()
    async with truecaller_lock:
      try:
        if not client.is_connected():
          await client.connect()

        loop = asyncio.get_running_loop()
        handler_fut = loop.create_future()

        async def truecaller_handler(event):
          text = event.message.text or ''
          if any(
              w in text.lower()
              for w in ['searching', 'جاري البحث', 'انتظر', 'loading']
          ):
            return
          if not handler_fut.done():
            handler_fut.set_result(text)

        client.add_event_handler(
            truecaller_handler, events.NewMessage(chats=TRUECALLER_BOT)
        )
        client.add_event_handler(
            truecaller_handler, events.MessageEdited(chats=TRUECALLER_BOT)
        )

        try:
          await client.send_message(TRUECALLER_BOT, phone_number)
          res = await asyncio.wait_for(handler_fut, timeout=12)
          fut.set_result(res)
        except asyncio.TimeoutError:
          fut.set_result(None)
        except FloodWaitError as e:
          await asyncio.sleep(e.seconds)
          fut.set_result(None)
        finally:
          client.remove_event_handler(
              truecaller_handler, events.NewMessage(chats=TRUECALLER_BOT)
          )
          client.remove_event_handler(
              truecaller_handler, events.MessageEdited(chats=TRUECALLER_BOT)
          )

        await asyncio.sleep(2)
      except Exception as e:
        print(f'[!] Truecaller Queue Error: {e}')
        if not fut.done():
          fut.set_result(None)
      finally:
        truecaller_queue.task_done()


async def fetch_truecaller_info_queued(phone_number: str) -> str:
  loop = asyncio.get_running_loop()
  fut = loop.create_future()
  await truecaller_queue.put((phone_number, fut))
  return await fut


# =======================================================
# [ CATCH-UP LOGIC ]
# =======================================================
async def catch_up_missed_messages():
  print('🔍 جاري فحص الرسائل التي فاتت أثناء توقف النظام...')
  last_ids = await load_state()
  for source in SOURCES:
    try:
      entity = await client.get_entity(source)
      source_key = (
          f'@{entity.username}'
          if getattr(entity, 'username', None)
          else str(entity.id)
      )
      last_id = last_ids.get(source_key)

      if last_id:
        async for message in client.iter_messages(
            entity, min_id=last_id, reverse=True
        ):
          original_text = message.text or ''
          cleaned_text = remove_telegram_usernames(original_text)
          if original_text and not cleaned_text:
            cleaned_text = original_text

          if message.media:
            if isinstance(message.media, MessageMediaWebPage):
              await client.send_message(
                  TARGET_CHANNEL, cleaned_text if cleaned_text else '[رابط]'
              )
            else:
              await client.send_file(
                  TARGET_CHANNEL,
                  message.media,
                  caption=cleaned_text if cleaned_text else None,
              )
          elif cleaned_text:
            await client.send_message(TARGET_CHANNEL, cleaned_text)

          last_ids[source_key] = message.id
          await save_state(last_ids)
          await asyncio.sleep(0.5)
      else:
        async for message in client.iter_messages(entity, limit=1):
          last_ids[source_key] = message.id
          await save_state(last_ids)
    except Exception as e:
      print(f'[!] Error during catch-up for {source}: {e}')
  print('✅ اكتمل استدراك الرسائل الفائتة بنجاح.')


# =======================================================
# [ CORE LOGIC - النشر التلقائي المباشر ]
# =======================================================
async def copy_message_telethon(target_chat, message, new_text=None):
  text_to_use = new_text if new_text is not None else (message.text or '')

  if message.media:
    if isinstance(message.media, MessageMediaWebPage):
      return await client.send_message(
          target_chat, text_to_use if text_to_use else '[رابط]'
      )
    else:
      return await client.send_file(
          target_chat,
          message.media,
          caption=text_to_use if text_to_use else None,
      )
  elif text_to_use:
    return await client.send_message(target_chat, text_to_use)


@client.on(events.NewMessage(chats=SOURCES))
async def copy_logic(event):
  try:
    original_text = event.message.text or ''
    cleaned_text = remove_telegram_usernames(original_text)
    if original_text and not cleaned_text:
      cleaned_text = original_text

    await copy_message_telethon(TARGET_CHANNEL, event.message, cleaned_text)

    source_key = (
        f'@{event.chat.username}' if event.chat.username else str(event.chat_id)
    )
    last_ids = await load_state()
    last_ids[source_key] = event.message.id
    await save_state(last_ids)
  except Exception as e:
    print(f'[!] Error copying message: {e}')


# =======================================================
# [ BOT EVENT HANDLERS ]
# =======================================================
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
    asyncio.create_task(
        notify_admin(
            sender_id,
            username,
            first_name,
            'طلب الحصول على تلجرام المميز',
            get_country_name(str(sender_id)),
        )
    )
    is_subbed = await check_subscription(sender_id)
    if is_subbed:
      buttons = [
          [Button.url('💎 تحميل تلجرام المميز ⚡', PREMIUM_URL)],
          [Button.inline('🔙 العودة للقائمة الرئيسية', data=b'main_menu')],
      ]
      await event.edit(
          f'🎉 **تهانينا! تم التحقق من اشتراكك بنجاح.**\n\n{FOOTER_TEXT}',
          buttons=buttons,
      )
    else:
      buttons = [
          [
              Button.url(
                  '📢 الاشتراك بالقناة أولاً', f'https://t.me/{CHANNEL_USERNAME}'
              )
          ],
          [Button.inline('🔄 تحقق من الاشتراك', data=b'btn_premium')],
          [Button.inline('🔙 العودة للقائمة الرئيسية', data=b'main_menu')],
      ]
      await event.edit(
          f'⚠️ **عذراً، يجب عليك الاشتراك بقناتنا أولاً!**\n\n{FOOTER_TEXT}',
          buttons=buttons,
      )

  elif data == b'btn_truecaller':
    asyncio.create_task(
        notify_admin(
            sender_id,
            username,
            first_name,
            'بدء استخدام خدمة البحث عن رقم',
            get_country_name(str(sender_id)),
        )
    )
    USER_MODES[sender_id] = 'waiting_for_truecaller_num'
    await event.edit(
        f'🔍 **أرسل الرقم للبحث عنه الآن...**\n\n{FOOTER_TEXT}',
        buttons=[[Button.inline('🔙 العودة للقائمة الرئيسية', data=b'main_menu')]],
    )


@sytc_bot.on(events.NewMessage(incoming=True))
async def sytc_bot_message_handler(event):
  if not event.is_private:
    return
  sender_id = event.sender_id
  sender = await event.get_sender()
  username = getattr(sender, 'username', None)
  first_name = getattr(sender, 'first_name', '')
  text = event.text or ''

  if text.startswith('/start'):
    USER_MODES.pop(sender_id, None)
    asyncio.create_task(save_bot_user(sender_id, username, first_name))
    asyncio.create_task(
        notify_admin(
            sender_id,
            username,
            first_name,
            'بدء استخدام النظام (/start)',
            get_country_name(str(sender_id)),
        )
    )
    await event.respond(WELCOME_TEXT, buttons=get_main_keyboard())
    return

  if USER_MODES.get(sender_id) == 'waiting_for_truecaller_num':
    USER_MODES.pop(sender_id, None)
    norm_p = normalize_phone(text)

    if norm_p in CUSTOM_RESPONSES:
      await event.respond(CUSTOM_RESPONSES[norm_p])
      return

    q_pos = truecaller_queue.qsize() + 1
    msg_text = (
        '⏳ **جاري الاستعلام عن الرقم...**'
        if q_pos == 1
        else f'⏳ **تم وضع طلبك في الترتيب ({q_pos})... يرجى الانتظار.**'
    )
    msg = await event.respond(msg_text)

    res = await fetch_truecaller_info_queued(norm_p)
    if res:
      await msg.edit(f'🔍 **النتيجة لـ ({norm_p}):**\n\n{res}\n\n{FOOTER_TEXT}')
    else:
      await msg.edit('❌ **لم يتم العثور على نتائج أو انتهت مهلة البحث.**')


# =======================================================
# [ MAIN STARTUP ]
# =======================================================
async def main():
  print('🚀 جاري بدء تشغيل النظام الشامل (الراديو + الخدمات)...')

  # 1. تشغيل خادم الراديو Flask في خيط منفصل (Daemon Thread)
  threading.Thread(target=run_flask_server, daemon=True).start()

  # 2. جلب عنوان IP المحلي لعرض روابط الاستماع للراديو
  try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('8.8.8.8', 80))
    ip = s.getsockname()[0]
    s.close()
  except Exception:
    ip = '127.0.0.1'

  print('✅ النظام يعمل!')
  print(f'🎙️ لوحة المذيع (البث الفوري): {HOST_URL}')
  print(f'🎧 صفحة المستمعين: {RADIO_URL}')

  # 3. تشغيل عملاء تيليجرام
  await client.start()
  await sytc_bot.start(bot_token=TOKEN_SYTC_BOT)
  print('✅ تم تشغيل الحسابات بنجاح.')

  # 4. تشغيل طابور Truecaller واستدراك الرسائل الفائتة
  asyncio.create_task(process_truecaller_queue())
  await catch_up_missed_messages()

  print('✅ النظام يعمل وجاهز لتلقي الرسائل والأوامر وطابور الانتظار نشط...')

  await asyncio.gather(
      client.run_until_disconnected(), sytc_bot.run_until_disconnected()
  )


if __name__ == '__main__':
  asyncio.run(main())
