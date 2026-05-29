# UWAGuessr Multiplayer: WebSocket Migration & Bug Fixes

This document outlines the plan to transition the challenge multiplayer system from HTTP polling to real-time WebSockets and address identified security and UX issues.

## 1. Problem Statement
The current challenge system uses a **3-second HTTP polling** mechanism.
- **Latency**: Up to 3 seconds of delay in game starts and progress updates.
- **Resource Intensive**: Constant polling creates unnecessary server load.
- **UX Gaps**: No real-time feedback (e.g., opponent progress) during gameplay.
- **Security**: Lack of server-side validation for round timers and photo set integrity.

## 2. Technical Solution: WebSockets
We will use `Flask-SocketIO` to move to an event-driven architecture.

### Phase 1: Foundation
- **Dependencies**: Add `flask-socketio`, `python-socketio`, and `eventlet` (for async performance) to `requirements.txt`.
- **Server Setup**:
    - Initialize `SocketIO` in `app/__init__.py`.
    - Update `run.py` to use `socketio.run(app)`.
- **Event Handlers**: Create `app/socket_handlers.py` to manage:
    - `connect` / `disconnect`: Handle player presence, detect abandonment, and optionally handle reconnections.
    - `join_challenge`: Subscribe to a specific room (`challenge_{id}`).
    - `player_ready`: Sync the "Ready" state and update the `Challenge` database model.
    - `update_progress`: Broadcast current round/score to the opponent and persist to the database.
    - `game_over`: Broadcast final results (win/loss/tie) when both players reach round 6.

### Phase 2: Frontend Refactor
- **Client integration**: Include the Socket.io client script in `base.html`.
- **Game Logic (`game.js`)**:
    - Replace `startPolling()` with socket listeners for `status_update`, `ready_update`, and `opponent_progress`.
    - Emit `score_update` immediately after each round to provide live competitive feedback.
- **Dashboard (`friends.js`)**: Listen for global `new_challenge` events to update notifications even when the sidebar is closed.

### Phase 3: Bug Fixes & Security
- **Server-Side Timer**: Modify `/api/guess` to validate the time elapsed (rejected if > 22s) using session-stored start times.
- **Photo Integrity**: Ensure `/api/guess` only accepts photo IDs linked to the active challenge.
- **Real-Time Invites**: Emit a `new_challenge` socket event from the `/api/challenges/create` route.
- **Pending Challenge Redirect**: Fix bug in `/api/challenges/create` where sending a challenge to someone with an already pending/active challenge shows an error alert; it should redirect the user straight into the game/waiting room.
- **Silent Rejections**: Emit a `challenge_rejected` event so the challenger is notified instantly.
- **Player Disconnects**: Emit an `opponent_disconnected` event if a socket drops mid-game to alert the active player.
- **Dashboard Sidebar**: Update `dashboard.html` to include a dedicated "Active Challenges" widget for better visibility.

## 3. Implementation Roadmap

### Step 1: Backend Infrastructure
```python
# app/__init__.py (example)
from flask_socketio import SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

# run.py (example)
if __name__ == "__main__":
    socketio.run(app, debug=True)
```

### Step 2: Game State Events
```javascript
// game.js (concept)
socket.on('opponent_progress', (data) => {
    updateOpponentCard(data.round, data.score);
});
```

## 4. Verification Plan
1. **Concurrency**: Verify Browser A and Browser B sync "READY" states instantly.
2. **Real-time Feedback**: Ensure the Game Over screen shows opponent progress as they play.
3. **Security**: Test timer spoofing by delaying the `/api/guess` call manually via console.
4. **Test Cases**: Generate unit tests for server-side validation logic and integration tests for WebSocket events.

---
**Status**: Planned  
**Last Updated**: May 29, 2026
