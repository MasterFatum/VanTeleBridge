from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='threading')

# Очередь: [ { sid: ..., country_pref: 'am'|'de'|...|'any', gender_pref: 'male'|'female'|'any' }, ... ]
waiting_queue = []

@socketio.on('connect')
def handle_connect():
    pass

@socketio.on('join_room')
def handle_join_room(data):
    room = data.get('room')
    if room:
        from flask_socketio import join_room
        join_room(room)

@socketio.on('leave_room')
def handle_leave_room(data):
    room = data.get('room')
    if room:
        from flask_socketio import leave_room
        leave_room(room)

@socketio.on('find_partner')
def handle_find_partner(data):
    country_pref = data.get('country', 'any')
    gender_pref = data.get('gender', 'any')
    sid = request.sid

    # Удаляем, если уже был
    global waiting_queue
    waiting_queue = [u for u in waiting_queue if u['sid'] != sid]

    # Добавляем в очередь
    waiting_queue.append({
        'sid': sid,
        'country_pref': country_pref,
        'gender_pref': gender_pref
    })

    # Уведомляем пользователя
    emit('status', 'Поиск собеседника...')
    find_match()

def are_compatible(user1, user2):
    country_match = user1['country_pref'] == 'any' or user2['country_pref'] == 'any' or user1['country_pref'] == user2['country_pref']
    gender_match = user1['gender_pref'] == 'any' or user2['gender_pref'] == 'any' or user1['gender_pref'] == user2['gender_pref']
    return country_match and gender_match

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
                socketio.emit('connect_with', {'target': u2['sid']}, room=u1['sid'])
                socketio.emit('connect_with', {'target': u1['sid']}, room=u2['sid'])
                return

@socketio.on('signal')
def handle_signal(data):
    target = data.get('target')
    payload = data.get('payload')
    if target:
        socketio.emit('signal', {'payload': payload}, room=target, include_self=False)

@socketio.on('disconnect')
def handle_disconnect():
    global waiting_queue
    waiting_queue = [u for u in waiting_queue if u['sid'] != request.sid]
    socketio.emit('partner_disconnected')

@socketio.on('hangup')
def handle_hangup():
    socketio.emit('partner_disconnected')

@socketio.on('chat_message')
def handle_chat_message(data):
    target = data.get('target')
    text = data.get('text')
    if target and text:
        socketio.emit('chat_message', {'text': text}, room=target, include_self=False)

@app.route('/')
def chat():
    return render_template('chat.html', active_page='home')

@app.route('/rules')
def rules():
    return render_template('rules.html', active_page='rules')

@app.route('/contacts')
def contacts():
    return render_template('contacts.html', active_page='contacts')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html', active_page='privacy')

if __name__ == '__main__':
    # Убедись, что установлен eventlet: pip install eventlet
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)