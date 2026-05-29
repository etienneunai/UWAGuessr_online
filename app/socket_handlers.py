from flask import request
from flask_socketio import emit, join_room, leave_room
from app import socketio, db
from app.models import Challenge, User
from flask_login import current_user

# Keep track of active connections: map user_id -> socket_sid
# and also map socket_sid -> user_id, challenge_id for easy cleanup on disconnect
connected_users = {}  # user_id -> sid
sid_to_user = {}      # sid -> {'user_id': user_id, 'challenge_id': challenge_id}

@socketio.on('connect')
def handle_connect():
    if not current_user.is_authenticated:
        return False  # Reject connection
    connected_users[current_user.uid] = request.sid
    sid_to_user[request.sid] = {'user_id': current_user.uid, 'challenge_id': None}

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    if sid in sid_to_user:
        info = sid_to_user[sid]
        user_id = info['user_id']
        challenge_id = info['challenge_id']
        
        # Remove from connected tracking
        if user_id in connected_users and connected_users[user_id] == sid:
            del connected_users[user_id]
        del sid_to_user[sid]
        
        if challenge_id:
            room = f"challenge_{challenge_id}"
            user = User.query.get(user_id)
            username = user.username if user else "Opponent"
            # Emit player disconnected event
            emit('opponent_disconnected', {'user_id': user_id, 'username': username}, room=room, include_self=False)

@socketio.on('join_challenge')
def handle_join_challenge(data):
    challenge_id = data.get('challenge_id')
    if not challenge_id:
        return
    
    challenge = Challenge.query.get(challenge_id)
    if not challenge:
        return
        
    if current_user.uid not in [challenge.challenger_id, challenge.challenged_id]:
        return
    
    room = f"challenge_{challenge_id}"
    join_room(room)
    
    # Emit player reconnected event
    emit('opponent_reconnected', {'user_id': current_user.uid, 'username': current_user.username}, room=room, include_self=False)
    
    # Update tracking
    sid = request.sid
    if sid in sid_to_user:
        sid_to_user[sid]['challenge_id'] = challenge_id

@socketio.on('join_global')
def handle_join_global(data):
    user_id = data.get('user_id')
    if not user_id or user_id != current_user.uid:
        return
        
    room = f"user_{user_id}"
    join_room(room)

@socketio.on('player_ready')
def handle_player_ready(data):
    challenge_id = data.get('challenge_id')
    if not challenge_id:
        return
        
    challenge = Challenge.query.get(challenge_id)
    if not challenge:
        return
        
    if current_user.uid == challenge.challenger_id:
        challenge.challenger_ready = True
    elif current_user.uid == challenge.challenged_id:
        challenge.challenged_ready = True
    else:
        return
        
    if challenge.challenger_ready and challenge.challenged_ready:
        challenge.status = 'in_progress'
        
    db.session.commit()
    
    room = f"challenge_{challenge_id}"
    emit('ready_update', challenge.to_dict(), room=room)
    if challenge.status == 'in_progress':
        emit('status_update', challenge.to_dict(), room=room)

@socketio.on('score_update')
def handle_score_update(data):
    challenge_id = data.get('challenge_id')
    round_num = data.get('round')
    score = data.get('score')

    if not challenge_id or round_num is None or score is None:
        return

    try:
        rnd = int(round_num)
        scr = int(score)
    except (TypeError, ValueError):
        return
    if rnd < 1 or rnd > 5:
        return
    if scr < 0 or scr > rnd * 5000:
        return

    round_num = rnd
    score = scr

    challenge = Challenge.query.get(challenge_id)
    if not challenge:
        return
        
    if current_user.uid == challenge.challenger_id:
        challenge.challenger_round = round_num
        challenge.challenger_score = score
    elif current_user.uid == challenge.challenged_id:
        challenge.challenged_round = round_num
        challenge.challenged_score = score
    else:
        return
        
    db.session.commit()
    
    room = f"challenge_{challenge_id}"
    emit('opponent_progress', {
        'user_id': current_user.uid,
        'round': round_num,
        'score': score
    }, room=room, include_self=False)

@socketio.on('game_complete')
def handle_game_complete(data):
    challenge_id = data.get('challenge_id')
    score = data.get('score')
    if not challenge_id or score is None:
        return

    try:
        score = int(score)
    except (TypeError, ValueError):
        return

    if score < 0 or score > 25000:
        return

    challenge = Challenge.query.get(challenge_id)
    if not challenge:
        return
        
    if current_user.uid == challenge.challenger_id:
        challenge.challenger_score = score
        challenge.challenger_round = 6
    elif current_user.uid == challenge.challenged_id:
        challenge.challenged_score = score
        challenge.challenged_round = 6
    else:
        return
        
    if challenge.challenger_round >= 6 and challenge.challenged_round >= 6:
        challenge.status = 'completed'
        
    db.session.commit()
    
    room = f"challenge_{challenge_id}"
    emit('status_update', challenge.to_dict(), room=room)
