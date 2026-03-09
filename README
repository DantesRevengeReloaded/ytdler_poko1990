<p align="center">
  <img src="images/pokoapp.ico" alt="PokoDler 1990 icon" width="96" height="96" />
</p>

<h1 align="center">PokoDler 1990</h1>

<p align="center">
  Local FastAPI + vanilla JS downloader for YouTube singles, YouTube playlists, and Spotify-to-YouTube mirroring.
</p>

<p align="center">
  <img alt="Backend" src="https://img.shields.io/badge/backend-FastAPI-0f172a?style=flat-square">
  <img alt="Frontend" src="https://img.shields.io/badge/frontend-Vanilla%20JS-0f172a?style=flat-square">
  <img alt="Database" src="https://img.shields.io/badge/database-PostgreSQL-0f172a?style=flat-square">
  <img alt="Downloader" src="https://img.shields.io/badge/downloader-yt--dlp-0f172a?style=flat-square">
</p>

---

## What This Project Is

PokoDler 1990 is a local desktop-style media utility built with FastAPI and a static dashboard UI.

It is designed to:

- download a single YouTube URL as audio or video
- download full YouTube playlists into organized folders
- mirror Spotify playlists, albums, or artists by searching matching audio on YouTube
- track active jobs in real time
- browse local library files and download history
- show storage stats, output folders, queue snapshots, and recent activity

The frontend is intentionally simple:

- no npm
- no build step
- no framework runtime
- static HTML/CSS/JS served directly by FastAPI

---

## Quick Start

Requirements:

- Python 3.11+
- PostgreSQL
- FFmpeg on `PATH`

Install:

```bash
pip install -r requirements.txt
cp .env.example .env
```

Run:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Or use the helper script:

```bash
./run.sh
```

Open:

```text
http://127.0.0.1:8000
```

---

## Configuration

Copy `.env.example` to `.env` and fill in the values you need.

Available keys:

```env
POKODLER_APP_NAME=
POKODLER_LOG_LEVEL=
POKODLER_DOWNLOAD_DIR=
POKODLER_DB_HOST=
POKODLER_DB_PORT=
POKODLER_DB_NAME=
POKODLER_DB_USER=
POKODLER_DB_PASSWORD=
POKODLER_DB_SSLMODE=
POKODLER_SPOTIFY_CLIENT_ID=
POKODLER_SPOTIFY_CLIENT_SECRET=
POKODLER_SPOTIFY_REDIRECT_URI=
POKODLER_SPOTIFY_SP_DC=
POKODLER_MAX_CONCURRENT_DOWNLOADS=
POKODLER_CLEANUP_DAYS=
```

---

## Architecture At A Glance

| Layer | Responsibility | Main Files |
|---|---|---|
| App bootstrap | FastAPI setup, logging, static mounts, startup hooks | `app/main.py` |
| Config | Environment-backed settings and DB DSN creation | `app/core/config.py` |
| API routes | HTTP endpoints for downloads, files, Spotify, stats | `app/api/routes/*` |
| Services | Download orchestration, Spotify logic, DB access | `app/services/*` |
| Database | PostgreSQL connection handling and schema creation | `app/db/*` |
| Frontend | Static dashboard UI | `app/web/static/*` |

Current stack:

- Backend: FastAPI
- Frontend: static HTML, CSS, JavaScript
- Persistence: PostgreSQL
- Downloader: `yt-dlp`
- Audio tagging: `mutagen`
- Spotify access: `requests`

---

## Repository Structure

```text
.
├── app/
│   ├── api/routes/
│   │   ├── downloads.py
│   │   ├── files.py
│   │   ├── spotify.py
│   │   └── stats.py
│   ├── core/
│   │   └── config.py
│   ├── db/
│   │   ├── init_db.py
│   │   └── session.py
│   ├── services/
│   │   ├── db_manager.py
│   │   ├── downloads.py
│   │   └── spotify.py
│   ├── web/static/
│   │   ├── index.html
│   │   ├── styles.css
│   │   ├── main.js
│   │   └── assets/
│   ├── main.py
│   └── models.py
├── images/
├── run.sh
├── setup_db.sh
├── requirements.txt
└── .env.example
```

---

## Backend Breakdown

### `app/main.py`

Bootstraps the FastAPI app and wires the project together.

Responsibilities:

- configure logging
- initialize database connectivity
- run startup cleanup
- mount frontend static assets
- serve the main dashboard

### `app/core/config.py`

Defines the `Settings` object used across the app.

Key concerns:

- `.env` loading
- app name and logging config
- download directory
- PostgreSQL settings
- Spotify credentials
- concurrency and cleanup settings

### `app/models.py`

Contains Pydantic request and response models for:

- single downloads
- playlist downloads
- Spotify previews
- Spotify mirror results
- history responses
- progress snapshots
- stats responses

