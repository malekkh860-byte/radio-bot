import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

state = {
    "is_broadcasting": False,
    "speak_granted": False,
    "chat_granted": False,
    "listener_name": ""
}

listener_html = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>محطة مالك خلوف الاذاعية</title>
    <style>
        body { font-family: Tahoma, sans-serif; background: #121212; color: #fff; text-align: center; padding-top: 30px; }
        h1 { color: #f39c12; text-shadow: 2px 2px 4px rgba(0,0,0,0.5); }
        .btn { display: block; width: 250px; margin: 15px auto; padding: 15px; border-radius: 10px; border: none; cursor: pointer; font-size: 18px; color: white; }
        .btn-play { background: #27ae60; font-weight: bold; }
        .btn-speak { background: #3498db; }
        .btn-chat { background: #9b59b6; }
        .btn-end { background: #e74c3c; display: none; }
        .status { margin-top: 15px; color: #f1c40f; font-weight: bold; font-size: 16px; }
        
        #chatBoxContainer { display: none; width: 90%; max-width: 400px; margin: 20px auto; background: #1e1e1e; border-radius: 10px; padding: 15px; border: 1px solid #444; text-align: right; }
        #chatMessages { height: 150px; overflow-y: scroll; background: #121212; padding: 10px; border-radius: 5px; margin-bottom: 10px; font-size: 14px; }
        .chat-input-row { display: flex; gap: 5px; }
        .chat-input-row input { flex: 1; padding: 10px; border-radius: 5px; border: 1px solid #555; background: #2a2a2a; color: #fff; }
        .chat-input-row button { padding: 10px 15px; background: #2ecc71; border: none; border-radius: 5px; color: white; cursor: pointer; }

        #nameModal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); justify-content: center; align-items: center; z-index: 1000; }
        .modal-box { background: #1e1e1e; padding: 25px; border-radius: 15px; width: 320px; text-align: center; box-shadow: 0 4px 20px rgba(0,0,0,0.5); }
        .modal-box input { width: 90%; padding: 12px; margin: 15px 0; border-radius: 8px; border: 1px solid #444; background: #2a2a2a; color: #fff; font-size: 16px; text-align: center; }
        .modal-btn { padding: 10px 20px; margin: 5px; border-radius: 8px; border: none; cursor: pointer; font-size: 16px; color: white; }
        .btn-send { background: #2ecc71; }
        .btn-back { background: #e74c3c; }
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
</head>
<body>
    <h1>📻 محطة مالك خلوف الاذاعية</h1>
    
    <button class="btn btn-play" onclick="startListeningStream()">تشغيل البث الصوتي</button>

    <button id="btnSpeak" class="btn btn-speak" onclick="openModal('speak')">طلب التحدث</button>
    <button id="btnChat" class="btn btn-chat" onclick="openModal('chat')">طلب المراسلة</button>
    <button id="btnEnd" class="btn btn-end" onclick="endConversation()">إنهاء المحادثة</button>
    
    <div id="status" class="status">الحالة: بانتظار تشغيل البث...</div>
    <audio id="listenerAudioPlayer" autoplay controls style="display:none; margin: 15px auto;"></audio>

    <div id="chatBoxContainer">
        <div id="chatMessages"></div>
        <div class="chat-input-row">
            <input type="text" id="chatInput" placeholder="اكتب رسالتك هنا..." onkeydown="if(event.key==='Enter') sendTextMessage()">
            <button onclick="sendTextMessage()">إرسال</button>
        </div>
    </div>

    <div id="nameModal">
        <div class="modal-box">
            <h3>أدخل اسمك للمتابعة</h3>
            <input type="text" id="listenerName" placeholder="اكتب اسمك هنا...">
            <br>
            <button class="modal-btn btn-send" onclick="confirmRequest()">إرسال</button>
            <button class="modal-btn btn-back" onclick="closeModal()">رجوع</button>
        </div>
    </div>

    <script>
        const socket = io();
        let currentType = '';
        let mediaRecorder;

        function startListeningStream() {
            const player = document.getElementById('listenerAudioPlayer');
            player.style.display = 'block';
            player.play().then(() => {
                document.getElementById('status').innerText = "تم تفعيل مشغل البث بنجاح 🟢";
            }).catch(err => {
                alert("اضغط على تشغيل في مشغل الصوت الظاهر للبدء");
            });
        }

        function openModal(type) {
            currentType = type;
            document.getElementById('nameModal').style.display = 'flex';
        }

        function closeModal() {
            document.getElementById('nameModal').style.display = 'none';
            document.getElementById('listenerName').value = '';
        }

        function confirmRequest() {
            let name = document.getElementById('listenerName').value.trim();
            if (!name) {
                alert("الرجاء إدخال الاسم للمتابعة!");
                return;
            }

            closeModal();

            if (currentType === 'speak') {
                navigator.mediaDevices.getUserMedia({ audio: true })
                    .then(stream => {
                        document.getElementById('status').innerText = "تم إرسال طلب التحدث باسم: " + name;
                        socket.emit('request_speak', { name: name });
                        
                        mediaRecorder = new MediaRecorder(stream);
                        mediaRecorder.ondataavailable = event => {
                            socket.emit('audio_from_listener', event.data);
                        };
                        mediaRecorder.start(200);
                    })
                    .catch(err => {
                        alert("تعذر الوصول للميكروفون: " + err);
                    });
            } else if (currentType === 'chat') {
                document.getElementById('status').innerText = "تم إرسال طلب المراسلة باسم: " + name;
                socket.emit('request_chat', { name: name });
            }
        }

        function sendTextMessage() {
            let input = document.getElementById('chatInput');
            let text = input.value.trim();
            if (!text) return;

            appendMessage("أنا: " + text, "#3498db");
            socket.emit('send_chat_message', { message: text, sender: 'listener' });
            input.value = '';
        }

        function appendMessage(text, color) {
            let container = document.getElementById('chatMessages');
            container.innerHTML += `<div style="color: ${color}; margin-bottom: 5px;">${text}</div>`;
            container.scrollTop = container.scrollHeight;
        }

        function endConversation() {
            if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                mediaRecorder.stop();
            }
            socket.emit('end_conversation');
        }

        socket.on('speak_granted_response', (data) => {
            if (data.granted) {
                document.getElementById('status').innerText = "وافق المذيع على طلب التحدث! الصوت مفتوح.";
                document.getElementById('status').style.color = "#2ecc71";
                document.getElementById('btnSpeak').style.display = 'none';
                document.getElementById('btnChat').style.display = 'none';
                document.getElementById('btnEnd').style.display = 'block';
            }
        });

        socket.on('chat_granted_response', (data) => {
            if (data.granted) {
                document.getElementById('status').innerText = "وافق المذيع على المراسلة النصية!";
                document.getElementById('status').style.color = "#2ecc71";
                document.getElementById('btnSpeak').style.display = 'none';
                document.getElementById('btnChat').style.display = 'none';
                document.getElementById('btnEnd').style.display = 'block';
                document.getElementById('chatBoxContainer').style.display = 'block';
            }
        });

        socket.on('receive_chat_message', (data) => {
            if (data.sender === 'host') {
                appendMessage("المذيع: " + data.message, "#e74c3c");
            }
        });

        socket.on('receive_audio_from_host', (arrayBuffer) => {
            const blob = new Blob([arrayBuffer], { type: 'audio/webm' });
            const audioUrl = URL.createObjectURL(blob);
            const player = document.getElementById('listenerAudioPlayer');
            player.src = audioUrl;
            player.play().catch(e => console.log("بانتظار تفاعل المستخدم"));
        });

        socket.on('conversation_ended', () => {
            document.getElementById('status').innerText = "تم إنهاء المحادثة.";
            document.getElementById('status').style.color = "#f1c40f";
            document.getElementById('btnSpeak').style.display = 'block';
            document.getElementById('btnChat').style.display = 'block';
            document.getElementById('btnEnd').style.display = 'none';
            document.getElementById('chatBoxContainer').style.display = 'none';
            document.getElementById('chatMessages').innerHTML = '';
            if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                mediaRecorder.stop();
            }
        });
    </script>
</body>
</html>
"""

host_html = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>لوحة المذيع - محطة مالك خلوف</title>
    <style>
        body { font-family: Tahoma, sans-serif; background: #1a1a1a; color: #fff; text-align: center; padding-top: 40px; }
        .btn { display: block; width: 250px; margin: 15px auto; padding: 15px; border-radius: 10px; border: none; cursor: pointer; font-size: 18px; color: white; }
        .btn-start { background: #27ae60; }
        .btn-stop { background: #c0392b; }
        .btn-accept { background: #2980b9; }
        .btn-end { background: #e74c3c; display: none; margin: 20px auto; }
        .notification { margin: 15px; font-size: 18px; color: #f39c12; font-weight: bold; }

        #hostChatContainer { display: none; width: 90%; max-width: 400px; margin: 20px auto; background: #222; border-radius: 10px; padding: 15px; border: 1px solid #444; text-align: right; }
        #hostChatMessages { height: 150px; overflow-y: scroll; background: #121212; padding: 10px; border-radius: 5px; margin-bottom: 10px; font-size: 14px; }
        .chat-input-row { display: flex; gap: 5px; }
        .chat-input-row input { flex: 1; padding: 10px; border-radius: 5px; border: 1px solid #555; background: #2a2a2a; color: #fff; }
        .chat-input-row button { padding: 10px 15px; background: #2ecc71; border: none; border-radius: 5px; color: white; cursor: pointer; }
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
</head>
<body>
    <h1>لوحة تحكم المذيع</h1>
    
    <div>
        <button class="btn btn-start" onclick="startBroadcast()">بدء البث الصوتي</button>
        <button class="btn btn-stop" onclick="stopBroadcast()">إيقاف البث</button>
    </div>
    <div id="broadcastStatus" style="margin: 10px; color: #bdc3c7;">حالة البث: متوقف</div>

    <hr style="border: 0.5px solid #333; width: 80%; margin: 20px auto;">

    <div id="notification" class="notification">لا توجد طلبات جديدة حالياً</div>
    
    <div id="action_area_speak" style="display:none;">
        <button class="btn btn-accept" onclick="grantSpeak()">قبول طلب التحدث</button>
    </div>

    <div id="action_area_chat" style="display:none;">
        <button class="btn btn-accept" onclick="grantChat()">قبول طلب المراسلة النصية</button>
    </div>
    
    <button id="btnEndHost" class="btn btn-end" onclick="endConversation()">إنهاء المحادثة</button>
    <audio id="hostAudioPlayer" autoplay controls style="display:none; margin: 15px auto;"></audio>

    <div id="hostChatContainer">
        <div id="hostChatMessages"></div>
        <div class="chat-input-row">
            <input type="text" id="hostChatInput" placeholder="اكتب رسالتك للمستمع..." onkeydown="if(event.key==='Enter') sendHostTextMessage()">
            <button onclick="sendHostTextMessage()">إرسال</button>
        </div>
    </div>

    <script>
        const socket = io();
        let hostMediaRecorder;

        function startBroadcast() {
            navigator.mediaDevices.getUserMedia({ audio: true })
                .then(stream => {
                    socket.emit('broadcast_control', { action: 'start' });
                    
                    hostMediaRecorder = new MediaRecorder(stream);
                    hostMediaRecorder.ondataavailable = event => {
                        socket.emit('audio_from_host', event.data);
                    };
                    hostMediaRecorder.start(200);
                })
                .catch(err => {
                    alert("يجب السماح للمتصفح بالوصول للميكروفون لبدء البث: " + err);
                });
        }

        function stopBroadcast() {
            if (hostMediaRecorder && hostMediaRecorder.state !== 'inactive') {
                hostMediaRecorder.stop();
            }
            socket.emit('broadcast_control', { action: 'stop' });
        }

        function endConversation() {
            socket.emit('end_conversation');
        }

        socket.on('broadcast_status', (data) => {
            let statusText = data.is_running ? "البث يعمل الآن 🟢" : "البث متوقف 🔴";
            document.getElementById('broadcastStatus').innerText = "حالة البث: " + statusText;
        });

        socket.on('new_speak_request', (data) => {
            document.getElementById('notification').innerText = "طلب تحدث من: " + data.name;
            document.getElementById('action_area_speak').style.display = "block";
            document.getElementById('action_area_chat').style.display = "none";
        });

        socket.on('new_chat_request', (data) => {
            document.getElementById('notification').innerText = "طلب مراسلة من: " + data.name;
            document.getElementById('action_area_chat').style.display = "block";
            document.getElementById('action_area_speak').style.display = "none";
        });

        function grantSpeak() {
            socket.emit('grant_speak');
            document.getElementById('notification').innerText = "تم قبول طلب التحدث.";
            document.getElementById('action_area_speak').style.display = "none";
            document.getElementById('btnEndHost').style.display = 'block';
            document.getElementById('hostAudioPlayer').style.display = 'block';
        }

        function grantChat() {
            socket.emit('grant_chat');
            document.getElementById('notification').innerText = "تم قبول طلب المراسلة النصية.";
            document.getElementById('action_area_chat').style.display = "none";
            document.getElementById('btnEndHost').style.display = 'block';
            document.getElementById('hostChatContainer').style.display = 'block';
        }

        function sendHostTextMessage() {
            let input = document.getElementById('hostChatInput');
            let text = input.value.trim();
            if (!text) return;

            appendHostMessage("أنا (المذيع): " + text, "#e74c3c");
            socket.emit('send_chat_message', { message: text, sender: 'host' });
            input.value = '';
        }

        function appendHostMessage(text, color) {
            let container = document.getElementById('hostChatMessages');
            container.innerHTML += `<div style="color: ${color}; margin-bottom: 5px;">${text}</div>`;
            container.scrollTop = container.scrollHeight;
        }

        socket.on('receive_chat_message', (data) => {
            if (data.sender === 'listener') {
                appendHostMessage("المستمع: " + data.message, "#3498db");
            }
        });

        socket.on('receive_audio_from_listener', (arrayBuffer) => {
            const blob = new Blob([arrayBuffer], { type: 'audio/webm' });
            const audioUrl = URL.createObjectURL(blob);
            const player = document.getElementById('hostAudioPlayer');
            player.src = audioUrl;
            player.play().catch(e => console.log("بانتظار تفاعل المستخدم"));
        });

        socket.on('conversation_ended', () => {
            document.getElementById('notification').innerText = "تم إنهاء المحادثة.";
            document.getElementById('action_area_speak').style.display = 'none';
            document.getElementById('action_area_chat').style.display = 'none';
            document.getElementById('btnEndHost').style.display = 'none';
            document.getElementById('hostAudioPlayer').style.display = 'none';
            document.getElementById('hostChatContainer').style.display = 'none';
            document.getElementById('hostChatMessages').innerHTML = '';
        });
    </script>
</body>
</html>
"""

@app.route('/')
def listener_panel():
    return render_template_string(listener_html)

@app.route('/host')
def host_panel():
    return render_template_string(host_html)

@socketio.on('broadcast_control')
def handle_broadcast(data):
    if data['action'] == 'start':
        state['is_broadcasting'] = True
    else:
        state['is_broadcasting'] = False
    emit('broadcast_status', {'is_running': state['is_broadcasting']}, broadcast=True)

@socketio.on('request_speak')
def handle_speak_req(data):
    state['listener_name'] = data.get('name', 'مستمع مجهول')
    emit('new_speak_request', {'name': state['listener_name']}, broadcast=True)

@socketio.on('request_chat')
def handle_chat_req(data):
    name = data.get('name', 'مستمع مجهول')
    emit('new_chat_request', {'name': name}, broadcast=True)

@socketio.on('grant_speak')
def handle_grant():
    state['speak_granted'] = True
    emit('speak_granted_response', {'granted': True}, broadcast=True)

@socketio.on('grant_chat')
def handle_grant_chat():
    state['chat_granted'] = True
    emit('chat_granted_response', {'granted': True}, broadcast=True)

@socketio.on('send_chat_message')
def handle_chat_message(data):
    emit('receive_chat_message', data, broadcast=True, include_self=False)

@socketio.on('audio_from_listener')
def handle_listener_audio(audio_data):
    emit('receive_audio_from_listener', audio_data, broadcast=True, include_self=False)

@socketio.on('audio_from_host')
def handle_host_audio(audio_data):
    emit('receive_audio_from_host', audio_data, broadcast=True, include_self=False)

@socketio.on('end_conversation')
def handle_end_conv():
    state['speak_granted'] = False
    state['chat_granted'] = False
    emit('conversation_ended', broadcast=True)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
    
