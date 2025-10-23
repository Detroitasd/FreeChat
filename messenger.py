from flask import Flask, render_template_string, request, jsonify, redirect, url_for, session
from flask_socketio import SocketIO, emit
import json
import sqlite3
import hashlib
import secrets
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
socketio = SocketIO(app, cors_allowed_origins="*")

# HTML шаблоны
LOGIN_HTML = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Вход - Мессенджер</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Arial', sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh; display: flex; align-items: center; justify-content: center;
        }
        .auth-container { 
            background: white; padding: 40px; border-radius: 15px; 
            box-shadow: 0 15px 35px rgba(0,0,0,0.1); width: 100%; max-width: 400px;
        }
        .logo { text-align: center; margin-bottom: 30px; color: #333; font-size: 28px; font-weight: bold; }
        .form-group { margin-bottom: 20px; }
        input { width: 100%; padding: 12px; border: 2px solid #e1e1e1; border-radius: 8px; font-size: 16px; }
        input:focus { outline: none; border-color: #667eea; }
        button { 
            width: 100%; padding: 12px; background: linear-gradient(135deg, #667eea, #764ba2); 
            color: white; border: none; border-radius: 8px; font-size: 16px; cursor: pointer;
            transition: transform 0.2s;
        }
        button:hover { transform: translateY(-2px); }
        .links { text-align: center; margin-top: 20px; }
        .links a { color: #667eea; text-decoration: none; }
        .error { color: #e74c3c; text-align: center; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="auth-container">
        <div class="logo">💬 WebMessenger</div>
        <form id="loginForm">
            <div class="form-group">
                <input type="text" name="username" placeholder="Имя пользователя" required>
            </div>
            <div class="form-group">
                <input type="password" name="password" placeholder="Пароль" required>
            </div>
            <button type="submit">Войти</button>
            <div class="links">
                <a href="/register">Создать аккаунт</a>
            </div>
            <div class="error" id="error"></div>
        </form>
    </div>

    <script>
        document.getElementById('loginForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const response = await fetch('/login', {
                method: 'POST',
                body: formData
            });
            const result = await response.json();
            
            if (result.success) {
                window.location.href = '/messenger';
            } else {
                document.getElementById('error').textContent = result.error;
            }
        });
    </script>
</body>
</html>
'''

REGISTER_HTML = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Регистрация - Мессенджер</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Arial', sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh; display: flex; align-items: center; justify-content: center;
        }
        .auth-container { 
            background: white; padding: 40px; border-radius: 15px; 
            box-shadow: 0 15px 35px rgba(0,0,0,0.1); width: 100%; max-width: 400px;
        }
        .logo { text-align: center; margin-bottom: 30px; color: #333; font-size: 28px; font-weight: bold; }
        .form-group { margin-bottom: 20px; }
        input { width: 100%; padding: 12px; border: 2px solid #e1e1e1; border-radius: 8px; font-size: 16px; }
        input:focus { outline: none; border-color: #667eea; }
        button { 
            width: 100%; padding: 12px; background: linear-gradient(135deg, #667eea, #764ba2); 
            color: white; border: none; border-radius: 8px; font-size: 16px; cursor: pointer;
            transition: transform 0.2s;
        }
        button:hover { transform: translateY(-2px); }
        .links { text-align: center; margin-top: 20px; }
        .links a { color: #667eea; text-decoration: none; }
        .error { color: #e74c3c; text-align: center; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="auth-container">
        <div class="logo">💬 WebMessenger</div>
        <form id="registerForm">
            <div class="form-group">
                <input type="text" name="username" placeholder="Имя пользователя" required>
            </div>
            <div class="form-group">
                <input type="email" name="email" placeholder="Email" required>
            </div>
            <div class="form-group">
                <input type="password" name="password" placeholder="Пароль" required>
            </div>
            <button type="submit">Зарегистрироваться</button>
            <div class="links">
                <a href="/login">Уже есть аккаунт?</a>
            </div>
            <div class="error" id="error"></div>
        </form>
    </div>

    <script>
        document.getElementById('registerForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const response = await fetch('/register', {
                method: 'POST',
                body: formData
            });
            const result = await response.json();
            
            if (result.success) {
                window.location.href = '/login';
            } else {
                document.getElementById('error').textContent = result.error;
            }
        });
    </script>
</body>
</html>
'''

MESSENGER_HTML = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Мессенджер - {{ username }}</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh; display: flex;
        }
        .container { 
            display: flex; width: 95%; height: 95%; margin: auto; 
            background: white; border-radius: 15px; overflow: hidden;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        }
        .sidebar { 
            width: 350px; background: #f8f9fa; border-right: 1px solid #e9ecef;
            display: flex; flex-direction: column;
        }
        .header { 
            padding: 20px; background: white; border-bottom: 1px solid #e9ecef;
            display: flex; justify-content: space-between; align-items: center;
        }
        .user-info { display: flex; align-items: center; gap: 10px; }
        .avatar { width: 40px; height: 40px; border-radius: 50%; background: #667eea; 
                 display: flex; align-items: center; justify-content: center; color: white; }
        .logout-btn { 
            background: none; border: none; color: #6c757d; cursor: pointer;
            padding: 5px 10px; border-radius: 5px;
        }
        .logout-btn:hover { background: #e9ecef; }
        .contacts { flex: 1; overflow-y: auto; padding: 10px; }
        .contact { 
            padding: 15px; border-radius: 10px; margin-bottom: 5px; cursor: pointer;
            display: flex; align-items: center; gap: 10px; transition: background 0.2s;
        }
        .contact:hover { background: #e9ecef; }
        .contact.active { background: #667eea; color: white; }
        .online-indicator { 
            width: 8px; height: 8px; border-radius: 50%; background: #28a745;
            margin-left: auto;
        }
        .chat-area { flex: 1; display: flex; flex-direction: column; }
        .chat-header { 
            padding: 20px; background: white; border-bottom: 1px solid #e9ecef;
            display: flex; justify-content: space-between; align-items: center;
        }
        .call-btn { 
            background: #28a745; color: white; border: none; padding: 8px 15px;
            border-radius: 20px; cursor: pointer; display: flex; align-items: center; gap: 5px;
        }
        .call-btn:hover { background: #218838; }
        .messages { 
            flex: 1; padding: 20px; overflow-y: auto; background: #f8f9fa;
            display: flex; flex-direction: column; gap: 10px;
        }
        .message { 
            max-width: 70%; padding: 12px 16px; border-radius: 15px;
            word-wrap: break-word;
        }
        .message.own { 
            background: #667eea; color: white; align-self: flex-end;
            border-bottom-right-radius: 5px;
        }
        .message.other { 
            background: white; align-self: flex-start;
            border: 1px solid #e9ecef; border-bottom-left-radius: 5px;
        }
        .message-time { 
            font-size: 12px; opacity: 0.7; margin-top: 5px; text-align: right;
        }
        .input-area { 
            padding: 20px; background: white; border-top: 1px solid #e9ecef;
            display: flex; gap: 10px;
        }
        .message-input { 
            flex: 1; padding: 12px; border: 1px solid #e9ecef; border-radius: 25px;
            outline: none;
        }
        .send-btn { 
            background: #667eea; color: white; border: none; padding: 12px 25px;
            border-radius: 25px; cursor: pointer;
        }
        .send-btn:hover { background: #5a6fd8; }
        .call-window {
            position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
            background: white; padding: 30px; border-radius: 15px; box-shadow: 0 20px 40px rgba(0,0,0,0.2);
            z-index: 1000; text-align: center; display: none;
        }
        .call-buttons { display: flex; gap: 10px; justify-content: center; margin-top: 20px; }
        .call-btn.accept { background: #28a745; }
        .call-btn.reject { background: #dc3545; }
        .video-container { display: flex; gap: 10px; margin-top: 20px; }
        video { width: 300px; height: 200px; background: #000; border-radius: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="sidebar">
            <div class="header">
                <div class="user-info">
                    <div class="avatar">{{ username[0].upper() }}</div>
                    <div>
                        <div style="font-weight: bold;">{{ username }}</div>
                        <div style="font-size: 12px; color: #28a745;">● онлайн</div>
                    </div>
                </div>
                <button class="logout-btn" onclick="location.href='/logout'">Выйти</button>
            </div>
            <div class="contacts" id="contactsList"></div>
        </div>

        <div class="chat-area">
            <div class="chat-header">
                <div id="currentChatUser">Выберите контакт для начала общения</div>
                <button class="call-btn" id="callButton" style="display: none;">📞 Позвонить</button>
            </div>
            
            <div class="messages" id="messagesContainer">
                <div style="text-align: center; color: #6c757d; margin-top: 50px;">
                    Выберите контакт для начала общения
                </div>
            </div>
            
            <div class="input-area" id="inputArea" style="display: none;">
                <input type="text" class="message-input" id="messageInput" placeholder="Введите сообщение...">
                <button class="send-btn" id="sendButton">Отправить</button>
            </div>
        </div>
    </div>

    <div class="call-window" id="incomingCallWindow">
        <h3>Входящий звонок</h3>
        <div id="callerName"></div>
        <div class="call-buttons">
            <button class="call-btn accept" onclick="acceptCall()">📞 Принять</button>
            <button class="call-btn reject" onclick="rejectCall()">📞 Отклонить</button>
        </div>
    </div>

    <div class="call-window" id="activeCallWindow" style="display: none;">
        <h3>Идет звонок</h3>
        <div class="video-container">
            <video id="localVideo" autoplay muted></video>
            <video id="remoteVideo" autoplay></video>
        </div>
        <div class="call-buttons">
            <button class="call-btn reject" onclick="endCall()">📞 Завершить</button>
        </div>
    </div>

    <script>
        const socket = io();
        let currentContact = null;
        let currentCallId = null;
        let localStream = null;
        let peerConnection = null;
        const configuration = { iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] };

        async function loadContacts() {
            const response = await fetch('/api/users');
            const contacts = await response.json();
            const contactsList = document.getElementById('contactsList');
            
            contactsList.innerHTML = contacts.map(contact => `
                <div class="contact" onclick="selectContact(${contact.id}, '${contact.username}')">
                    <div class="avatar">${contact.username[0].toUpperCase()}</div>
                    <div>${contact.username}</div>
                    <div class="online-indicator" style="display: none;" id="online-${contact.id}"></div>
                </div>
            `).join('');
        }

        async function selectContact(userId, username) {
            currentContact = { id: userId, username: username };
            document.querySelectorAll('.contact').forEach(c => c.classList.remove('active'));
            event.currentTarget.classList.add('active');
            document.getElementById('currentChatUser').textContent = username;
            document.getElementById('callButton').style.display = 'block';
            document.getElementById('inputArea').style.display = 'flex';
            await loadMessages(userId);
        }

        async function loadMessages(userId) {
            const response = await fetch(`/api/messages/${userId}`);
            const messages = await response.json();
            const messagesContainer = document.getElementById('messagesContainer');
            
            messagesContainer.innerHTML = messages.map(msg => `
                <div class="message ${msg.from === 'Вы' ? 'own' : 'other'}">
                    <div>${msg.message}</div>
                    <div class="message-time">${msg.time}</div>
                </div>
            `).join('');
            
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }

        document.getElementById('sendButton').addEventListener('click', sendMessage);
        document.getElementById('messageInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });

        function sendMessage() {
            const messageInput = document.getElementById('messageInput');
            const message = messageInput.value.trim();
            
            if (message && currentContact) {
                socket.emit('send_message', {
                    to_user_id: currentContact.id,
                    message: message
                });
                
                const messagesContainer = document.getElementById('messagesContainer');
                messagesContainer.innerHTML += `
                    <div class="message own">
                        <div>${message}</div>
                        <div class="message-time">${new Date().toLocaleTimeString()}</div>
                    </div>
                `;
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
                messageInput.value = '';
            }
        }

        document.getElementById('callButton').addEventListener('click', startCall);

        function startCall() {
            if (currentContact) {
                socket.emit('start_call', { to_user_id: currentContact.id });
                showActiveCallWindow();
                startWebRTC(false);
            }
        }

        function showIncomingCallWindow(callerName, callId) {
            currentCallId = callId;
            document.getElementById('callerName').textContent = callerName;
            document.getElementById('incomingCallWindow').style.display = 'block';
        }

        function acceptCall() {
            socket.emit('accept_call', { call_id: currentCallId });
            document.getElementById('incomingCallWindow').style.display = 'none';
            showActiveCallWindow();
            startWebRTC(true);
        }

        function rejectCall() {
            socket.emit('reject_call', { call_id: currentCallId });
            document.getElementById('incomingCallWindow').style.display = 'none';
            currentCallId = null;
        }

        function showActiveCallWindow() {
            document.getElementById('activeCallWindow').style.display = 'block';
        }

        function endCall() {
            socket.emit('end_call', { call_id: currentCallId });
            document.getElementById('activeCallWindow').style.display = 'none';
            if (localStream) {
                localStream.getTracks().forEach(track => track.stop());
            }
            currentCallId = null;
        }

        async function startWebRTC(isAnswerer = false) {
            try {
                localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
                document.getElementById('localVideo').srcObject = localStream;
                
                peerConnection = new RTCPeerConnection(configuration);
                localStream.getTracks().forEach(track => peerConnection.addTrack(track, localStream));
                
                peerConnection.ontrack = (event) => {
                    document.getElementById('remoteVideo').srcObject = event.streams[0];
                };
                
                peerConnection.onicecandidate = (event) => {
                    if (event.candidate && currentContact) {
                        socket.emit('webrtc_ice_candidate', {
                            to_user_id: currentContact.id,
                            candidate: event.candidate
                        });
                    }
                };
                
                if (!isAnswerer) {
                    const offer = await peerConnection.createOffer();
                    await peerConnection.setLocalDescription(offer);
                    socket.emit('webrtc_offer', { to_user_id: currentContact.id, offer: offer });
                }
                
            } catch (error) {
                console.error('Error starting WebRTC:', error);
            }
        }

        socket.on('receive_message', (data) => {
            if (currentContact && data.from_user_id === currentContact.id) {
                const messagesContainer = document.getElementById('messagesContainer');
                messagesContainer.innerHTML += `
                    <div class="message other">
                        <div>${data.message}</div>
                        <div class="message-time">${data.timestamp}</div>
                    </div>
                `;
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }
        });

        socket.on('incoming_call', (data) => {
            showIncomingCallWindow(data.from_username, data.call_id);
        });

        socket.on('call_accepted', (data) => {
            startWebRTC(false);
        });

        socket.on('call_rejected', () => {
            alert('Звонок отклонен');
            document.getElementById('activeCallWindow').style.display = 'none';
        });

        socket.on('call_ended', () => {
            document.getElementById('activeCallWindow').style.display = 'none';
            if (localStream) localStream.getTracks().forEach(track => track.stop());
        });

        socket.on('webrtc_offer', async (data) => {
            if (peerConnection) {
                await peerConnection.setRemoteDescription(data.offer);
                const answer = await peerConnection.createAnswer();
                await peerConnection.setLocalDescription(answer);
                socket.emit('webrtc_answer', { to_user_id: data.from_user_id, answer: answer });
            }
        });

        socket.on('webrtc_answer', async (data) => {
            if (peerConnection) await peerConnection.setRemoteDescription(data.answer);
        });

        socket.on('webrtc_ice_candidate', async (data) => {
            if (peerConnection) await peerConnection.addIceCandidate(data.candidate);
        });

        socket.on('user_online', (data) => {
            const indicator = document.getElementById(`online-${data.user_id}`);
            if (indicator) indicator.style.display = 'block';
        });

        socket.on('user_offline', (data) => {
            const indicator = document.getElementById(`online-${data.user_id}`);
            if (indicator) indicator.style.display = 'none';
        });

        loadContacts();
    </script>
</body>
</html>
'''

# База данных
def init_db():
    conn = sqlite3.connect('messenger.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  email TEXT UNIQUE NOT NULL,
                  password_hash TEXT NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  from_user INTEGER NOT NULL,
                  to_user INTEGER NOT NULL,
                  message TEXT NOT NULL,
                  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

# Менеджер пользователей
class UserManager:
    @staticmethod
    def hash_password(password):
        return hashlib.sha256(password.encode()).hexdigest()
    
    @staticmethod
    def create_user(username, email, password):
        conn = sqlite3.connect('messenger.db', check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                     (username, email, UserManager.hash_password(password)))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    @staticmethod
    def verify_user(username, password):
        conn = sqlite3.connect('messenger.db', check_same_thread=False)
        c = conn.cursor()
        c.execute("SELECT id, username, password_hash FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        conn.close()
        
        if user and user[2] == UserManager.hash_password(password):
            return {'id': user[0], 'username': user[1]}
        return None
    
    @staticmethod
    def get_all_users():
        conn = sqlite3.connect('messenger.db', check_same_thread=False)
        c = conn.cursor()
        c.execute("SELECT id, username FROM users")
        users = [{'id': row[0], 'username': row[1]} for row in c.fetchall()]
        conn.close()
        return users
    
    @staticmethod
    def save_message(from_user, to_user, message):
        conn = sqlite3.connect('messenger.db', check_same_thread=False)
        c = conn.cursor()
        c.execute("INSERT INTO messages (from_user, to_user, message) VALUES (?, ?, ?)",
                 (from_user, to_user, message))
        conn.commit()
        conn.close()
    
    @staticmethod
    def get_message_history(user1, user2):
        conn = sqlite3.connect('messenger.db', check_same_thread=False)
        c = conn.cursor()
        c.execute('''SELECT u.username, m.message, m.timestamp 
                    FROM messages m
                    JOIN users u ON m.from_user = u.id
                    WHERE (m.from_user = ? AND m.to_user = ?) OR (m.from_user = ? AND m.to_user = ?)
                    ORDER BY m.timestamp''',
                 (user1, user2, user2, user1))
        messages = []
        for row in c.fetchall():
            from_user = 'Вы' if row[0] == session.get('username') else row[0]
            messages.append({'from': from_user, 'message': row[1], 'time': row[2][11:16]})
        conn.close()
        return messages

# Хранилища
active_users = {}
active_calls = {}

# Маршруты Flask
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('messenger'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = UserManager.verify_user(username, password)
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Неверное имя пользователя или пароль'})
    return render_template_string(LOGIN_HTML)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        if UserManager.create_user(username, email, password):
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Пользователь с таким именем или email уже существует'})
    return render_template_string(REGISTER_HTML)

@app.route('/messenger')
def messenger():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template_string(MESSENGER_HTML, username=session['username'])

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/api/users')
def get_users():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authorized'}), 401
    users = [user for user in UserManager.get_all_users() if user['id'] != session['user_id']]
    return jsonify(users)

@app.route('/api/messages/<int:other_user_id>')
def get_messages(other_user_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authorized'}), 401
    messages = UserManager.get_message_history(session['user_id'], other_user_id)
    return jsonify(messages)

# WebSocket события
@socketio.on('connect')
def handle_connect():
    if 'user_id' in session:
        user_id = session['user_id']
        username = session['username']
        active_users[user_id] = request.sid
        emit('user_online', {'user_id': user_id, 'username': username}, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    user_id = session.get('user_id')
    if user_id and user_id in active_users:
        username = session['username']
        del active_users[user_id]
        emit('user_offline', {'user_id': user_id, 'username': username}, broadcast=True)

@socketio.on('send_message')
def handle_send_message(data):
    to_user_id = data['to_user_id']
    message = data['message']
    from_user_id = session['user_id']
    
    UserManager.save_message(from_user_id, to_user_id, message)
    
    if to_user_id in active_users:
        emit('receive_message', {
            'from_user_id': from_user_id,
            'from_username': session['username'],
            'message': message,
            'timestamp': datetime.now().strftime('%H:%M')
        }, room=active_users[to_user_id])

@socketio.on('start_call')
def handle_start_call(data):
    to_user_id = data['to_user_id']
    from_user_id = session['user_id']
    
    call_id = secrets.token_hex(16)
    active_calls[call_id] = {
        'from_user_id': from_user_id,
        'to_user_id': to_user_id,
        'from_username': session['username']
    }
    
    if to_user_id in active_users:
        emit('incoming_call', {
            'call_id': call_id,
            'from_user_id': from_user_id,
            'from_username': session['username']
        }, room=active_users[to_user_id])

@socketio.on('accept_call')
def handle_accept_call(data):
    call_id = data['call_id']
    if call_id in active_calls:
        call_data = active_calls[call_id]
        from_user_id = call_data['from_user_id']
        if from_user_id in active_users:
            emit('call_accepted', {'call_id': call_id}, room=active_users[from_user_id])

@socketio.on('reject_call')
def handle_reject_call(data):
    call_id = data['call_id']
    if call_id in active_calls:
        call_data = active_calls[call_id]
        from_user_id = call_data['from_user_id']
        if from_user_id in active_users:
            emit('call_rejected', room=active_users[from_user_id])
        del active_calls[call_id]

@socketio.on('end_call')
def handle_end_call(data):
    call_id = data['call_id']
    if call_id in active_calls:
        call_data = active_calls[call_id]
        from_user_id = call_data['from_user_id']
        to_user_id = call_data['to_user_id']
        if from_user_id in active_users:
            emit('call_ended', room=active_users[from_user_id])
        if to_user_id in active_users:
            emit('call_ended', room=active_users[to_user_id])
        del active_calls[call_id]

@socketio.on('webrtc_offer')
def handle_webrtc_offer(data):
    to_user_id = data['to_user_id']
    if to_user_id in active_users:
        emit('webrtc_offer', {
            'offer': data['offer'],
            'from_user_id': session['user_id']
        }, room=active_users[to_user_id])

@socketio.on('webrtc_answer')
def handle_webrtc_answer(data):
    to_user_id = data['to_user_id']
    if to_user_id in active_users:
        emit('webrtc_answer', {
            'answer': data['answer'],
            'from_user_id': session['user_id']
        }, room=active_users[to_user_id])

@socketio.on('webrtc_ice_candidate')
def handle_webrtc_ice_candidate(data):
    to_user_id = data['to_user_id']
    if to_user_id in active_users:
        emit('webrtc_ice_candidate', {
            'candidate': data['candidate'],
            'from_user_id': session['user_id']
        }, room=active_users[to_user_id])

if __name__ == '__main__':
    print("Запуск мессенджера...")
    print("Откройте http://localhost:5000 в браузере")
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)