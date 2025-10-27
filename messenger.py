from flask import Flask, render_template_string, request
import uuid

app = Flask(__name__)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VideoMeet - Видеоконференции</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }

        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }

        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
            width: 100%;
            max-width: 400px;
        }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }

        .header h1 {
            font-size: 28px;
            font-weight: 600;
            margin-bottom: 10px;
        }

        .header p {
            opacity: 0.9;
            font-size: 14px;
        }

        .content {
            padding: 30px;
        }

        .form-group {
            margin-bottom: 20px;
        }

        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 500;
            color: #333;
        }

        .form-group input {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e1e5e9;
            border-radius: 10px;
            font-size: 16px;
            transition: all 0.3s ease;
        }

        .form-group input:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        .btn {
            width: 100%;
            padding: 14px;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-bottom: 10px;
        }

        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }

        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
        }

        .btn-secondary {
            background: #f8f9fa;
            color: #333;
            border: 2px solid #e1e5e9;
        }

        .btn-secondary:hover {
            background: #e9ecef;
        }

        .divider {
            text-align: center;
            margin: 20px 0;
            color: #6c757d;
            font-size: 14px;
            position: relative;
        }

        .divider::before {
            content: "";
            position: absolute;
            top: 50%;
            left: 0;
            right: 0;
            height: 1px;
            background: #e1e5e9;
        }

        .divider span {
            background: white;
            padding: 0 15px;
        }

        /* Стили для комнаты */
        .room-header {
            background: #1a1a1a;
            color: white;
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .room-id {
            background: rgba(255,255,255,0.1);
            padding: 5px 10px;
            border-radius: 5px;
            font-size: 14px;
        }

        .video-container {
            background: #000;
            position: relative;
            height: 400px;
        }

        video {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }

        .local-video {
            position: absolute;
            bottom: 20px;
            right: 20px;
            width: 120px;
            height: 90px;
            border: 2px solid white;
            border-radius: 10px;
            z-index: 10;
        }

        .controls {
            background: white;
            padding: 20px;
            display: flex;
            justify-content: center;
            gap: 10px;
        }

        .control-btn {
            width: 50px;
            height: 50px;
            border-radius: 50%;
            border: none;
            background: #f8f9fa;
            color: #333;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
        }

        .control-btn:hover {
            transform: scale(1.1);
        }

        .control-btn.active {
            background: #667eea;
            color: white;
        }

        .control-btn.danger {
            background: #dc3545;
            color: white;
        }

        .invite-section {
            background: #f8f9fa;
            padding: 20px;
            border-top: 1px solid #e1e5e9;
        }

        .invite-link {
            display: flex;
            gap: 10px;
            margin-bottom: 10px;
        }

        .invite-link input {
            flex: 1;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
        }

        .copy-btn {
            background: #28a745;
            color: white;
            border: none;
            padding: 10px 15px;
            border-radius: 5px;
            cursor: pointer;
        }

        .hidden {
            display: none;
        }

        .participants {
            position: absolute;
            top: 20px;
            left: 20px;
            color: white;
            background: rgba(0,0,0,0.5);
            padding: 5px 10px;
            border-radius: 5px;
            font-size: 14px;
        }
    </style>
</head>
<body>
    {% if not room_id %}
    <!-- Главная страница -->
    <div class="container">
        <div class="header">
            <h1>🎥 VideoMeet</h1>
            <p>Бесплатные видеоконференции в один клик</p>
        </div>
        <div class="content">
            <form action="/create" method="POST">
                <div class="form-group">
                    <label for="username">Ваше имя</label>
                    <input type="text" id="username" name="username" placeholder="Введите ваше имя" required>
                </div>
                <button type="submit" class="btn btn-primary">🎯 Создать встречу</button>
            </form>

            <div class="divider"><span>или</span></div>

            <form action="/join" method="POST">
                <div class="form-group">
                    <label for="joinUsername">Ваше имя</label>
                    <input type="text" id="joinUsername" name="username" placeholder="Введите ваше имя" required>
                </div>
                <div class="form-group">
                    <label for="roomId">ID комнаты</label>
                    <input type="text" id="roomId" name="room_id" placeholder="Введите ID комнаты" required>
                </div>
                <button type="submit" class="btn btn-secondary">🔗 Присоединиться</button>
            </form>
        </div>
    </div>
    {% else %}
    <!-- Страница комнаты -->
    <div class="container" style="max-width: 800px;">
        <div class="room-header">
            <div>
                <strong>VideoMeet</strong>
                <span style="margin: 0 10px">•</span>
                <span class="room-id">ID: {{ room_id }}</span>
            </div>
            <div style="color: #00ff00;">● Живой эфир</div>
        </div>
        
        <div class="video-container">
            <div class="participants">👥 Участники: 1</div>
            <video id="remoteVideo" autoplay></video>
            <video id="localVideo" class="local-video" autoplay muted></video>
        </div>

        <div class="controls">
            <button class="control-btn active" id="toggleAudio" title="Микрофон">🎤</button>
            <button class="control-btn active" id="toggleVideo" title="Камера">📹</button>
            <button class="control-btn" id="shareScreen" title="Поделиться экраном">🖥️</button>
            <button class="control-btn danger" id="leaveCall" title="Покинуть встречу">📞</button>
        </div>

        <div class="invite-section">
            <h3 style="margin-bottom: 15px;">👋 Пригласить участников</h3>
            <div class="invite-link">
                <input type="text" id="inviteLink" value="{{ invite_link }}" readonly>
                <button class="copy-btn" onclick="copyLink()">📋 Копировать</button>
            </div>
            <p style="font-size: 12px; color: #666;">Отправьте эту ссылку участникам встречи</p>
        </div>
    </div>
    {% endif %}

    <script>
        {% if room_id %}
        // Функционал для комнаты
        let localStream;
        let videoEnabled = true;
        let audioEnabled = true;

        async function initCamera() {
            try {
                localStream = await navigator.mediaDevices.getUserMedia({ 
                    video: { width: 1280, height: 720 },
                    audio: true 
                });
                
                document.getElementById('localVideo').srcObject = localStream;
                
                // Симуляция подключения другого участника (для демо)
                setTimeout(() => {
                    document.getElementById('remoteVideo').srcObject = localStream;
                    document.querySelector('.participants').textContent = '👥 Участники: 2';
                }, 2000);
                
            } catch (error) {
                alert('Ошибка доступа к камере/микрофону: ' + error.message);
            }
        }

        // Обработчики кнопок
        document.getElementById('toggleVideo').onclick = function() {
            if (localStream) {
                const videoTrack = localStream.getVideoTracks()[0];
                videoTrack.enabled = !videoTrack.enabled;
                videoEnabled = videoTrack.enabled;
                this.classList.toggle('active', videoEnabled);
                this.textContent = videoEnabled ? '📹' : '📹❌';
            }
        };

        document.getElementById('toggleAudio').onclick = function() {
            if (localStream) {
                const audioTrack = localStream.getAudioTracks()[0];
                audioTrack.enabled = !audioTrack.enabled;
                audioEnabled = audioTrack.enabled;
                this.classList.toggle('active', audioEnabled);
                this.textContent = audioEnabled ? '🎤' : '🎤❌';
            }
        };

        document.getElementById('leaveCall').onclick = function() {
            if (confirm('Покинуть встречу?')) {
                window.location.href = '/';
            }
        };

        function copyLink() {
            const linkInput = document.getElementById('inviteLink');
            linkInput.select();
            document.execCommand('copy');
            alert('Ссылка скопирована в буфер обмена!');
        }

        // Инициализация при загрузке
        initCamera();
        {% endif %}
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/create', methods=['POST'])
def create_room():
    username = request.form['username']
    room_id = str(uuid.uuid4())[:8]
    return f'''
    <script>
        alert('Комната создана! ID: {room_id}');
        window.location.href = '/room/{room_id}?username={username}';
    </script>
    '''

@app.route('/join', methods=['POST'])
def join_room():
    username = request.form['username']
    room_id = request.form['room_id']
    return f'''
    <script>
        window.location.href = '/room/{room_id}?username={username}';
    </script>
    '''

@app.route('/room/<room_id>')
def room(room_id):
    username = request.args.get('username', 'Участник')
    invite_link = f"{request.host_url}room/{room_id}"
    
    return render_template_string(HTML_TEMPLATE, 
                                room_id=room_id, 
                                username=username,
                                invite_link=invite_link)

if __name__ == '__main__':
    print("🚀 VideoMeet запущен!")
    print("📧 Откройте: http://localhost:5000")
    print("💡 Создайте комнату и пригласите друзей!")
    app.run(host='0.0.0.0', port=5000, debug=True, load_dotenv=False)
