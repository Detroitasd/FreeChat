from flask import Flask, render_template_string, request, jsonify, redirect, url_for, session, flash
from flask_socketio import SocketIO, emit
import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
socketio = SocketIO(app, cors_allowed_origins="*")

# Функция для определения типа устройства
def is_mobile_device(user_agent):
    mobile_keywords = ['mobile', 'android', 'iphone', 'ipad', 'tablet']
    user_agent_lower = user_agent.lower()
    return any(keyword in user_agent_lower for keyword in mobile_keywords)

# HTML шаблоны
LOGIN_HTML = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Вход - WebMessenger</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh; display: flex; align-items: center; justify-content: center;
            padding: 20px;
        }
        .auth-container { 
            background: rgba(255, 255, 255, 0.95); 
            backdrop-filter: blur(10px);
            padding: 40px; border-radius: 20px; 
            box-shadow: 0 20px 60px rgba(0,0,0,0.15); 
            width: 100%; max-width: 400px;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .logo { 
            text-align: center; margin-bottom: 30px; 
            color: #333; font-size: 32px; font-weight: 800;
            background: linear-gradient(135deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }
        .logo-icon {
            font-size: 36px;
        }
        .form-group { margin-bottom: 20px; }
        input { 
            width: 100%; padding: 15px; 
            border: 2px solid #f1f3f4; 
            border-radius: 12px; 
            font-size: 16px; 
            background: #f8f9fa;
            transition: all 0.3s ease;
        }
        input:focus { 
            outline: none; 
            border-color: #667eea;
            background: white;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        button { 
            width: 100%; padding: 15px; 
            background: linear-gradient(135deg, #667eea, #764ba2); 
            color: white; border: none; border-radius: 12px; 
            font-size: 16px; font-weight: 600; cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        }
        button:hover { 
            transform: translateY(-2px); 
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
        }
        .links { text-align: center; margin-top: 25px; }
        .links a { 
            color: #667eea; text-decoration: none; font-weight: 500;
            transition: color 0.3s ease;
        }
        .links a:hover { color: #764ba2; }
        .error { 
            color: #e74c3c; text-align: center; margin-top: 15px;
            padding: 10px; background: rgba(231, 76, 60, 0.1);
            border-radius: 8px; border: 1px solid rgba(231, 76, 60, 0.2);
        }
        .success { 
            color: #27ae60; text-align: center; margin-top: 15px;
            padding: 10px; background: rgba(39, 174, 96, 0.1);
            border-radius: 8px; border: 1px solid rgba(39, 174, 96, 0.2);
        }
        .remember-me {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 20px;
        }
        .remember-me input {
            width: auto;
        }
    </style>
</head>
<body>
    <div class="auth-container">
        <div class="logo">
            <span class="logo-icon">💬</span>
            WebMessenger
        </div>
        <form id="loginForm">
            <div class="form-group">
                <input type="text" name="username" placeholder="Имя пользователя" required>
            </div>
            <div class="form-group">
                <input type="password" name="password" placeholder="Пароль" required>
            </div>
            <div class="remember-me">
                <input type="checkbox" id="remember" name="remember">
                <label for="remember">Запомнить меня</label>
            </div>
            <button type="submit">Войти</button>
            <div class="links">
                <a href="/register">Создать аккаунт</a>
            </div>
            <div class="error" id="error"></div>
            {% with messages = get_flashed_messages() %}
                {% if messages %}
                    <div class="success">{{ messages[0] }}</div>
                {% endif %}
            {% endwith %}
        </form>
    </div>

    <script>
        document.getElementById('loginForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const response = await fetch('/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams(formData)
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
    <title>Регистрация - WebMessenger</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh; display: flex; align-items: center; justify-content: center;
            padding: 20px;
        }
        .auth-container { 
            background: rgba(255, 255, 255, 0.95); 
            backdrop-filter: blur(10px);
            padding: 40px; border-radius: 20px; 
            box-shadow: 0 20px 60px rgba(0,0,0,0.15); 
            width: 100%; max-width: 400px;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .logo { 
            text-align: center; margin-bottom: 30px; 
            color: #333; font-size: 32px; font-weight: 800;
            background: linear-gradient(135deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }
        .logo-icon {
            font-size: 36px;
        }
        .form-group { margin-bottom: 20px; }
        input { 
            width: 100%; padding: 15px; 
            border: 2px solid #f1f3f4; 
            border-radius: 12px; 
            font-size: 16px; 
            background: #f8f9fa;
            transition: all 0.3s ease;
        }
        input:focus { 
            outline: none; 
            border-color: #667eea;
            background: white;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        button { 
            width: 100%; padding: 15px; 
            background: linear-gradient(135deg, #667eea, #764ba2); 
            color: white; border: none; border-radius: 12px; 
            font-size: 16px; font-weight: 600; cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        }
        button:hover { 
            transform: translateY(-2px); 
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
        }
        .links { text-align: center; margin-top: 25px; }
        .links a { 
            color: #667eea; text-decoration: none; font-weight: 500;
            transition: color 0.3s ease;
        }
        .links a:hover { color: #764ba2; }
        .error { 
            color: #e74c3c; text-align: center; margin-top: 15px;
            padding: 10px; background: rgba(231, 76, 60, 0.1);
            border-radius: 8px; border: 1px solid rgba(231, 76, 60, 0.2);
        }
    </style>
</head>
<body>
    <div class="auth-container">
        <div class="logo">
            <span class="logo-icon">💬</span>
            WebMessenger
        </div>
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
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams(formData)
            });
            const result = await response.json();
            
            if (result.success) {
                window.location.href = '/login?registered=true';
            } else {
                document.getElementById('error').textContent = result.error;
            }
        });
    </script>
</body>
</html>
'''

PROFILE_HTML = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Профиль - WebMessenger</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh; display: flex; align-items: center; justify-content: center;
            padding: 20px;
        }
        .profile-container { 
            background: rgba(255, 255, 255, 0.95); 
            backdrop-filter: blur(10px);
            padding: 40px; border-radius: 20px; 
            box-shadow: 0 20px 60px rgba(0,0,0,0.15); 
            width: 100%; max-width: 450px;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .logo { 
            text-align: center; margin-bottom: 30px; 
            color: #333; font-size: 28px; font-weight: 800;
            background: linear-gradient(135deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .avatar-section {
            text-align: center; margin-bottom: 30px;
        }
        .avatar {
            width: 100px; height: 100px; border-radius: 50%; 
            background: linear-gradient(135deg, #667eea, #764ba2);
            display: flex; align-items: center; justify-content: center; 
            color: white; font-size: 36px; font-weight: bold;
            margin: 0 auto 15px;
            border: 4px solid white;
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
        }
        .form-group { margin-bottom: 20px; }
        label {
            display: block; margin-bottom: 8px; font-weight: 600;
            color: #333;
        }
        input, textarea { 
            width: 100%; padding: 15px; 
            border: 2px solid #f1f3f4; 
            border-radius: 12px; 
            font-size: 16px; 
            background: #f8f9fa;
            transition: all 0.3s ease;
            font-family: inherit;
        }
        textarea {
            resize: vertical; min-height: 80px;
        }
        input:focus, textarea:focus { 
            outline: none; 
            border-color: #667eea;
            background: white;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        .button-group {
            display: flex; gap: 15px; margin-top: 25px;
        }
        button { 
            flex: 1; padding: 15px; 
            border: none; border-radius: 12px; 
            font-size: 16px; font-weight: 600; cursor: pointer;
            transition: all 0.3s ease;
        }
        .save-btn {
            background: linear-gradient(135deg, #667eea, #764ba2); 
            color: white;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        }
        .save-btn:hover { 
            transform: translateY(-2px); 
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
        }
        .back-btn {
            background: #f8f9fa; 
            color: #333;
            border: 2px solid #e9ecef;
        }
        .back-btn:hover {
            background: #e9ecef;
            transform: translateY(-2px);
        }
        .success { 
            color: #27ae60; text-align: center; margin-top: 15px;
            padding: 10px; background: rgba(39, 174, 96, 0.1);
            border-radius: 8px; border: 1px solid rgba(39, 174, 96, 0.2);
        }
        .error { 
            color: #e74c3c; text-align: center; margin-top: 15px;
            padding: 10px; background: rgba(231, 76, 60, 0.1);
            border-radius: 8px; border: 1px solid rgba(231, 76, 60, 0.2);
        }
    </style>
</head>
<body>
    <div class="profile-container">
        <div class="logo">Редактирование профиля</div>
        <div class="avatar-section">
            <div class="avatar" id="avatarPreview">{{ current_user.username[0].upper() }}</div>
        </div>
        <form id="profileForm">
            <div class="form-group">
                <label for="display_name">Отображаемое имя</label>
                <input type="text" id="display_name" name="display_name" 
                       value="{{ current_user.display_name or current_user.username }}" 
                       placeholder="Введите отображаемое имя">
            </div>
            <div class="form-group">
                <label for="bio">О себе</label>
                <textarea id="bio" name="bio" placeholder="Расскажите о себе...">{{ current_user.bio or '' }}</textarea>
            </div>
            <div class="form-group">
                <label for="phone">Телефон</label>
                <input type="tel" id="phone" name="phone" value="{{ current_user.phone or '' }}" placeholder="+7 (XXX) XXX-XX-XX">
            </div>
            <div class="button-group">
                <button type="button" class="back-btn" onclick="location.href='/messenger'">Назад</button>
                <button type="submit" class="save-btn">Сохранить</button>
            </div>
            <div class="success" id="success" style="display: none;"></div>
            <div class="error" id="error" style="display: none;"></div>
        </form>
    </div>

    <script>
        document.getElementById('profileForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const response = await fetch('/api/profile/update', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams(formData)
            });
            const result = await response.json();
            
            if (result.success) {
                document.getElementById('success').textContent = 'Профиль успешно обновлен!';
                document.getElementById('success').style.display = 'block';
                document.getElementById('error').style.display = 'none';
                
                // Обновляем аватар
                const displayName = formData.get('display_name');
                if (displayName) {
                    document.getElementById('avatarPreview').textContent = displayName[0].toUpperCase();
                }
            } else {
                document.getElementById('error').textContent = result.error;
                document.getElementById('error').style.display = 'block';
                document.getElementById('success').style.display = 'none';
            }
        });

        // Обновление аватара в реальном времени
        document.getElementById('display_name').addEventListener('input', function(e) {
            const value = e.target.value;
            if (value) {
                document.getElementById('avatarPreview').textContent = value[0].toUpperCase();
            }
        });
    </script>
</body>
</html>
'''

# Шаблон для ПК
MESSENGER_HTML_PC = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WebMessenger - {{ username }}</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh; display: flex;
        }
        .container { 
            display: flex; width: 95%; height: 95%; margin: auto; 
            background: white; border-radius: 20px; overflow: hidden;
            box-shadow: 0 25px 50px rgba(0,0,0,0.15);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .sidebar { 
            width: 380px; background: #f8fafc; border-right: 1px solid #e9ecef;
            display: flex; flex-direction: column;
        }
        .header { 
            padding: 25px; background: white; border-bottom: 1px solid #e9ecef;
            display: flex; justify-content: space-between; align-items: center;
        }
        .user-info { display: flex; align-items: center; gap: 12px; cursor: pointer; }
        .avatar { 
            width: 50px; height: 50px; border-radius: 50%; 
            background: linear-gradient(135deg, #667eea, #764ba2);
            display: flex; align-items: center; justify-content: center; 
            color: white; font-weight: bold; font-size: 18px;
            border: 3px solid white;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        .user-details { display: flex; flex-direction: column; }
        .username { font-weight: 700; color: #2d3748; font-size: 16px; }
        .status { font-size: 13px; color: #48bb78; font-weight: 500; }
        .header-buttons { display: flex; gap: 10px; }
        .header-btn { 
            background: none; border: none; color: #718096; cursor: pointer;
            padding: 8px 12px; border-radius: 10px; font-size: 16px;
            transition: all 0.3s ease;
        }
        .header-btn:hover { 
            background: #f7fafc; color: #4a5568;
            transform: translateY(-1px);
        }
        .contacts { flex: 1; overflow-y: auto; padding: 15px; }
        .contact { 
            padding: 18px; border-radius: 15px; margin-bottom: 8px; cursor: pointer;
            display: flex; align-items: center; gap: 12px; transition: all 0.3s ease;
            border: 2px solid transparent;
        }
        .contact:hover { 
            background: white; 
            border-color: #e2e8f0;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }
        .contact.active { 
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white; border-color: #667eea;
        }
        .contact-avatar {
            width: 45px; height: 45px; border-radius: 50%; 
            background: linear-gradient(135deg, #48bb78, #38a169);
            display: flex; align-items: center; justify-content: center; 
            color: white; font-weight: bold; font-size: 16px;
        }
        .contact.active .contact-avatar {
            background: rgba(255, 255, 255, 0.2);
            border: 2px solid rgba(255, 255, 255, 0.3);
        }
        .contact-details { flex: 1; }
        .contact-name { font-weight: 600; font-size: 15px; margin-bottom: 2px; }
        .contact-status { font-size: 12px; opacity: 0.7; }
        .online-indicator { 
            width: 10px; height: 10px; border-radius: 50%; background: #48bb78;
            margin-left: auto;
        }
        .chat-area { flex: 1; display: flex; flex-direction: column; }
        .chat-header { 
            padding: 25px; background: white; border-bottom: 1px solid #e9ecef;
            display: flex; justify-content: space-between; align-items: center;
        }
        .chat-user { display: flex; align-items: center; gap: 12px; }
        .call-btn { 
            background: linear-gradient(135deg, #48bb78, #38a169); 
            color: white; border: none; padding: 12px 24px;
            border-radius: 25px; cursor: pointer; display: flex; align-items: center; gap: 8px;
            font-weight: 600; font-size: 14px;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(72, 187, 120, 0.3);
        }
        .call-btn:hover { 
            transform: translateY(-2px); 
            box-shadow: 0 8px 25px rgba(72, 187, 120, 0.4);
        }
        .messages { 
            flex: 1; padding: 25px; overflow-y: auto; background: #f8fafc;
            display: flex; flex-direction: column; gap: 15px;
        }
        .message { 
            max-width: 70%; padding: 16px 20px; border-radius: 18px;
            word-wrap: break-word; position: relative;
            animation: messageAppear 0.3s ease-out;
        }
        @keyframes messageAppear {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .message.own { 
            background: linear-gradient(135deg, #667eea, #764ba2); 
            color: white; align-self: flex-end;
            border-bottom-right-radius: 5px;
        }
        .message.other { 
            background: white; align-self: flex-start;
            border: 1px solid #e9ecef; border-bottom-left-radius: 5px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        .message-time { 
            font-size: 12px; opacity: 0.7; margin-top: 5px; text-align: right;
        }
        .input-area { 
            padding: 25px; background: white; border-top: 1px solid #e9ecef;
            display: flex; gap: 12px; align-items: flex-end;
        }
        .message-input { 
            flex: 1; padding: 16px 20px; border: 2px solid #e9ecef; border-radius: 25px;
            outline: none; font-size: 15px; background: #f8f9fa;
            transition: all 0.3s ease;
            resize: none; max-height: 120px;
        }
        .message-input:focus { 
            border-color: #667eea; background: white;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        .send-btn { 
            background: linear-gradient(135deg, #667eea, #764ba2); 
            color: white; border: none; padding: 16px 24px;
            border-radius: 25px; cursor: pointer; font-weight: 600;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        }
        .send-btn:hover { 
            transform: translateY(-2px); 
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
        }
        .send-btn:disabled {
            opacity: 0.6; cursor: not-allowed; transform: none;
        }

        /* Стили для звонков */
        .call-window {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: #1a1a2e; z-index: 1000; display: none; flex-direction: column;
        }
        .call-header { 
            padding: 25px; color: white; text-align: center;
            background: rgba(0,0,0,0.5); 
        }
        .video-container { 
            flex: 1; display: flex; justify-content: center; align-items: center;
            position: relative; padding: 20px;
        }
        .video-wrapper { 
            position: relative; margin: 10px; 
            border-radius: 15px; overflow: hidden;
            box-shadow: 0 15px 35px rgba(0,0,0,0.5);
            border: 2px solid rgba(255, 255, 255, 0.1);
        }
        .local-video-wrapper {
            position: absolute; bottom: 30px; right: 30px;
            width: 320px; height: 240px; z-index: 10;
        }
        .remote-video-wrapper {
            width: 100%; max-width: 1200px; height: 80vh;
        }
        video { 
            width: 100%; height: 100%; object-fit: cover;
            background: #000;
        }
        .video-placeholder {
            width: 100%; height: 100%; background: #16213e;
            display: flex; align-items: center; justify-content: center;
            color: white; font-size: 24px;
        }
        .call-controls { 
            padding: 35px; display: flex; justify-content: center; gap: 25px;
            background: rgba(0,0,0,0.5);
        }
        .control-btn { 
            width: 80px; height: 80px; border-radius: 50%; border: none;
            cursor: pointer; display: flex; align-items: center; 
            justify-content: center; font-size: 28px;
            transition: all 0.3s ease;
            box-shadow: 0 8px 25px rgba(0,0,0,0.3);
        }
        .control-btn:hover { transform: scale(1.15); }
        .control-btn.end-call { 
            background: linear-gradient(135deg, #e53e3e, #c53030); 
            color: white; 
        }
        .control-btn.toggle-video { 
            background: linear-gradient(135deg, #718096, #4a5568); 
            color: white; 
        }
        .control-btn.toggle-audio { 
            background: linear-gradient(135deg, #3182ce, #2c5aa0); 
            color: white; 
        }
        .control-btn.active { 
            background: linear-gradient(135deg, #48bb78, #38a169); 
        }
        .control-btn.inactive { 
            background: linear-gradient(135deg, #e53e3e, #c53030); 
        }
        .caller-info { 
            position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
            color: white; text-align: center; z-index: 5;
        }
        .caller-avatar {
            width: 140px; height: 140px; border-radius: 50%; 
            background: linear-gradient(135deg, #667eea, #764ba2);
            display: flex; align-items: center; justify-content: center;
            font-size: 56px; color: white; margin: 0 auto 25px;
            border: 4px solid rgba(255, 255, 255, 0.2);
        }
        .incoming-call-window {
            position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
            background: white; padding: 50px; border-radius: 25px; 
            box-shadow: 0 30px 60px rgba(0,0,0,0.3); z-index: 1001; 
            text-align: center; display: none;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .incoming-call-buttons { 
            display: flex; gap: 25px; justify-content: center; margin-top: 35px;
        }
        .incoming-call-btn { 
            width: 70px; height: 70px; border-radius: 50%; border: none;
            cursor: pointer; display: flex; align-items: center;
            justify-content: center; font-size: 28px;
            transition: all 0.3s ease;
            box-shadow: 0 8px 25px rgba(0,0,0,0.2);
        }
        .incoming-call-btn.accept { 
            background: linear-gradient(135deg, #48bb78, #38a169); 
            color: white; 
        }
        .incoming-call-btn.reject { 
            background: linear-gradient(135deg, #e53e3e, #c53030); 
            color: white; 
        }
        .incoming-call-btn:hover { transform: scale(1.15); }
    </style>
</head>
<body>
    <div class="container">
        <div class="sidebar">
            <div class="header">
                <div class="user-info" onclick="location.href='/profile'">
                    <div class="avatar">{{ user_display_name[0].upper() if user_display_name else username[0].upper() }}</div>
                    <div class="user-details">
                        <div class="username">{{ user_display_name or username }}</div>
                        <div class="status">● онлайн</div>
                    </div>
                </div>
                <div class="header-buttons">
                    <button class="header-btn" onclick="location.href='/profile'" title="Профиль">👤</button>
                    <button class="header-btn" onclick="location.href='/logout'" title="Выйти">🚪</button>
                </div>
            </div>
            <div class="contacts" id="contactsList"></div>
        </div>

        <div class="chat-area">
            <div class="chat-header">
                <div class="chat-user">
                    <div id="currentChatUser">Выберите контакт для начала общения</div>
                </div>
                <button class="call-btn" id="callButton" style="display: none;">
                    <span>📞</span> Позвонить
                </button>
            </div>
            
            <div class="messages" id="messagesContainer">
                <div style="text-align: center; color: #a0aec0; margin-top: 50px; font-size: 16px;">
                    💬 Выберите контакт для начала общения
                </div>
            </div>
            
            <div class="input-area" id="inputArea" style="display: none;">
                <textarea class="message-input" id="messageInput" placeholder="Введите сообщение..." rows="1"></textarea>
                <button class="send-btn" id="sendButton">Отправить</button>
            </div>
        </div>
    </div>

    <!-- Окно входящего звонка -->
    <div class="incoming-call-window" id="incomingCallWindow">
        <div class="caller-avatar" id="incomingCallAvatar"></div>
        <h2 style="margin-bottom: 10px;">Входящий звонок</h2>
        <div id="callerName" style="font-size: 22px; margin: 15px 0; color: #4a5568;"></div>
        <div class="incoming-call-buttons">
            <button class="incoming-call-btn accept" onclick="acceptCall()">📞</button>
            <button class="incoming-call-btn reject" onclick="rejectCall()">✖</button>
        </div>
    </div>

    <!-- Основное окно звонка -->
    <div class="call-window" id="activeCallWindow">
        <div class="call-header">
            <h3 id="callStatus">Идет звонок с <span id="remoteUserName"></span></h3>
            <div id="callTimer" style="font-size: 18px; margin-top: 8px;">00:00</div>
        </div>
        
        <div class="video-container">
            <!-- Удаленное видео -->
            <div class="video-wrapper remote-video-wrapper">
                <video id="remoteVideo" autoplay playsinline></video>
                <div class="video-placeholder" id="remoteVideoPlaceholder">
                    <div class="caller-info">
                        <div class="caller-avatar" id="remoteUserAvatar"></div>
                        <div id="remoteUserNameText" style="font-size: 28px; margin-top: 25px;"></div>
                    </div>
                </div>
            </div>
            
            <!-- Локальное видео -->
            <div class="video-wrapper local-video-wrapper">
                <video id="localVideo" autoplay muted playsinline></video>
                <div class="video-placeholder" id="localVideoPlaceholder" style="display: none;">
                    <div style="font-size: 16px;">Камера выключена</div>
                </div>
            </div>
        </div>
        
        <div class="call-controls">
            <button class="control-btn toggle-audio active" id="toggleAudioBtn" onclick="toggleAudio()">
                🎤
            </button>
            <button class="control-btn toggle-video" id="toggleVideoBtn" onclick="toggleVideo()">
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
        let isVideoEnabled = true;
        let callStartTime = null;
        let callTimerInterval = null;
        const configuration = { 
            iceServers: [
                { urls: 'stun:stun.l.google.com:19302' },
                { urls: 'stun:stun1.l.google.com:19302' }
            ] 
        };

        // Автоматическое изменение высоты textarea
        const messageInput = document.getElementById('messageInput');
        if (messageInput) {
            messageInput.addEventListener('input', function() {
                this.style.height = 'auto';
                this.style.height = (this.scrollHeight) + 'px';
            });
        }

        async function loadContacts() {
            try {
                const response = await fetch('/api/users');
                const contacts = await response.json();
                const contactsList = document.getElementById('contactsList');
                
                contactsList.innerHTML = contacts.map(contact => `
                    <div class="contact" onclick="selectContact(${contact.id}, '${contact.username}', '${contact.display_name || contact.username}')">
                        <div class="contact-avatar">${(contact.display_name || contact.username)[0].toUpperCase()}</div>
                        <div class="contact-details">
                            <div class="contact-name">${contact.display_name || contact.username}</div>
                            <div class="contact-status">@${contact.username}</div>
                        </div>
                        <div class="online-indicator" style="display: none;" id="online-${contact.id}"></div>
                    </div>
                `).join('');
            } catch (error) {
                console.error('Error loading contacts:', error);
            }
        }

        async function selectContact(userId, username, displayName) {
            currentContact = { id: userId, username: username, displayName: displayName };
            document.querySelectorAll('.contact').forEach(c => c.classList.remove('active'));
            event.currentTarget.classList.add('active');
            document.getElementById('currentChatUser').textContent = displayName;
            document.getElementById('callButton').style.display = 'flex';
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
                console.error('Error loading messages:', error);
            }
        }

        document.getElementById('sendButton').addEventListener('click', sendMessage);
        document.getElementById('messageInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        function sendMessage() {
            const messageInput = document.getElementById('messageInput');
            const message = messageInput.value.trim();
            
            if (message && currentContact) {
                socket.emit('send_message', {
                    to_user_id: currentContact.id,
                    message: message
                });
                
                // Добавляем сообщение сразу в чат
                const messagesContainer = document.getElementById('messagesContainer');
                const now = new Date();
                const timeString = now.getHours().toString().padStart(2, '0') + ':' + now.getMinutes().toString().padStart(2, '0');
                
                messagesContainer.innerHTML += `
                    <div class="message own">
                        <div>${message}</div>
                        <div class="message-time">${timeString}</div>
                    </div>
                `;
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
                messageInput.value = '';
                messageInput.style.height = 'auto';
            }
        }

        // WebSocket обработчики сообщений
        socket.on('receive_message', (data) => {
            console.log('Received message:', data);
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

        socket.on('user_online', (data) => {
            const indicator = document.getElementById(`online-${data.user_id}`);
            if (indicator) indicator.style.display = 'block';
        });

        socket.on('user_offline', (data) => {
            const indicator = document.getElementById(`online-${data.user_id}`);
            if (indicator) indicator.style.display = 'none';
        });

        // Инициализация
        loadContacts();

        // Функции для звонков
        document.getElementById('callButton').addEventListener('click', startCall);

        async function startCall() {
            if (currentContact) {
                try {
                    await requestMediaPermissions();
                    socket.emit('start_call', { to_user_id: currentContact.id });
                    showActiveCallWindow();
                    startWebRTC(false);
                } catch (error) {
                    console.error('Error starting call:', error);
                    alert('Ошибка при запуске звонка: ' + error.message);
                }
            }
        }

        async function requestMediaPermissions() {
            try {
                localStream = await navigator.mediaDevices.getUserMedia({ 
                    video: true,
                    audio: true 
                });
                
                document.getElementById('localVideo').srcObject = localStream;
                isAudioEnabled = true;
                isVideoEnabled = true;
                
            } catch (error) {
                console.error('Error requesting media permissions:', error);
                throw new Error('Не удалось получить доступ к камере и микрофону');
            }
        }

        function showIncomingCallWindow(callerName, callId) {
            currentCallId = callId;
            document.getElementById('callerName').textContent = callerName;
            document.getElementById('incomingCallAvatar').textContent = callerName[0].toUpperCase();
            document.getElementById('incomingCallWindow').style.display = 'block';
        }

        async function acceptCall() {
            try {
                await requestMediaPermissions();
                socket.emit('accept_call', { call_id: currentCallId });
                document.getElementById('incomingCallWindow').style.display = 'none';
                showActiveCallWindow();
                startWebRTC(true);
            } catch (error) {
                console.error('Error accepting call:', error);
                alert('Ошибка при принятии звонка: ' + error.message);
                rejectCall();
            }
        }

        function rejectCall() {
            socket.emit('reject_call', { call_id: currentCallId });
            document.getElementById('incomingCallWindow').style.display = 'none';
            currentCallId = null;
        }

        function showActiveCallWindow() {
            document.getElementById('activeCallWindow').style.display = 'flex';
            if (currentContact) {
                // Используем только существующие элементы
                const remoteUserNameElement = document.getElementById('remoteUserName');
                if (remoteUserNameElement) {
                    remoteUserNameElement.textContent = currentContact.displayName;
                }
                
                // Убираем обращение к несуществующим элементам в мобильной версии
                const remoteUserNameText = document.getElementById('remoteUserNameText');
                const remoteUserAvatar = document.getElementById('remoteUserAvatar');
                
                if (remoteUserNameText) {
                    remoteUserNameText.textContent = currentContact.displayName;
                }
                if (remoteUserAvatar) {
                    remoteUserAvatar.textContent = currentContact.displayName[0].toUpperCase();
                }
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
        }

        async function startWebRTC(isAnswerer = false) {
            try {
                if (!localStream) {
                    await requestMediaPermissions();
                }
                
                peerConnection = new RTCPeerConnection(configuration);
                
                localStream.getTracks().forEach(track => {
                    peerConnection.addTrack(track, localStream);
                });
                
                peerConnection.ontrack = (event) => {
                    const remoteVideo = document.getElementById('remoteVideo');
                    const remoteVideoPlaceholder = document.getElementById('remoteVideoPlaceholder');
                    
                    if (event.streams && event.streams[0]) {
                        remoteVideo.srcObject = event.streams[0];
                        remoteVideo.style.display = 'block';
                        remoteVideoPlaceholder.style.display = 'none';
                    }
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
                    socket.emit('webrtc_offer', { 
                        to_user_id: currentContact.id, 
                        offer: offer 
                    });
                }
                
            } catch (error) {
                console.error('Error starting WebRTC:', error);
                alert('Ошибка WebRTC: ' + error.message);
                endCall();
            }
        }

        // WebSocket обработчики звонков
        socket.on('incoming_call', (data) => {
            showIncomingCallWindow(data.from_username, data.call_id);
        });

        socket.on('call_accepted', (data) => {
            // Ответчик уже начал WebRTC в acceptCall
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
            if (peerConnection) {
                try {
                    await peerConnection.setRemoteDescription(data.offer);
                    const answer = await peerConnection.createAnswer();
                    await peerConnection.setLocalDescription(answer);
                    socket.emit('webrtc_answer', { 
                        to_user_id: data.from_user_id, 
                        answer: answer 
                    });
                } catch (error) {
                    console.error('Error handling WebRTC offer:', error);
                }
            }
        });

        socket.on('webrtc_answer', async (data) => {
            if (peerConnection) {
                try {
                    await peerConnection.setRemoteDescription(data.answer);
                } catch (error) {
                    console.error('Error handling WebRTC answer:', error);
                }
            }
        });

        socket.on('webrtc_ice_candidate', async (data) => {
            if (peerConnection) {
                try {
                    await peerConnection.addIceCandidate(data.candidate);
                } catch (error) {
                    console.error('Error adding ICE candidate:', error);
                }
            }
        });
    </script>
</body>
</html>
'''

# Шаблон для мобильных устройств
MESSENGER_HTML_MOBILE = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WebMessenger - {{ username }}</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; 
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
            position: sticky; top: 0; z-index: 100;
        }
        .user-info { display: flex; align-items: center; gap: 10px; }
        .avatar { 
            width: 40px; height: 40px; border-radius: 50%; 
            background: linear-gradient(135deg, #667eea, #764ba2);
            display: flex; align-items: center; justify-content: center; 
            color: white; font-weight: bold; font-size: 16px;
        }
        .user-details { display: flex; flex-direction: column; }
        .username { font-weight: 700; color: #2d3748; font-size: 16px; }
        .status { font-size: 12px; color: #48bb78; font-weight: 500; }
        .header-buttons { display: flex; gap: 10px; }
        .header-btn { 
            background: none; border: none; color: #718096; cursor: pointer;
            padding: 8px; border-radius: 8px; font-size: 16px;
        }
        .tabs { 
            display: flex; background: #f8f9fa; 
            border-bottom: 1px solid #e9ecef;
        }
        .tab { 
            flex: 1; padding: 15px; text-align: center; cursor: pointer;
            border-bottom: 3px solid transparent;
            font-weight: 500;
        }
        .tab.active { 
            border-bottom-color: #667eea; 
            color: #667eea;
        }
        .content { 
            flex: 1; overflow: hidden; position: relative;
            background: white;
        }
        .contacts-list { 
            position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background: white; overflow-y: auto; padding: 10px;
            transition: transform 0.3s ease;
        }
        .chat-area { 
            position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background: white; display: flex; flex-direction: column;
            transition: transform 0.3s ease; transform: translateX(100%);
        }
        .chat-area.active { transform: translateX(0); }
        .contacts-list.hidden { transform: translateX(-100%); }
        .contact { 
            padding: 15px; border-radius: 12px; margin-bottom: 8px; cursor: pointer;
            display: flex; align-items: center; gap: 12px; 
            background: #f8f9fa; border: 2px solid transparent;
        }
        .contact:hover { background: #e9ecef; }
        .contact.active { 
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
        }
        .contact-avatar {
            width: 40px; height: 40px; border-radius: 50%; 
            background: linear-gradient(135deg, #48bb78, #38a169);
            display: flex; align-items: center; justify-content: center; 
            color: white; font-weight: bold; font-size: 14px;
        }
        .contact.active .contact-avatar {
            background: rgba(255, 255, 255, 0.2);
        }
        .contact-details { flex: 1; }
        .contact-name { font-weight: 600; font-size: 14px; margin-bottom: 2px; }
        .contact-status { font-size: 12px; opacity: 0.7; }
        .online-indicator { 
            width: 8px; height: 8px; border-radius: 50%; background: #48bb78;
        }
        .chat-header { 
            padding: 15px; background: white; border-bottom: 1px solid #e9ecef;
            display: flex; align-items: center; gap: 10px;
            position: sticky; top: 0; z-index: 100;
        }
        .back-btn { 
            background: none; border: none; font-size: 18px; cursor: pointer;
            color: #667eea;
        }
        .call-btn { 
            background: linear-gradient(135deg, #48bb78, #38a169); 
            color: white; border: none; padding: 8px 16px;
            border-radius: 20px; cursor: pointer; 
            font-weight: 500; font-size: 14px;
            margin-left: auto;
        }
        .messages { 
            flex: 1; padding: 15px; overflow-y: auto; background: #f8fafc;
            display: flex; flex-direction: column; gap: 10px;
        }
        .message { 
            max-width: 85%; padding: 12px 16px; border-radius: 16px;
            word-wrap: break-word;
        }
        .message.own { 
            background: linear-gradient(135deg, #667eea, #764ba2); 
            color: white; align-self: flex-end;
            border-bottom-right-radius: 5px;
        }
        .message.other { 
            background: white; align-self: flex-start;
            border: 1px solid #e9ecef; border-bottom-left-radius: 5px;
        }
        .message-time { 
            font-size: 11px; opacity: 0.7; margin-top: 4px; text-align: right;
        }
        .input-area { 
            padding: 15px; background: white; border-top: 1px solid #e9ecef;
            display: flex; gap: 10px; align-items: flex-end;
        }
        .message-input { 
            flex: 1; padding: 12px 16px; border: 2px solid #e9ecef; border-radius: 20px;
            outline: none; font-size: 14px; background: #f8f9fa;
            resize: none; max-height: 100px;
        }
        .send-btn { 
            background: linear-gradient(135deg, #667eea, #764ba2); 
            color: white; border: none; padding: 12px 16px;
            border-radius: 20px; cursor: pointer; font-weight: 500;
        }

        /* Адаптивные стили для звонков */
        .call-window {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: #1a1a2e; z-index: 1000; display: none; flex-direction: column;
        }
        .call-header { 
            padding: 20px; color: white; text-align: center;
            background: rgba(0,0,0,0.5); 
        }
        .video-container { 
            flex: 1; display: flex; flex-direction: column; 
            justify-content: center; align-items: center;
            position: relative; padding: 10px;
        }
        .video-wrapper { 
            position: relative; margin: 5px; 
            border-radius: 10px; overflow: hidden;
            border: 2px solid rgba(255, 255, 255, 0.1);
        }
        .remote-video-wrapper {
            width: 100%; height: 60vh; max-height: 70vh;
        }
        .local-video-wrapper {
            position: absolute; bottom: 60px; right: 10px;
            width: 100px; height: 150px; z-index: 10;
        }
        video { 
            width: 100%; height: 100%; object-fit: cover;
        }
        .video-placeholder {
            width: 100%; height: 100%; background: #16213e;
            display: flex; align-items: center; justify-content: center;
            color: white; font-size: 14px;
        }
        .call-controls { 
            padding: 20px; display: flex; justify-content: center; gap: 15px;
            background: rgba(0,0,0,0.5);
        }
        .control-btn { 
            width: 60px; height: 60px; border-radius: 50%; border: none;
            cursor: pointer; display: flex; align-items: center; 
            justify-content: center; font-size: 20px;
        }
        .control-btn.end-call { 
            background: linear-gradient(135deg, #e53e3e, #c53030); 
            color: white; 
        }
        .control-btn.toggle-video { 
            background: linear-gradient(135deg, #718096, #4a5568); 
            color: white; 
        }
        .control-btn.toggle-audio { 
            background: linear-gradient(135deg, #3182ce, #2c5aa0); 
            color: white; 
        }
        .control-btn.active { 
            background: linear-gradient(135deg, #48bb78, #38a169); 
        }
        .control-btn.inactive { 
            background: linear-gradient(135deg, #e53e3e, #c53030); 
        }
        .incoming-call-window {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.9); z-index: 1001; 
            display: none; flex-direction: column; justify-content: center;
            align-items: center; color: white;
        }
        .incoming-call-buttons { 
            display: flex; gap: 30px; justify-content: center; margin-top: 30px;
        }
        .incoming-call-btn { 
            width: 60px; height: 60px; border-radius: 50%; border: none;
            cursor: pointer; display: flex; align-items: center;
            justify-content: center; font-size: 24px;
        }
        .incoming-call-btn.accept { 
            background: linear-gradient(135deg, #48bb78, #38a169); 
            color: white; 
        }
        .incoming-call-btn.reject { 
            background: linear-gradient(135deg, #e53e3e, #c53030); 
            color: white; 
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="user-info" onclick="location.href='/profile'">
                <div class="avatar">{{ user_display_name[0].upper() if user_display_name else username[0].upper() }}</div>
                <div class="user-details">
                    <div class="username">{{ user_display_name or username }}</div>
                    <div class="status">● онлайн</div>
                </div>
            </div>
            <div class="header-buttons">
                <button class="header-btn" onclick="location.href='/profile'" title="Профиль">👤</button>
                <button class="header-btn" onclick="location.href='/logout'" title="Выйти">🚪</button>
            </div>
        </div>

        <div class="tabs">
            <div class="tab active" onclick="showContacts()">Контакты</div>
            <div class="tab" onclick="showChat()" id="chatTab" style="display: none;">Чат</div>
        </div>

        <div class="content">
            <div class="contacts-list" id="contactsListContainer">
                <div id="contactsList"></div>
            </div>
            
            <div class="chat-area" id="chatArea">
                <div class="chat-header">
                    <button class="back-btn" onclick="showContacts()">←</button>
                    <div id="currentChatUser" style="flex: 1; font-weight: 600;"></div>
                    <button class="call-btn" id="callButton" style="display: none;">📞</button>
                </div>
                
                <div class="messages" id="messagesContainer">
                    <div style="text-align: center; color: #a0aec0; margin-top: 50px;">
                        💬 Выберите контакт для начала общения
                    </div>
                </div>
                
                <div class="input-area" id="inputArea" style="display: none;">
                    <textarea class="message-input" id="messageInput" placeholder="Введите сообщение..." rows="1"></textarea>
                    <button class="send-btn" id="sendButton">➤</button>
                </div>
            </div>
        </div>
    </div>

    <!-- Окно входящего звонка -->
    <div class="incoming-call-window" id="incomingCallWindow">
        <div class="caller-avatar" id="incomingCallAvatar" style="width: 80px; height: 80px; border-radius: 50%; background: linear-gradient(135deg, #667eea, #764ba2); display: flex; align-items: center; justify-content: center; font-size: 32px; color: white; margin-bottom: 20px;"></div>
        <h2>Входящий звонок</h2>
        <div id="callerName" style="font-size: 20px; margin: 15px 0;"></div>
        <div class="incoming-call-buttons">
            <button class="incoming-call-btn accept" onclick="acceptCall()">📞</button>
            <button class="incoming-call-btn reject" onclick="rejectCall()">✖</button>
        </div>
    </div>

    <!-- Основное окно звонка -->
    <div class="call-window" id="activeCallWindow">
        <div class="call-header">
            <h3 id="callStatus">Идет звонок с <span id="remoteUserName"></span></h3>
            <div id="callTimer" style="font-size: 16px; margin-top: 5px;">00:00</div>
        </div>
        
        <div class="video-container">
            <!-- Удаленное видео -->
            <div class="video-wrapper remote-video-wrapper">
                <video id="remoteVideo" autoplay playsinline></video>
                <div class="video-placeholder" id="remoteVideoPlaceholder">
                    <div style="text-align: center; color: white;">
                        <div style="font-size: 48px; margin-bottom: 10px;">📱</div>
                        <div>Ожидание видео...</div>
                    </div>
                </div>
            </div>
            
            <!-- Локальное видео -->
            <div class="video-wrapper local-video-wrapper">
                <video id="localVideo" autoplay muted playsinline></video>
                <div class="video-placeholder" id="localVideoPlaceholder" style="display: none;">
                    <div style="font-size: 12px;">Камера выключена</div>
                </div>
            </div>
        </div>
        
        <div class="call-controls">
            <button class="control-btn toggle-audio active" id="toggleAudioBtn" onclick="toggleAudio()">
                🎤
            </button>
            <button class="control-btn toggle-video" id="toggleVideoBtn" onclick="toggleVideo()">
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
        let isVideoEnabled = true;
        let callStartTime = null;
        let callTimerInterval = null;
        const configuration = { 
            iceServers: [
                { urls: 'stun:stun.l.google.com:19302' },
                { urls: 'stun:stun1.l.google.com:19302' }
            ] 
        };

        function showContacts() {
            document.getElementById('contactsListContainer').classList.remove('hidden');
            document.getElementById('chatArea').classList.remove('active');
            document.querySelectorAll('.tab')[0].classList.add('active');
            document.querySelectorAll('.tab')[1].classList.remove('active');
            document.getElementById('chatTab').style.display = 'none';
        }

        function showChat() {
            document.getElementById('contactsListContainer').classList.add('hidden');
            document.getElementById('chatArea').classList.add('active');
            document.querySelectorAll('.tab')[0].classList.remove('active');
            document.querySelectorAll('.tab')[1].classList.add('active');
            document.getElementById('chatTab').style.display = 'block';
        }

        // Остальной JavaScript код аналогичен PC версии
        async function loadContacts() {
            try {
                const response = await fetch('/api/users');
                const contacts = await response.json();
                const contactsList = document.getElementById('contactsList');
                
                contactsList.innerHTML = contacts.map(contact => `
                    <div class="contact" onclick="selectContact(${contact.id}, '${contact.username}', '${contact.display_name || contact.username}')">
                        <div class="contact-avatar">${(contact.display_name || contact.username)[0].toUpperCase()}</div>
                        <div class="contact-details">
                            <div class="contact-name">${contact.display_name || contact.username}</div>
                            <div class="contact-status">@${contact.username}</div>
                        </div>
                        <div class="online-indicator" style="display: none;" id="online-${contact.id}"></div>
                    </div>
                `).join('');
            } catch (error) {
                console.error('Error loading contacts:', error);
            }
        }

        async function selectContact(userId, username, displayName) {
            currentContact = { id: userId, username: username, displayName: displayName };
            document.querySelectorAll('.contact').forEach(c => c.classList.remove('active'));
            event.currentTarget.classList.add('active');
            document.getElementById('currentChatUser').textContent = displayName;
            document.getElementById('callButton').style.display = 'block';
            document.getElementById('inputArea').style.display = 'flex';
            document.getElementById('chatTab').style.display = 'block';
            await loadMessages(userId);
            showChat();
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
                console.error('Error loading messages:', error);
            }
        }

        document.getElementById('sendButton').addEventListener('click', sendMessage);
        document.getElementById('messageInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        function sendMessage() {
            const messageInput = document.getElementById('messageInput');
            const message = messageInput.value.trim();
            
            if (message && currentContact) {
                socket.emit('send_message', {
                    to_user_id: currentContact.id,
                    message: message
                });
                
                // Добавляем сообщение сразу в чат
                const messagesContainer = document.getElementById('messagesContainer');
                const now = new Date();
                const timeString = now.getHours().toString().padStart(2, '0') + ':' + now.getMinutes().toString().padStart(2, '0');
                
                messagesContainer.innerHTML += `
                    <div class="message own">
                        <div>${message}</div>
                        <div class="message-time">${timeString}</div>
                    </div>
                `;
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
                messageInput.value = '';
                messageInput.style.height = 'auto';
            }
        }

        // WebSocket обработчики сообщений
        socket.on('receive_message', (data) => {
            console.log('Received message:', data);
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

        socket.on('user_online', (data) => {
            const indicator = document.getElementById(`online-${data.user_id}`);
            if (indicator) indicator.style.display = 'block';
        });

        socket.on('user_offline', (data) => {
            const indicator = document.getElementById(`online-${data.user_id}`);
            if (indicator) indicator.style.display = 'none';
        });

        // Инициализация
        loadContacts();

        // Остальные функции для звонков аналогичны PC версии
        document.getElementById('callButton').addEventListener('click', startCall);

        async function startCall() {
            if (currentContact) {
                try {
                    await requestMediaPermissions();
                    socket.emit('start_call', { to_user_id: currentContact.id });
                    showActiveCallWindow();
                    startWebRTC(false);
                } catch (error) {
                    console.error('Error starting call:', error);
                    alert('Ошибка при запуске звонка: ' + error.message);
                }
            }
        }

        async function requestMediaPermissions() {
            try {
                localStream = await navigator.mediaDevices.getUserMedia({ 
                    video: true,
                    audio: true 
                });
                
                document.getElementById('localVideo').srcObject = localStream;
                isAudioEnabled = true;
                isVideoEnabled = true;
                
            } catch (error) {
                console.error('Error requesting media permissions:', error);
                throw new Error('Не удалось получить доступ к камере и микрофону');
            }
        }

        function showIncomingCallWindow(callerName, callId) {
            currentCallId = callId;
            document.getElementById('callerName').textContent = callerName;
            document.getElementById('incomingCallAvatar').textContent = callerName[0].toUpperCase();
            document.getElementById('incomingCallWindow').style.display = 'flex';
        }

        async function acceptCall() {
            try {
                await requestMediaPermissions();
                socket.emit('accept_call', { call_id: currentCallId });
                document.getElementById('incomingCallWindow').style.display = 'none';
                showActiveCallWindow();
                startWebRTC(true);
            } catch (error) {
                console.error('Error accepting call:', error);
                alert('Ошибка при принятии звонка: ' + error.message);
                rejectCall();
            }
        }

        function rejectCall() {
            socket.emit('reject_call', { call_id: currentCallId });
            document.getElementById('incomingCallWindow').style.display = 'none';
            currentCallId = null;
        }

        function showActiveCallWindow() {
            document.getElementById('activeCallWindow').style.display = 'flex';
            if (currentContact) {
                // Используем только существующие элементы в мобильной версии
                const remoteUserNameElement = document.getElementById('remoteUserName');
                if (remoteUserNameElement) {
                    remoteUserNameElement.textContent = currentContact.displayName;
                }
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
        }

        async function startWebRTC(isAnswerer = false) {
            try {
                if (!localStream) {
                    await requestMediaPermissions();
                }
                
                peerConnection = new RTCPeerConnection(configuration);
                
                localStream.getTracks().forEach(track => {
                    peerConnection.addTrack(track, localStream);
                });
                
                peerConnection.ontrack = (event) => {
                    const remoteVideo = document.getElementById('remoteVideo');
                    const remoteVideoPlaceholder = document.getElementById('remoteVideoPlaceholder');
                    
                    if (event.streams && event.streams[0]) {
                        remoteVideo.srcObject = event.streams[0];
                        remoteVideo.style.display = 'block';
                        remoteVideoPlaceholder.style.display = 'none';
                    }
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
                    socket.emit('webrtc_offer', { 
                        to_user_id: currentContact.id, 
                        offer: offer 
                    });
                }
                
            } catch (error) {
                console.error('Error starting WebRTC:', error);
                alert('Ошибка WebRTC: ' + error.message);
                endCall();
            }
        }

        // WebSocket обработчики звонков
        socket.on('incoming_call', (data) => {
            showIncomingCallWindow(data.from_username, data.call_id);
        });

        socket.on('call_accepted', (data) => {
            // Ответчик уже начал WebRTC в acceptCall
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
            if (peerConnection) {
                try {
                    await peerConnection.setRemoteDescription(data.offer);
                    const answer = await peerConnection.createAnswer();
                    await peerConnection.setLocalDescription(answer);
                    socket.emit('webrtc_answer', { 
                        to_user_id: data.from_user_id, 
                        answer: answer 
                    });
                } catch (error) {
                    console.error('Error handling WebRTC offer:', error);
                }
            }
        });

        socket.on('webrtc_answer', async (data) => {
            if (peerConnection) {
                try {
                    await peerConnection.setRemoteDescription(data.answer);
                } catch (error) {
                    console.error('Error handling WebRTC answer:', error);
                }
            }
        });

        socket.on('webrtc_ice_candidate', async (data) => {
            if (peerConnection) {
                try {
                    await peerConnection.addIceCandidate(data.candidate);
                } catch (error) {
                    console.error('Error adding ICE candidate:', error);
                }
            }
        });
    </script>
</body>
</html>
'''

# База данных
def init_db():
    conn = sqlite3.connect('messenger.db', check_same_thread=False)
    c = conn.cursor()
    
    # Создаем таблицу users если её нет
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  email TEXT UNIQUE NOT NULL,
                  password_hash TEXT NOT NULL,
                  display_name TEXT,
                  bio TEXT,
                  phone TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Проверяем существование колонок и добавляем их если нужно
    c.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in c.fetchall()]
    
    if 'display_name' not in columns:
        c.execute("ALTER TABLE users ADD COLUMN display_name TEXT")
    
    if 'bio' not in columns:
        c.execute("ALTER TABLE users ADD COLUMN bio TEXT")
    
    if 'phone' not in columns:
        c.execute("ALTER TABLE users ADD COLUMN phone TEXT")
    
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
        
        # Проверяем существование колонки display_name
        c.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in c.fetchall()]
        
        if 'display_name' in columns:
            c.execute("SELECT id, username, password_hash, display_name FROM users WHERE username = ?", (username,))
        else:
            c.execute("SELECT id, username, password_hash FROM users WHERE username = ?", (username,))
            
        user = c.fetchone()
        conn.close()
        
        if user and user[2] == UserManager.hash_password(password):
            user_data = {'id': user[0], 'username': user[1]}
            if len(user) > 3:  # Если есть display_name
                user_data['display_name'] = user[3]
            return user_data
        return None
    
    @staticmethod
    def get_user_profile(user_id):
        conn = sqlite3.connect('messenger.db', check_same_thread=False)
        c = conn.cursor()
        
        # Проверяем существование колонок
        c.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in c.fetchall()]
        
        if all(col in columns for col in ['display_name', 'bio', 'phone']):
            c.execute("SELECT id, username, email, display_name, bio, phone FROM users WHERE id = ?", (user_id,))
        else:
            c.execute("SELECT id, username, email FROM users WHERE id = ?", (user_id,))
            
        user = c.fetchone()
        conn.close()
        
        if user:
            user_data = {
                'id': user[0],
                'username': user[1],
                'email': user[2]
            }
            if len(user) > 3:  # Если есть дополнительные поля
                user_data['display_name'] = user[3]
                user_data['bio'] = user[4]
                user_data['phone'] = user[5]
            return user_data
        return None
    
    @staticmethod
    def update_user_profile(user_id, display_name, bio, phone):
        conn = sqlite3.connect('messenger.db', check_same_thread=False)
        c = conn.cursor()
        try:
            # Проверяем существование колонок
            c.execute("PRAGMA table_info(users)")
            columns = [column[1] for column in c.fetchall()]
            
            if all(col in columns for col in ['display_name', 'bio', 'phone']):
                c.execute("UPDATE users SET display_name = ?, bio = ?, phone = ? WHERE id = ?",
                         (display_name, bio, phone, user_id))
            else:
                # Если колонок нет, создаем их
                if 'display_name' not in columns:
                    c.execute("ALTER TABLE users ADD COLUMN display_name TEXT")
                if 'bio' not in columns:
                    c.execute("ALTER TABLE users ADD COLUMN bio TEXT")
                if 'phone' not in columns:
                    c.execute("ALTER TABLE users ADD COLUMN phone TEXT")
                
                c.execute("UPDATE users SET display_name = ?, bio = ?, phone = ? WHERE id = ?",
                         (display_name, bio, phone, user_id))
                
            conn.commit()
            return True
        except Exception as e:
            print(f"Error updating profile: {e}")
            return False
        finally:
            conn.close()
    
    @staticmethod
    def get_all_users():
        conn = sqlite3.connect('messenger.db', check_same_thread=False)
        c = conn.cursor()
        
        # Проверяем существование колонки display_name
        c.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in c.fetchall()]
        
        if 'display_name' in columns:
            c.execute("SELECT id, username, display_name FROM users")
            users = [{'id': row[0], 'username': row[1], 'display_name': row[2]} for row in c.fetchall()]
        else:
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
        remember = request.form.get('remember') == 'on'
        
        user = UserManager.verify_user(username, password)
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['display_name'] = user.get('display_name')
            
            # Устанавливаем постоянную сессию если пользователь выбрал "Запомнить меня"
            if remember:
                session.permanent = True
            else:
                session.permanent = False
                
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Неверное имя пользователя или пароль'})
    
    # Показываем сообщение об успешной регистрации если есть
    registered = request.args.get('registered')
    if registered:
        flash('Аккаунт успешно создан! Войдите в систему.')
    
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

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_profile = UserManager.get_user_profile(session['user_id'])
    return render_template_string(PROFILE_HTML, current_user=user_profile)

@app.route('/api/profile/update', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authorized'}), 401
    
    display_name = request.form.get('display_name')
    bio = request.form.get('bio')
    phone = request.form.get('phone')
    
    if UserManager.update_user_profile(session['user_id'], display_name, bio, phone):
        session['display_name'] = display_name
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Ошибка при обновлении профиля'})

@app.route('/messenger')
def messenger():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Определяем тип устройства
    user_agent = request.headers.get('User-Agent', '')
    is_mobile = is_mobile_device(user_agent)
    
    user_profile = UserManager.get_user_profile(session['user_id'])
    
    # Выбираем соответствующий шаблон
    if is_mobile:
        return render_template_string(MESSENGER_HTML_MOBILE, 
                                   username=session['username'],
                                   user_display_name=session.get('display_name'))
    else:
        return render_template_string(MESSENGER_HTML_PC, 
                                   username=session['username'],
                                   user_display_name=session.get('display_name'))

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
    print(f"Client connected: {request.sid}")
    if 'user_id' in session:
        user_id = session['user_id']
        username = session['username']
        active_users[user_id] = request.sid
        print(f"User {username} connected with SID: {request.sid}")
        emit('user_online', {'user_id': user_id, 'username': username}, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    print(f"Client disconnected: {request.sid}")
    user_id = session.get('user_id')
    if user_id and user_id in active_users:
        username = session['username']
        del active_users[user_id]
        print(f"User {username} disconnected")
        emit('user_offline', {'user_id': user_id, 'username': username}, broadcast=True)

@socketio.on('send_message')
def handle_send_message(data):
    print(f"Received message: {data}")
    to_user_id = data['to_user_id']
    message = data['message']
    from_user_id = session['user_id']
    
    # Сохраняем сообщение в базу
    UserManager.save_message(from_user_id, to_user_id, message)
    
    # Отправляем сообщение получателю если он онлайн
    if to_user_id in active_users:
        print(f"Sending message to user {to_user_id} with SID: {active_users[to_user_id]}")
        emit('receive_message', {
            'from_user_id': from_user_id,
            'from_username': session['username'],
            'message': message,
            'timestamp': datetime.now().strftime('%H:%M')
        }, room=active_users[to_user_id])
    else:
        print(f"User {to_user_id} is offline")

@socketio.on('start_call')
def handle_start_call(data):
    to_user_id = data['to_user_id']
    from_user_id = session['user_id']
    
    call_id = secrets.token_hex(16)
    active_calls[call_id] = {
        'from_user_id': from_user_id,
        'to_user_id': to_user_id,
        'from_username': session.get('display_name') or session['username']
    }
    
    if to_user_id in active_users:
        emit('incoming_call', {
            'call_id': call_id,
            'from_user_id': from_user_id,
            'from_username': session.get('display_name') or session['username']
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
    print(f"Starting server on port {port}")
    socketio.run(app, host='0.0.0.0', port=port, debug=True, allow_unsafe_werkzeug=True)
