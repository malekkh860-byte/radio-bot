from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

# حالة النظام العامة
state = {
    "is_broadcasting": False,
    "speak_requested": False,
    "chat_requested": False,
    "speak_granted": False,
    "listener_name": ""
}

listener_html = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>لوحة المستمع</title>
    <style>
        body { font-family: Tahoma, sans-serif; background: #121212; color: #fff; text-align: center; padding-top: 50px; }
        .btn { display: block; width: 250px; margin: 15px auto; padding: 15px; border-radius: 10px; border: none; cursor: pointer; font-size: 18px; color: white; }
        .btn-speak { background: #3498db; }
        .btn-chat { background: #9b59b6; }
        .btn-end { background: #e74c3c; display: none; }
        .status { margin-top: 20px; color: #f1c40f; font-weight: bold; font-size: 16px; }
        
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
    <h1>لوحة المستمع</h1>
    <button id="btnSpeak" class="btn btn-speak" onclick="openModal('speak')">طلب التحدث</button>
    <button id="btnChat" class="btn btn-chat" onclick="openModal('chat')">طلب المراسلة</button>
    <button id="btnEnd" class="btn btn-end" onclick="endConversation()">إنهاء المحادثة</button>
    <div id="status" class="status">الحالة: متصل</div>
    <audio id="listenerAudioPlayer" autoplay controls style="display:none; margin-top:20px;"></audio>

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

        function openModal(type) {
            currentType = type;
            document.getElementById('nameModal').style.display = 'flex';
        }

        function closeModal() {
            document.getElementById('nameModal').style.display = 'none';
            document.getElementById('listenerName'].value = '';
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
                        document.getElementById('status').innerText = "تم منح إذن الميكروفون، وإرسال الطلب باسم: " + name;
                        socket.emit('request_speak', { name: name });
                        
                        mediaRecorder = new MediaRecorder(stream);
                        mediaRecorder.ondataavailable = event => {
                            socket.emit('audio_from_listener', event.data);
                        };
                        mediaRecorder.start(200);
                    })
                    .catch(err => {
                        alert("يجب السماح للبرنامج باستخدام الميكروفون: " + err);
                    });
            } else if (currentType === 'chat') {
                document.getElementById('status').innerText = "تم إرسال طلب المراسلة باسم: " + name;
                socket.emit('request_chat', { name: name });
            }
        }

        function endConversation() {
            if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                mediaRecorder.stop();
            }
            socket.emit('end_conversation');
        }

        socket.on('speak_granted_response', (data) => {
            if (data.granted) {
                document.getElementById('status').innerText = "وافق المذيع على طلب التحدث! الصوت مفتوح الآن.";
                document.getElementById('status').style.color = "#2ecc71";
                document.getElementById('btnSpeak').style.display = 'none';
                document.getElementById('btnChat').style.display = 'none';
                document.getElementById('btnEnd').style.display = 'block';
                document.getElementById('listenerAudioPlayer').style.display = 'block';
            }
        });

        socket.on('receive_audio_from_host', (arrayBuffer) => {
            const blob = new Blob([arrayBuffer], { type: 'audio/webm' });
            const audioUrl = URL.createObjectURL(blob);
            const player = document.getElementById('listenerAudioPlayer');
            player.src = audioUrl;
            player.play().catch(e => console.log("التشغيل التلقائي يتطلب تفاعل"));
        });

        socket.on('conversation_ended', () => {
            document.getElementById('status').innerText = "تم إنهاء المحادثة.";
            document.getElementById('status').style.color = "#f1c40f";
            document.getElementById('btnSpeak').style.display = 'block';
            document.getElementById('btnChat').style.display = 'block';
            document.getElementById('btnEnd').style.display = 'none';
            document.getElementById('listenerAudioPlayer').style.display = 'none';
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
    <title>لوحة المذيع</title>
    <style>
        body { font-family: Tahoma, sans-serif; background: #1a1a1a; color: #fff; text-align: center; padding-top: 50px; }
        .btn { display: block; width: 250px; margin: 15px auto; padding: 15px; border-radius: 10px; border: none; cursor: pointer; font-size: 18px; color: white; }
        .btn-start { background: #27ae60; }
        .btn-stop { background: #c0392b; }
        .btn-accept { background: #2980b9; }
        .btn-end { background: #e74c3c; display: none; margin: 20px auto; }
        .notification { margin: 20px; font-size: 18px; color: #f39c12; font-weight: bold; }
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
</head>
<body>
    <h1>لوحة تحكم المذيع</h1>
    
    <div>
        <button class="btn btn-start" onclick="controlBroadcast('start')">بدء البث</button>
        <button class="btn btn-stop" onclick="controlBroadcast('stop')">إيقاف البث</button>
    </div>
    <div id="broadcastStatus" style="margin: 10px; color: #bdc3c7;">حالة البث: متوقف</div>

    <hr style="border: 0.5px solid #333; width: 80%; margin: 30px auto;">

    <div id="notification" class="notification">لا توجد طلبات جديدة حالياً</div>
    <div id="action_area" style="display:none;">
        <button class="btn btn-accept" onclick="grantSpeak()">قبول طلب التحدث وفتح الميكروفون</button>
    </div>
    
    <button id="btnEndHost" class="btn btn-end" onclick="endConversation()">إنهاء المحادثة</button>
    <audio id="hostAudioPlayer" autoplay controls style="display:none; margin-top:20px;"></audio>

    <script>
        const socket = io();
        let hostMediaRecorder;

        function controlBroadcast(action) {
            socket.emit('broadcast_control', { action: action });
        }

        function endConversation() {
            if (hostMediaRecorder && hostMediaRecorder.state !== 'inactive') {
                hostMediaRecorder.stop();
            }
            socket.emit('end_conversation');
        }

        socket.on('broadcast_status', (data) => {
            let statusText = data.is_running ? "البث يعمل الآن 🟢" : "البث متوقف 🔴";
            document.getElementById('broadcastStatus').innerText = "حالة البث: " + statusText;
        });

        socket.on('new_speak_request', (data) => {
            document.getElementById('notification').innerText = "هناك طلب تحدث جديد من المستمع: " + data.name;
            document.getElementById('action_area').style.display = "block";
        });

        socket.on('new_chat_request', (data) => {
            document.getElementById('notification').innerText = "هناك طلب مراسلة جديد من المستمع: " + data.name;
        });

        function grantSpeak() {
            // طلب إذن الميكروفون للمذيع عند القبول
            navigator.mediaDevices.getUserMedia({ audio: true })
                .then(stream => {
                    socket.emit('grant_speak');
                    document.getElementById('notification').innerText = "تم قبول طلب التحدث، الميكروفون يعمل الآن.";
                    document.getElementById('action_area').style.display = "none";
                    document.getElementById('btnEndHost').style.display = 'block';
                    document.getElementById('hostAudioPlayer').style.display = 'block';

                    hostMediaRecorder = new MediaRecorder(stream);
                    hostMediaRecorder.ondataavailable = event => {
                        socket.emit('audio_from_host', event.data);
                    };
                    hostMediaRecorder.start(200);
                })
                .catch(err => {
                    alert("يجب السماح للمذيع باستخدام الميكروفون: " + err);
                });
        }

        socket.on('receive_audio_from_listener', (arrayBuffer) => {
            const blob = new Blob([arrayBuffer], { type: 'audio/webm' });
            const audioUrl = URL.createObjectURL(blob);
            const player = document.getElementById('hostAudioPlayer');
            player.src = audioUrl;
            player.play().catch(e => console.log("التشغيل التلقائي تطلب تفاعلاً"));
        });

        socket.on('conversation_ended', () => {
            document.getElementById('notification').innerText = "تم إنهاء المحادثة.";
            document.getElementById('action_area').style.display = 'none';
            document.getElementById('btnEndHost').style.display = 'none';
            document.getElementById('hostAudioPlayer').style.display = 'none';
            if (hostMediaRecorder && hostMediaRecorder.state !== 'inactive') {
                hostMediaRecorder.stop();
            }
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

@socketio.on('audio_from_listener')
def handle_listener_audio(audio_data):
    emit('receive_audio_from_listener', audio_data, broadcast=True, include_self=False)

@socketio.on('audio_from_host')
def handle_host_audio(audio_data):
    emit('receive_audio_from_host', audio_data, broadcast=True, include_self=False)

@socketio.on('end_conversation')
def handle_end_conv():
    state['speak_granted'] = False
    state['speak_requested'] = False
    state['chat_requested'] = False
    emit('conversation_ended', broadcast=True)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
