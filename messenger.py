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

# Функция для определения типа устройства
def is_mobile_device(user_agent):
    mobile_keywords = ['mobile', 'android', 'iphone', 'ipad', 'tablet']
    user_agent_lower = user_agent.lower()
    return any(keyword in user_agent_lower for keyword in mobile_keywords)

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
    
    # Добавляем тестовых пользователей
    test_users = [
        ('alex', 'alex@test.com', UserManager.hash_password('123456')),
        ('maria', 'maria@test.com', UserManager.hash_password('123456')),
        ('john', 'john@test.com', UserManager.hash_password('123456'))
    ]
    
    for username, email, password_hash in test_users:
        try:
            c.execute("INSERT OR IGNORE INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                     (username, email, password_hash))
        except:
            pass
    
    conn.commit()
    conn.close()

init_db()

# HTML шаблоны (оставляем как есть)
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

# Шаблон для ПК с исправленными звонками
MESSENGER_HTML_PC = '''
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
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: #1a1a1a; z-index: 1000; display: none; flex-direction: column;
        }
        .call-header { 
            padding: 20px; color: white; text-align: center;
            background: rgba(0,0,0,0.5); 
        }
        .video-container { 
            flex: 1; display: flex; justify-content: center; align-items: center;
            position: relative; padding: 20px;
        }
        .video-wrapper { 
            position: relative; margin: 10px; 
            border-radius: 10px; overflow: hidden;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }
        .local-video-wrapper {
            position: absolute; bottom: 20px; right: 20px;
            width: 300px; height: 200px; z-index: 10;
        }
        .remote-video-wrapper {
            width: 100%; max-width: 1200px; height: 80vh;
        }
        video { 
            width: 100%; height: 100%; object-fit: cover;
            background: #000;
        }
        .video-placeholder {
            width: 100%; height: 100%; background: #2a2a2a;
            display: flex; align-items: center; justify-content: center;
            color: white; font-size: 24px;
        }
        .call-controls { 
            padding: 30px; display: flex; justify-content: center; gap: 20px;
            background: rgba(0,0,0,0.5);
        }
        .control-btn { 
            width: 70px; height: 70px; border-radius: 50%; border: none;
            cursor: pointer; display: flex; align-items: center; 
            justify-content: center; font-size: 24px;
            transition: all 0.3s ease;
        }
        .control-btn:hover { transform: scale(1.1); }
        .control-btn.end-call { background: #dc3545; color: white; }
        .control-btn.toggle-video { background: #6c757d; color: white; }
        .control-btn.toggle-audio { background: #17a2b8; color: white; }
        .control-btn.active { background: #28a745; }
        .control-btn.inactive { background: #dc3545; }
        .caller-info { 
            position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
            color: white; text-align: center; z-index: 5;
        }
        .caller-avatar {
            width: 120px; height: 120px; border-radius: 50%; background: #667eea;
            display: flex; align-items: center; justify-content: center;
            font-size: 48px; color: white; margin: 0 auto 20px;
        }
        .incoming-call-window {
            position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
            background: white; padding: 40px; border-radius: 20px; 
            box-shadow: 0 20px 60px rgba(0,0,0,0.3); z-index: 1001; 
            text-align: center; display: none;
        }
        .incoming-call-buttons { 
            display: flex; gap: 20px; justify-content: center; margin-top: 30px;
        }
        .incoming-call-btn { 
            width: 60px; height: 60px; border-radius: 50%; border: none;
            cursor: pointer; display: flex; align-items: center;
            justify-content: center; font-size: 24px;
        }
        .incoming-call-btn.accept { background: #28a745; color: white; }
        .incoming-call-btn.reject { background: #dc3545; color: white; }
        .loading { 
            text-align: center; color: #6c757d; padding: 20px;
        }
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
            <div class="contacts" id="contactsList">
                <div class="loading">Загрузка контактов...</div>
            </div>
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

    <!-- Окно входящего звонка -->
    <div class="incoming-call-window" id="incomingCallWindow">
        <div class="caller-avatar" id="incomingCallAvatar"></div>
        <h3>Входящий звонок</h3>
        <div id="callerName" style="font-size: 20px; margin: 10px 0;"></div>
        <div class="incoming-call-buttons">
            <button class="incoming-call-btn accept" onclick="acceptCall()">📞</button>
            <button class="incoming-call-btn reject" onclick="rejectCall()">✖</button>
        </div>
    </div>

    <!-- Основное окно звонка -->
    <div class="call-window" id="activeCallWindow">
        <div class="call-header">
            <h3 id="callStatus">Идет звонок с <span id="remoteUserName"></span></h3>
            <div id="callTimer">00:00</div>
        </div>
        
        <div class="video-container">
            <!-- Удаленное видео -->
            <div class="video-wrapper remote-video-wrapper">
                <video id="remoteVideo" autoplay></video>
                <div class="video-placeholder" id="remoteVideoPlaceholder">
                    <div class="caller-info">
                        <div class="caller-avatar" id="remoteUserAvatar"></div>
                        <div id="remoteUserNameText" style="font-size: 24px; margin-top: 20px;"></div>
                    </div>
                </div>
            </div>
            
            <!-- Локальное видео -->
            <div class="video-wrapper local-video-wrapper">
                <video id="localVideo" autoplay muted></video>
                <div class="video-placeholder" id="localVideoPlaceholder" style="display: none;">
                    <div>Камера выключена</div>
                </div>
            </div>
        </div>
        
        <div class="call-controls">
            <button class="control-btn toggle-audio active" id="toggleAudioBtn" onclick="toggleAudio()">
                🎤
            </button>
            <button class="control-btn toggle-video active" id="toggleVideoBtn" onclick="toggleVideo()">
                📹
            </button>
            <button class="control-btn end-call" onclick="endCall()">
                ✖
            </button>
        </div>
    </div>

    <script>
        const socket = io();
        let currentContact = null;
        let currentCallId = null;
        let localStream = null;
        let peerConnection = null;
        let isAudioEnabled = true;
        let isVideoEnabled = false;
        let callStartTime = null;
        let callTimerInterval = null;
        
        // Улучшенная конфигурация WebRTC
        const configuration = {
            iceServers: [
                { urls: 'stun:stun.l.google.com:19302' },
                { urls: 'stun:stun1.l.google.com:19302' },
                { urls: 'stun:stun2.l.google.com:19302' }
            ]
        };

        async function loadContacts() {
            try {
                const response = await fetch('/api/users');
                const contacts = await response.json();
                const contactsList = document.getElementById('contactsList');
                
                if (contacts.length === 0) {
                    contactsList.innerHTML = '<div class="loading">Контакты не найдены</div>';
                    return;
                }
                
                contactsList.innerHTML = contacts.map(contact => `
                    <div class="contact" onclick="selectContact(${contact.id}, '${contact.username}')">
                        <div class="avatar">${contact.username[0].toUpperCase()}</div>
                        <div>${contact.username}</div>
                        <div class="online-indicator" style="display: none;" id="online-${contact.id}"></div>
                    </div>
                `).join('');
                
            } catch (error) {
                console.error('Ошибка загрузки контактов:', error);
                document.getElementById('contactsList').innerHTML = 
                    '<div class="loading">Ошибка загрузки контактов</div>';
            }
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
            try {
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
            } catch (error) {
                console.error('Ошибка загрузки сообщений:', error);
            }
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
            document.getElementById('incomingCallAvatar').textContent = callerName[0].toUpperCase();
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
            document.getElementById('activeCallWindow').style.display = 'flex';
            if (currentContact) {
                document.getElementById('remoteUserName').textContent = currentContact.username;
                document.getElementById('remoteUserNameText').textContent = currentContact.username;
                document.getElementById('remoteUserAvatar').textContent = currentContact.username[0].toUpperCase();
            }
            startCallTimer();
        }

        function startCallTimer() {
            callStartTime = new Date();
            callTimerInterval = setInterval(() => {
                const now = new Date();
                const diff = new Date(now - callStartTime);
                const minutes = diff.getMinutes().toString().padStart(2, '0');
                const seconds = diff.getSeconds().toString().padStart(2, '0');
                document.getElementById('callTimer').textContent = `${minutes}:${seconds}`;
            }, 1000);
        }

        function stopCallTimer() {
            if (callTimerInterval) {
                clearInterval(callTimerInterval);
                callTimerInterval = null;
            }
        }

        function toggleAudio() {
            if (localStream) {
                const audioTracks = localStream.getAudioTracks();
                if (audioTracks.length > 0) {
                    isAudioEnabled = !isAudioEnabled;
                    audioTracks[0].enabled = isAudioEnabled;
                    const btn = document.getElementById('toggleAudioBtn');
                    if (isAudioEnabled) {
                        btn.classList.add('active');
                        btn.classList.remove('inactive');
                    } else {
                        btn.classList.remove('active');
                        btn.classList.add('inactive');
                    }
                }
            }
        }

        function toggleVideo() {
            if (localStream) {
                const videoTracks = localStream.getVideoTracks();
                if (videoTracks.length > 0) {
                    isVideoEnabled = !isVideoEnabled;
                    videoTracks[0].enabled = isVideoEnabled;
                    
                    const btn = document.getElementById('toggleVideoBtn');
                    const localVideo = document.getElementById('localVideo');
                    const localVideoPlaceholder = document.getElementById('localVideoPlaceholder');
                    
                    if (isVideoEnabled) {
                        btn.classList.add('active');
                        btn.classList.remove('inactive');
                        localVideo.style.display = 'block';
                        localVideoPlaceholder.style.display = 'none';
                    } else {
                        btn.classList.remove('active');
                        btn.classList.add('inactive');
                        localVideo.style.display = 'none';
                        localVideoPlaceholder.style.display = 'flex';
                    }
                }
            }
        }

        function endCall() {
            socket.emit('end_call', { call_id: currentCallId });
            document.getElementById('activeCallWindow').style.display = 'none';
            stopCallTimer();
            if (localStream) {
                localStream.getTracks().forEach(track => track.stop());
                localStream = null;
            }
            if (peerConnection) {
                peerConnection.close();
                peerConnection = null;
            }
            currentCallId = null;
            resetControlButtons();
        }

        function resetControlButtons() {
            document.getElementById('toggleAudioBtn').classList.add('active');
            document.getElementById('toggleAudioBtn').classList.remove('inactive');
            document.getElementById('toggleVideoBtn').classList.add('active');
            document.getElementById('toggleVideoBtn').classList.remove('inactive');
            isAudioEnabled = true;
            isVideoEnabled = false;
        }

        async function startWebRTC(isAnswerer = false) {
            try {
                console.log('Starting WebRTC connection...');
                
                // Запрашиваем медиа
                localStream = await navigator.mediaDevices.getUserMedia({ 
                    video: true,
                    audio: true 
                });
                
                console.log('Media stream obtained');
                
                // Выключаем видео по умолчанию
                const videoTracks = localStream.getVideoTracks();
                if (videoTracks.length > 0) {
                    videoTracks[0].enabled = false;
                    isVideoEnabled = false;
                    
                    const localVideo = document.getElementById('localVideo');
                    const localVideoPlaceholder = document.getElementById('localVideoPlaceholder');
                    const toggleVideoBtn = document.getElementById('toggleVideoBtn');
                    
                    localVideo.style.display = 'none';
                    localVideoPlaceholder.style.display = 'flex';
                    toggleVideoBtn.classList.remove('active');
                    toggleVideoBtn.classList.add('inactive');
                }
                
                document.getElementById('localVideo').srcObject = localStream;
                
                // Создаем новое соединение
                peerConnection = new RTCPeerConnection(configuration);
                console.log('PeerConnection created');
                
                // Добавляем треки в соединение
                localStream.getTracks().forEach(track => {
                    peerConnection.addTrack(track, localStream);
                    console.log('Added track:', track.kind);
                });
                
                // Обработчик входящих потоков
                peerConnection.ontrack = (event) => {
                    console.log('Received remote track');
                    const remoteVideo = document.getElementById('remoteVideo');
                    const remoteVideoPlaceholder = document.getElementById('remoteVideoPlaceholder');
                    
                    if (event.streams && event.streams[0]) {
                        remoteVideo.srcObject = event.streams[0];
                        remoteVideo.style.display = 'block';
                        remoteVideoPlaceholder.style.display = 'none';
                        console.log('Remote video stream set');
                    }
                };
                
                // Обработчик ICE кандидатов
                peerConnection.onicecandidate = (event) => {
                    if (event.candidate && currentContact) {
                        console.log('Sending ICE candidate');
                        socket.emit('webrtc_ice_candidate', {
                            to_user_id: currentContact.id,
                            candidate: event.candidate
                        });
                    }
                };
                
                if (!isAnswerer) {
                    // Создаем оффер
                    const offer = await peerConnection.createOffer({
                        offerToReceiveAudio: true,
                        offerToReceiveVideo: true
                    });
                    console.log('Offer created');
                    
                    await peerConnection.setLocalDescription(offer);
                    console.log('Local description set');
                    
                    socket.emit('webrtc_offer', { 
                        to_user_id: currentContact.id, 
                        offer: offer 
                    });
                    console.log('Offer sent');
                }
                
            } catch (error) {
                console.error('Error starting WebRTC:', error);
                alert('Ошибка при запуске звонка: ' + error.message);
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
            console.log('Incoming call from:', data.from_username);
            showIncomingCallWindow(data.from_username, data.call_id);
        });

        socket.on('call_accepted', (data) => {
            console.log('Call accepted by remote user');
        });

        socket.on('call_rejected', () => {
            alert('Звонок отклонен');
            document.getElementById('activeCallWindow').style.display = 'none';
            stopCallTimer();
            if (localStream) {
                localStream.getTracks().forEach(track => track.stop());
                localStream = null;
            }
        });

        socket.on('call_ended', () => {
            console.log('Call ended by remote user');
            document.getElementById('activeCallWindow').style.display = 'none';
            stopCallTimer();
            if (localStream) {
                localStream.getTracks().forEach(track => track.stop());
                localStream = null;
            }
            if (peerConnection) {
                peerConnection.close();
                peerConnection = null;
            }
        });

        socket.on('webrtc_offer', async (data) => {
            console.log('Received WebRTC offer from:', data.from_user_id);
            if (!peerConnection && currentContact && data.from_user_id === currentContact.id) {
                await startWebRTC(true);
            }
            if (peerConnection) {
                try {
                    await peerConnection.setRemoteDescription(data.offer);
                    console.log('Remote description set from offer');
                    
                    const answer = await peerConnection.createAnswer();
                    await peerConnection.setLocalDescription(answer);
                    console.log('Answer created and local description set');
                    
                    socket.emit('webrtc_answer', { 
                        to_user_id: data.from_user_id, 
                        answer: answer 
                    });
                    console.log('Answer sent');
                } catch (error) {
                    console.error('Error handling offer:', error);
                }
            }
        });

        socket.on('webrtc_answer', async (data) => {
            console.log('Received WebRTC answer from:', data.from_user_id);
            if (peerConnection) {
                try {
                    await peerConnection.setRemoteDescription(data.answer);
                    console.log('Remote description set from answer');
                } catch (error) {
                    console.error('Error handling answer:', error);
                }
            }
        });

        socket.on('webrtc_ice_candidate', async (data) => {
            console.log('Received ICE candidate from:', data.from_user_id);
            if (peerConnection) {
                try {
                    await peerConnection.addIceCandidate(data.candidate);
                    console.log('ICE candidate added');
                } catch (error) {
                    console.error('Error adding ICE candidate:', error);
                }
            }
        });

        socket.on('user_online', (data) => {
            const indicator = document.getElementById(`online-${data.user_id}`);
            if (indicator) indicator.style.display = 'block';
        });

        socket.on('user_offline', (data) => {
            const indicator = document.getElementById(`online-${data.user_id}`);
            if (indicator) indicator.style.display = 'none';
        });

        // Загружаем контакты при загрузке страницы
        document.addEventListener('DOMContentLoaded', loadContacts);
    </script>
</body>
</html>
'''

# Шаблон для мобильных устройств (упрощенный)
MESSENGER_HTML_MOBILE = '''
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
            height: 100vh;
        }
        .container { 
            width: 100%; height: 100%; background: white;
            display: flex; flex-direction: column;
        }
        .header { 
            padding: 15px; background: white; border-bottom: 1px solid #e9ecef;
            display: flex; justify-content: space-between; align-items: center;
        }
        .user-info { display: flex; align-items: center; gap: 10px; }
        .avatar { width: 40px; height: 40px; border-radius: 50%; background: #667eea; 
                 display: flex; align-items: center; justify-content: center; color: white; }
        .logout-btn { 
            background: none; border: none; color: #6c757d; cursor: pointer;
            padding: 5px 10px; border-radius: 5px; font-size: 14px;
        }
        .contacts { flex: 1; overflow-y: auto; padding: 10px; }
        .contact { 
            padding: 15px; border-radius: 10px; margin-bottom: 5px; cursor: pointer;
            display: flex; align-items: center; gap: 10px;
        }
        .contact.active { background: #667eea; color: white; }
        .loading { text-align: center; color: #6c757d; padding: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="user-info">
                <div class="avatar">{{ username[0].upper() }}</div>
                <div>
                    <div style="font-weight: bold; font-size: 16px;">{{ username }}</div>
                    <div style="font-size: 12px; color: #28a745;">● онлайн</div>
                </div>
            </div>
            <button class="logout-btn" onclick="location.href='/logout'">Выйти</button>
        </div>

        <div class="contacts" id="contactsList">
            <div class="loading">Загрузка контактов...</div>
        </div>
    </div>

    <script>
        async function loadContacts() {
            try {
                const response = await fetch('/api/users');
                const contacts = await response.json();
                const contactsList = document.getElementById('contactsList');
                
                if (contacts.length === 0) {
                    contactsList.innerHTML = '<div class="loading">Контакты не найдены</div>';
                    return;
                }
                
                contactsList.innerHTML = contacts.map(contact => `
                    <div class="contact" onclick="alert('Выбран: ${contact.username}')">
                        <div class="avatar">${contact.username[0].toUpperCase()}</div>
                        <div>${contact.username}</div>
                    </div>
                `).join('');
                
            } catch (error) {
                document.getElementById('contactsList').innerHTML = 
                    '<div class="loading">Ошибка загрузки</div>';
            }
        }

        document.addEventListener('DOMContentLoaded', loadContacts);
    </script>
</body>
</html>
'''

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
    
    user_agent = request.headers.get('User-Agent', '')
    is_mobile = is_mobile_device(user_agent)
    
    if is_mobile:
        return render_template_string(MESSENGER_HTML_MOBILE, username=session['username'])
    else:
        return render_template_string(MESSENGER_HTML_PC, username=session['username'])

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
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)
