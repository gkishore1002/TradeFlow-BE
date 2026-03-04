# app/socket_handlers.py
from flask_socketio import join_room, leave_room
from .extensions import socketio
from flask import request

@socketio.on('connect')
def handle_connect():
    """Handle SocketIO connection"""
    print(f"🔌 Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle SocketIO disconnection"""
    print(f"🔌 Client disconnected: {request.sid}")

@socketio.on('join')
def handle_join(data):
    """Handle joining a notification room"""
    user_id = data.get('user_id')
    if user_id:
        room = f"user_{user_id}"
        join_room(room)
        print(f"🚪 Client {request.sid} joined room: {room}")
        socketio.emit('join_response', {'status': 'success', 'room': room}, room=request.sid)
    else:
        print(f"⚠️ Join attempt without user_id from {request.sid}")
        socketio.emit('join_response', {'status': 'error', 'message': 'user_id is required'}, room=request.sid)

@socketio.on('leave')
def handle_leave(data):
    """Handle leaving a notification room"""
    user_id = data.get('user_id')
    if user_id:
        room = f"user_{user_id}"
        leave_room(room)
        print(f"🚪 Client {request.sid} left room: {room}")
