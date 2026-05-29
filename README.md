# UWAGuessr

Fork from the project repo to improve the website and deploy it.

| Student ID | Name                       | Github Account                                               |
| ---------- | -------------------------- | ------------------------------------------------------------ |
| 24149137   | Mathew Nedumpurath Tomy    | [mathewtomy973-pixel](https://github.com/mathewtomy973-pixel) |
| 24465269   | Tep (Vu Minh Hoang) Nguyen | [tepnguyenvu](https://github.com/tepnguyenvu)                |
| 23831382   | Janee Pandithasekara       | [Janee190](https://github.com/Janee190)                      |
| 24217857   | Etienne Vinton Horn        | [etienneunai](https://github.com/etienneunai)                |

## Description
UWAGuessr is a web-based discovery game inspired by GeoGuessr, focussed specifically on the University of Western Australia (UWA) campus. Players are presented with photos of various locations around UWA and must pinpoint their location on an interactive map.

## Configuration

Set the required environment variables before running the server:

**Windows (PowerShell):**
```powershell
$env:UWAGUESSR_SECRET_KEY = "your-secret-key-here"
$env:DATABASE_URL = "sqlite:///app.db"
```

**macOS / Linux:**
```bash
export UWAGUESSR_SECRET_KEY="your-secret-key-here"
export DATABASE_URL="sqlite:///app.db"
```

`UWAGUESSR_SECRET_KEY` is required (the app will not start without it). `DATABASE_URL` defaults to `sqlite:///app.db` if not set.

## Running the Server

Process for first running (we recommend using a virtual environment):

```bash
pip install -r requirements.txt
flask db upgrade
flask --app run load-photos # loads initial photos from data json file

flask run
```

Users can be promoted to an admin account with the following command:

```bash
flask --app run admin-promote [USERNAME]
```

Admins can be demoted with:

```bash
flask --app run admin-demote [USERNAME]
```

## Running Tests

```bash
python -m pytest
```  
To run a test file individually:  
```bash
python -m pytest tests/test_game.py
python -m pytest tests/test_authentication.py
python -m pytest tests/test_routes.py
python -m pytest tests/test_selenium.py
python -m pytest tests/test_selenium_auth.py
```

# Project Details

## Project Goals
* **Engagement:** Create a fun, interactive way for students, alumni, and visitors to explore the UWA campus.
* **Competition:** Build a community through leaderboards and social sharing features.
* **Scalability:** Provide an easy-to-use administrative interface to update campus photos as the university evolves.

## Key Features
* **User Authentication:** Secure account creation and login/logout functionality to save progress.
* **Password Reset:** Secure method to allow users to reset their passwords with a custom security question if they forget.
* **Interactive Map Guessing:** A map interface allowing players to place markers to submit their guesses.
* **Scoring & Feedback:** Real-time distance calculation between the guess and the actual location, including visual reveals of the correct spot.
* **User Profiles:** Dedicated profile pages to track past game history and individual performance metrics.
* **Global Leaderboard:** A competitive ranking system to compare scores with other players.
* **Social Challenges:** Ability to send friends challenges and play a real-time game using Socket.IO WebSockets for syncing round progress, ready statuses, and live spectating outcomes.
* **Admin Dashboard:** Tools for system administrators to manage users and for game admins to upload/delete campus photos without writing code.

## Site Structure
* **Home/Landing Page:** Introduction to the game and quick start.
* **Game Page:** The core interactive interface for viewing photos and the map.
* **Leaderboard:** Ranking of top users.
* **Profile:** Personal dashboard for game history and stats.
* **User Pages**: View the profiles and stats of other users.
* **About/How to Play:** Instructions and project background.
* **Authentication Pages:** Simple Login, sign-up, and password-reset.
* **Admin Management Portal:** Allows the upload, deletion, and editing of game photos.

## Tech Stack
* **Frontend:** Bootstrap (HTML/CSS)
* **Backend:** Flask (Python)
* **Database:** SQLite (via SQLAlchemy)
* **Map API:** MazeMap (Mapbox GL-based)
* **Real-time Sync:** Socket.IO (WebSockets)

