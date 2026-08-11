from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

# الحالة العامة
state = {
    "speak_requested": False,
    "speak_granted": False
}

listener_html = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>لوحة المستمع</title>
    <style>
        body { font-family: Tahoma, sans-serif; background: #121212; color: #fff; text-align: center; padding-top: 50px; }
        .btn { width: 250px; margin: 15px; padding: 20px; border-radius: 25px; border: none; cursor: pointer; font-size: 20px; color: white; background: #3498db; }
        .status { margin-top: 25px; color: #f1c40f; font-weight: bold; font-size: 18px; }
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
</head>
<body>
    <h1>مرحباً بك في الراديو</h1>
    <button class="btn" onclick="requestSpeak()">طلب التحدث الصوتي</button>
    <div id="status" class="status">الحالة: في انتظار الطلب...</div>
    <audio id="audioPlayer" autoplay controls style="display:none; margin-top:20px;"></audio>

    <script>
        const socket = io();

        function requestSpeak() {
            socket.emit('request_speak');
            document.getElementById('status').innerText = "تم إرسال طلب التحدث، بانتظار الموافقة...";
        }

        socket.on('speak_granted_response', (data) => {
            if (data.granted) {
                document.getElementById('status').innerText = "تم قبول الطلب! جاري فتح المايكروفون...";
                document.getElementById('status').style.color = "#2ecc71";
                startMic();
            }
        });

        function startMic() {
            navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
                const mediaRecorder = new MediaRecorder(stream);
                mediaRecorder.ondataavailable = event => {
                    socket.emit('audio_stream', event.data);
                };
                mediaRecorder.start(200); // إرسال أجزاء الصوت كل 200 ميللي ثانية للتزامن الفوري
            }).catch(err => {
                alert("تعذر الوصول إلى المايكروفون: " + err);
            });
        }

        socket.on('receive_audio', (arrayBuffer) => {
            const blob = new Blob([arrayBuffer], { type: 'audio/webm' });
            const audioUrl = URL.createObjectURL(blob);
            const player = document.getElementById('audioPlayer');
            player.style.display = 'block';
            player.src = audioUrl;
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
        .btn { display: block; width: 250px; margin: 20px auto; padding: 20px; border-radius: 10px; border: none; cursor: pointer; font-size: 20px; color: white; background: #27ae60; }
        .notification { margin: 20px; font-size: 20px; color: #e74c3c; font-weight: bold; }
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
</head>
<body>
    <h1>لوحة تحكم المذيع</h1>
    <div id="notification" class="notification">لا توجد طلبات جديدة حالياً</div>
    <div id="action_area" style="display:none;">
        <button class="btn" onclick="grantSpeak()">قبول طلب التحدث وفتح الصوت</button>
    </div>
    <audio id="audioPlayer" autoplay controls style="display:none; margin-top:20px;"></audio>

    <script>
        const socket = io();

        socket.on('new_request', () => {
            document.getElementById('notification').innerText = "هناك طلب تحدث جديد بانتظار الموافقة!";
            document.getElementById('action_area').style.display = "block";
        });

        function grantSpeak() {
            socket.emit('grant_speak');
            document.getElementById('notification').innerText = "تم قبول الطلب، الصوت متصل الآن.";
            document.getElementById('action_area').style.display = "none";
            document.getElementById('audioPlayer').style.display = 'block';
        }

        socket.on('receive_audio', (arrayBuffer) => {
            const blob = new Blob([arrayBuffer], { type: 'audio/webm' });
            const audioUrl = URL.createObjectURL(blob);
            const player = document.getElementById('audioPlayer');
            player.src = audioUrl;
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

@socketio.on('request_speak')
def handle_request():
    state['speak_requested'] = True
    emit('new_request', broadcast=True)

@socketio.on('grant_speak')
def handle_grant():
    state['speak_granted'] = True
    emit('speak_granted_response', {'granted': True}, broadcast=True)

@socketio.on('audio_stream')
def handle_audio(audio_data):
    emit('receive_audio', audio_data, broadcast=True, include_self=False)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
