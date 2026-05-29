# Agent Guidance: UWAGuessr Codebase

This file provides context and instructions for AI agents working on the UWAGuessr project.

## **1. PROJECT OVERVIEW**

**Project:** UWAGuessr – A web-based discovery game inspired by GeoGuessr, focused on the University of Western Australia (UWA) campus.

**Purpose:** Players explore UWA through photos and attempt to guess their exact locations on an interactive MazeMap. The application includes competitive features like leaderboards, a social friendship system, and asynchronous challenges.

**Tech Stack:**
- **Backend:** Flask 3.1.3 (Python)
- **Database:** SQLite with SQLAlchemy ORM and Flask-Migrate (Alembic)
- **Frontend:** Bootstrap 5, jQuery, Mapbox GL (via MazeMap API), Pannellum (Panorama Viewer)
- **Image Processing:** Pillow (EXIF GPS extraction, WebP conversion, metadata stripping)
- **Security:** Flask-Login, Flask-WTF, Werkzeug password hashing, CSRF protection
- **Testing:** pytest, Selenium (E2E)

---

## **2. PROJECT STRUCTURE**

```
UWAGuessr_online/
├── app/                          # Main Flask application package
│   ├── __init__.py              # Factory setup, extensions (db, login, migrate, csrf)
│   ├── config.py                # App Configuration (SQLAlchemy, Secret Keys)
│   ├── models.py                # DB Models: User, Photos, GameResult, Challenge, Friendship
│   ├── routes.py                # Endpoint definitions (Templates & JSON APIs)
│   ├── controllers.py           # Service layer: Business logic for Auth, Stats, Leaderboards
│   ├── game_logic.py            # Game engine: Scoring algorithms, distance calculation
│   ├── image_upload.py          # Admin utilities: Image processing & DB sync
│   ├── static/
│   │   ├── css/                 # Custom component styling
│   │   ├── game/photos/         # Game-ready WebP images (stripped of GPS metadata)
│   │   └── js/
│   │       ├── game.js          # Core loop: Round management, Timer (20s), Scoring UI
│   │       ├── map.js           # MazeMap integration: Markers, Lines, Coordinate Projection
│   │       ├── dashboard.js     # User stats visualization & Friend leaderboard
│   │       ├── friends.js       # Social UI: Requests, Searching, Relationships
│   │       └── pano-utils.js    # Pannellum panorama initialization utilities
│   └── templates/               # Jinja2 HTML blueprints
├── instance/                     # Local data (uploads, sqlite db if local)
├── migrations/                  # Alembic version history
├── tests/                       # Automated test suite
├── run.py                       # Management CLI (create-user, load-photos, admin tasks)
└── photos.json                  # Source of truth for photo metadata seed
```

---

## **3. DATABASE SCHEMA**

| Table | Major Columns | Description |
|-------|---------------|-------------|
| **`user`** | `uid`, `username`, `email`, `password_hash`, `security_question`, `security_answer_hash`, `total_score`, `is_admin` | Core identity and aggregate progression. |
| **`friendship`** | `id`, `requester_id`, `receiver_id`, `status` | Maps relationships (`pending`, `accepted`, `rejected`). |
| **`photos`** | `pid`, `image_path`, `latitude`, `longitude`, `timestamp` | Photo metadata. `image_path` points to a WebP asset. |
| **`game_results`** | `sid`, `user_id`, `score`, `timestamp` | Tracks individual game history for the dashboard. |
| **`challenges`** | `id`, `challenger_id`, `challenged_id`, `photo_ids`, `status`, `challenger_ready`, `challenged_ready`, `challenger_score`, `challenged_score`, `challenger_round`, `challenged_round` | State machine for 1v1 asynchronous games. |

---

## **4. CODING CONVENTIONS**

| Aspect | Convention |
|--------|-----------|
| **Python naming** | `snake_case` for variables/functions, `PascalCase` for classes |
| **Validation** | Service layer (`controllers.py`) uses `validate_*` pattern; returns `errors` dict or `None` |
| **JSON API** | Return `jsonify({'data': ...})` or `jsonify({'errors': ...})` with explicit HTTP status codes |
| **JS/jQuery** | Prefer `$.ajax` or `fetch`; perform DOM updates via IDs; follow `camelCase` |
| **Database** | `uid`/`pid`/`sid` used for primary keys in legacy tables; `snake_case` columns |

---

## **5. CORE DOMAIN LOGIC**

### **Scoring & Game Flow (app/game_logic.py & static/js/game.js)**
- **Rounds**: 5 rounds per game.
- **Timer**: 20 seconds per round. Bonus points for speed are not explicitly in the formula but implied by gameplay pressure.
- **Formula**: `5000 * e^(-0.005 * (distance - 10))` for distances > 10m; 5,000 pts if < 10m.
- **Coordinates**: Uses Haversine distance for Earth's curvature.