---

## API Endpoints

### Downloads

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/v1/downloads/` | Create single YouTube download |
| `POST` | `/api/v1/downloads/playlist` | Create YouTube playlist download |
| `GET` | `/api/v1/downloads/progress/{job_id}` | Poll live job progress |
| `GET` | `/api/v1/downloads/history` | Fetch download history |

### Spotify

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/v1/spotify/auth/login` | Start Spotify OAuth |
| `GET` | `/api/v1/spotify/auth/callback` | Complete Spotify OAuth |
| `GET` | `/api/v1/spotify/auth/status` | Report auth status |
| `POST` | `/api/v1/spotify/playlist` | Fetch Spotify metadata |
| `GET` | `/api/v1/spotify/history` | Fetch Spotify mirror history |
| `POST` | `/api/v1/spotify/mirror` | Mirror Spotify collection to YouTube downloads |

### Files / Stats

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/v1/files` | List local media files |
| `GET` | `/api/v1/files/root` | Show configured output root |
| `GET` | `/api/v1/files/stream/{filepath}` | Stream local file |
| `DELETE` | `/api/v1/files/{filepath}` | Delete local file |
| `GET` | `/api/v1/stats` | Basic totals |
| `GET` | `/api/v1/stats/breakdown` | Breakdown by type/storage |
| `GET` | `/api/v1/healthz` | Health check |

---

## Service Layer

### `app/services/downloads.py`

Handles all YouTube download workflows:

- single audio download
- single video download
- playlist download
- progress tracking
- semaphore-based concurrency limiting
- playlist folder naming and sanitization
- ID3 tagging for audio outputs
- old-file cleanup

Output layout:

- singles: `downloads/singledls/`
- playlists: `downloads/playlists/<sanitized_playlist>_<timestamp>/`

### `app/services/spotify.py`

Handles Spotify-specific logic:

- OAuth authorization URL creation
- OAuth callback token exchange
- persisted user token load/save
- client-credentials token flow
- optional `sp_dc` cookie flow
- playlist, album, and artist metadata fetch
- editorial playlist fallback through YouTube Music lookup
- Spotify-to-YouTube mirror workflow

Spotify mirror flow:

1. parse Spotify URL or URI
2. fetch playlist/album/artist metadata
3. create a local output folder
4. search YouTube per track
5. download best audio and convert to MP3
6. validate file output
7. write history and tags

### `app/services/db_manager.py`

Database-facing helper layer for:

- download history inserts
- Spotify mirror history inserts
- job progress upserts
- total size and total item stats
- history reads
- filesystem storage summaries

---

## Database Layer

### `app/db/session.py`

Provides PostgreSQL access using `psycopg2`.

- builds connections from env config
- exposes `get_cursor()` as a transactional context manager

### `app/db/init_db.py`

Creates the core tables if they do not exist:

- `downloaded_songs`
- `spotify_downloads`
- `jobs`

---

## Frontend Dashboard

Frontend files:

- `app/web/static/index.html`
- `app/web/static/styles.css`
- `app/web/static/main.js`

Main dashboard sections:

1. Hero/header with branding, context, status, and settings
2. Main action row
   - Single Download
   - Playlist Download
   - Spotify Retriever
3. Full-width Live Activity row
4. Result summary row
5. Utility/support row
   - Insights
   - Output
   - Queue / History Snapshot
6. Workspace row
   - Library
   - History

Frontend responsibilities:

- send API requests
- poll progress state
- render stats and queue summaries
- render output folder information
- render the local library and history views
- keep lightweight UI preferences in `localStorage`

---

## Output And Runtime Files

Under the configured download directory:

- `singledls/`
- `playlists/`
- `spotify_playlists/`

Other local runtime files:

- PostgreSQL stores history and job metadata
- logs are written to `logs/app.log`
- Spotify OAuth token state may be persisted locally by the Spotify service

---

## Database Setup Helper

If you want the helper script to create/update the PostgreSQL role and database, set the DB environment values first and run:

```bash
sudo bash setup_db.sh
```

The script reads:

- `POKODLER_DB_HOST`
- `POKODLER_DB_PORT`
- `POKODLER_DB_NAME`
- `POKODLER_DB_USER`
- `POKODLER_DB_PASSWORD`

---

## Local Notes

- This project is designed for local use.
- Spotify mirroring depends on YouTube search quality and may not always match perfectly.
- Large playlists can generate many files quickly.
- The codebase currently keeps backend orchestration, provider integration, and desktop-style behavior in one app, so future modularization would help.

---

## Suggested Future Improvements

- move Spotify token storage outside the repository tree
- add stricter server-side validation for supported URLs and input types
- split provider-specific logic from downloader orchestration
- add CI and a cleaner automated test workflow
- add release-safe local-data handling and privacy controls

---

## License

MIT
