from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='eventlet')

# Очередь: [ { sid: ..., gender_pref: 'male'|'female'|'any' }, ... ]
waiting_queue = []

@socketio.on('find_partner')
def handle_find_partner(data):
    gender_pref = data.get('gender', 'any')
    sid = request.sid

    # Удаляем, если уже был
    global waiting_queue
    waiting_queue = [u for u in waiting_queue if u['sid'] != sid]

    # Добавляем в очередь
    waiting_queue.append({
        'sid': sid,
        'gender_pref': gender_pref
    })

    # Уведомляем пользователя
    emit('status', 'Поиск собеседника...')

    # Пробуем найти пару
    find_match()

def are_compatible(user1, user2):
    if user1['gender_pref'] == 'any' or user2['gender_pref'] == 'any':
        return True
    return user1['gender_pref'] == user2['gender_pref']

def find_match():
    if len(waiting_queue) < 2:
        return

    for i in range(len(waiting_queue)):
        for j in range(i + 1, len(waiting_queue)):
            u1 = waiting_queue[i]
            u2 = waiting_queue[j]
            if are_compatible(u1, u2):
                # Удаляем из очереди
                del waiting_queue[j]
                del waiting_queue[i]

                # Соединяем
                socketio.emit('connect_with', {'target': u2['sid']}, to=u1['sid'])
                socketio.emit('connect_with', {'target': u1['sid']}, to=u2['sid'])
                print(f"Соединение: {u1['sid']} ↔ {u2['sid']}")  # Лог
                return

@socketio.on('signal')
def handle_signal(data):
    target = data.get('target')
    payload = data.get('payload')
    if target:
        emit('signal', {'payload': payload}, to=target, include_self=False)
        print(f"Сигнал к {target}: {payload['type'] if payload else ''}")  # Лог

@socketio.on('disconnect')
def handle_disconnect():
    global waiting_queue
    waiting_queue = [u for u in waiting_queue if u['sid'] != request.sid]
    print(f"Пользователь отключён: {request.sid}")

@app.route('/')
def chat():
    return render_template('chat.html')

if __name__ == '__main__':
    # Убедись, что установлен eventlet: pip install eventlet
    socketio.run(app, host='0.0.0.0', port=5000, ssl_context='adhoc', debug=True)