### **Authentication & Security (app/controllers.py)**
- **Password Recovery**: Uses a mandatory `security_question` and hashed `security_answer` during signup.
- **Admin**: `is_admin` flag gating `/upload-image` and `/delete-photo`.

### **Social & Challenges (app/models.py)**
- **Friendships**: Three states: `pending`, `accepted`, `rejected`.
- **Challenges**: Allows a user to challenge a friend using the same set of 5 photos. Tracks rounds/scores for both players. Uses Socket.IO WebSockets for real-time syncing of game and social events (friend list updates, requests, rematch flows, in-game ready states, and live results updating).

---

## **6. API ENDPOINTS REFERENCE**

### **Game & Leaderboard**
- `GET /api/game-images`: Returns 5 photos (random or via `challengeId`).
- `POST /api/guess`: Submits guess. Returns score and actual coords.
- `POST /api/game-complete`: Finalizes game; updates `total_score`. Handles `challengeId`.
- `GET /api/leaderboard`: Top 10 by `total_score` (Daily/All-time).

### **Social & Multiplayer**
- `GET /api/friends`: List of accepted friends.
- `GET /api/friends/search?q=query`: Search users by username.
- `POST /api/friends/request`: Send friend request (`uid`).
- `POST /api/friends/respond`: Accept/Reject request.
- `POST /api/friends/remove`: Remove / unfriend a user (`uid`).
- `POST /api/challenges/create`: Start challenge with friend (`uid`).
- `GET /api/challenges/active`: List of pending/in-progress challenges.
- `GET /api/challenges/poll/<id>`: Polling endpoint for real-time progress syncing.
- `POST /api/challenges/update-progress`: Syncs round/score during a challenge.

### **Admin & Assets**
- `POST /api/upload-images`: Batch upload to temp storage; returns extracted GPS.
- `POST /api/confirm-image`: Finalizes upload: WebP conversion, EXIF stripping, DB/JSON sync.
- `GET /api/photos`: List all registered photos.
- `POST /api/photos/<pid>/update-location`: Adjust lat/lng for a photo.
- `POST /api/photos/<pid>/delete`: Remove photo record and WebP asset.

---

## **7. MULTIPLAYER & CHALLENGES**

- **Asynchronous Flow**: Challenges are created as `pending`. Once the challenged friend accepts and both sides mark `ready`, the status moves to `in_progress`.
- **Syncing**: The application uses real-time bi-directional WebSockets via Socket.IO. Game updates, player ready states, and friendship events trigger real-time socket events (`new_challenge`, `friend_request_update`, `friend_list_update`, `ready_update`, `status_update`, `opponent_progress`, `score_update`) inside global (`user_{uid}`) and challenge-specific (`challenge_{id}`) socket rooms, completely replacing HTTP polling.
- **Scoring**: Both players play the **exact same set of 5 photos**. The winner is determined once both reach round 6 (completed).
- **Expiration**: Challenges in `pending` or `ready_waiting` states expire after 3 minutes of inactivity.

---

## **8. IMAGE UPLOAD & ASSET MANAGEMENT**

- **Workflow**: Upload (temp) ➔ GPS Extraction (EXIF) ➔ Admin Confirmation (preview/adjust) ➔ WebP Conversion ➔ DB Record ➔ JSON Sync.
- **Storage**:
    - `instance/uploads/`: Temporary storage for original files during extraction.
    - `app/static/game/photos/`: Production WebP assets (metadata-stripped).
- **Source of Truth**: [photos.json](photos.json) acts as a portable seed file for photo metadata. Any DB change (add/delete/update) triggers a sync to this file.

---

## **9. DEVELOPMENT WORKFLOW**

### **Database Management**
- **Migration**: `flask db migrate -m "change description"`
- **Execution**: `flask db upgrade`
- **Seeding**: `flask --app run load-photos` (reads from `photos.json`)

### **Admin Tasks**
- **Promote User**: `python run.py admin-promote --username [name]`
- **Create User**: `python run.py create-user --username [name] --email [email] --password [pass]`

---

## **10. AGENT INSTRUCTIONS**

- **Privacy**: **NEVER** expose the original source photos in `instance/uploads` to the client. Only serve via `app/static/game/photos` after WebP conversion and EXIF stripping in `image_upload.py`.
- **Front-end State**: `game.js` manages global state for active games. Do not bypass `game_logic.py` for scoring calculations.
- **Testing**: Run `pytest` before any PR. UI changes requiring map interaction should be verified via `tests/test_selenium.py`.
