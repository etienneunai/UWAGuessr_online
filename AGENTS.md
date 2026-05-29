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

## **3. CODING CONVENTIONS**

| Aspect | Convention |
|--------|-----------|
| **Python naming** | `snake_case` for variables/functions, `PascalCase` for classes |
| **Validation** | Service layer (`controllers.py`) uses `validate_*` pattern; returns `errors` dict or `None` |
| **JSON API** | Return `jsonify({'data': ...})` or `jsonify({'errors': ...})` with explicit HTTP status codes |
| **JS/jQuery** | Prefer `$.ajax` or `fetch`; perform DOM updates via IDs; follow `camelCase` |
| **Database** | `uid`/`pid`/`sid` used for primary keys in legacy tables; `snake_case` columns |

---

## **4. CORE DOMAIN LOGIC**

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
- **Challenges**: Allows a user to challenge a friend using the same set of 5 photos. Tracks rounds/scores for both players.

---

## **5. API ENDPOINTS REFERENCE**

- `POST /api/guess`: Submits a lat/lng guess. Returns score, actual coords, and distance.
- `GET /api/game-images`: Returns a randomized set of 5 photos (or specific ones if `challengeId` provided).
- `GET /api/dashboard-stats`: Returns summary of games, best score, and recent trend.
- `GET /api/leaderboard`: Returns top 10 players based on `total_score`.

---

## **6. DEVELOPMENT WORKFLOW**

### **Database Management**
- **Migration**: `flask db migrate -m "change description"`
- **Execution**: `flask db upgrade`
- **Seeding**: `flask --app run load-photos` (reads from `photos.json`)

### **Admin Tasks**
- **Promote User**: `python run.py admin-promote --username [name]`
- **Create User**: `python run.py create-user --username [name] --email [email] --password [pass]`

---

## **7. AGENT INSTRUCTIONS**

- **Privacy**: **NEVER** expose the original source photos in `instance/uploads` to the client. Only serve via `app/static/game/photos` after WebP conversion and EXIF stripping in `image_upload.py`.
- **Front-end State**: `game.js` manages global state for active games. Do not bypass `game_logic.py` for scoring calculations.
- **Testing**: Run `pytest` before any PR. UI changes requiring map interaction should be verified via `tests/test_selenium.py`.
