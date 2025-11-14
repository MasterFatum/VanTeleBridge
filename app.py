from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins='*')

# Очередь: [ { sid: ..., gender: 'male'|'female'|'any' }, ... ]
waiting_queue = []

@socketio.on('find_partner')
def handle_find_partner(data):
    gender_pref = data.get('gender', 'any')  # 'male', 'female', 'any'
    sid = request.sid

    # Удаляем из очереди, если уже был
    waiting_queue[:] = [u for u in waiting_queue if u['sid'] != sid]

    # Добавляем с предпочтением
    waiting_queue.append({'sid': sid, 'gender_pref': gender_pref})

    emit('status', 'Поиск собеседника...')

    # Попробуем подобрать пару
    find_match()

def find_match():
    if len(waiting_queue) < 2:
        return

    # Полный перебор: ищем совместимые пары
    for i, user1 in enumerate(waiting_queue):
        for j, user2 in enumerate(waiting_queue):
            if i >= j:
                continue
            if are_compatible(user1, user2):
                # Убираем из очереди
                waiting_queue.pop(i)
                waiting_queue.pop(j - 1)  # после удаления i, j сдвигается
                # Соединяем
                socketio.emit('connect_with', {'target': user2['sid']}, room=user1['sid'])
                socketio.emit('connect_with', {'target': user1['sid']}, room=user2['sid'])
                return

def are_compatible(user1, user2):
    # Правила совместимости:
    # Любой пол подходит к 'any'
    if user1['gender_pref'] == 'any' or user2['gender_pref'] == 'any':
        return True
    # Иначе должны совпадать
    return user1['gender_pref'] == user2['gender_pref']

@socketio.on('signal')
def handle_signal(data):
    target = data['target']
    payload = data['payload']
    emit('signal', payload, room=target, include_self=False)

@socketio.on('disconnect')
def handle_disconnect():
    # Удаляем при отключении
    waiting_queue[:] = [u for u in waiting_queue if u['sid'] != request.sid]

@app.route('/')
def chat():
    return render_template('chat.html')

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, ssl_context='adhoc', debug=False)