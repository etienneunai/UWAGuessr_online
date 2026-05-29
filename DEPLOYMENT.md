# UWAGuessr Cloud Deployment Plan — Oracle Cloud Infrastructure

## Context

UWAGuessr currently runs only locally: SQLite database, local filesystem image storage, Flask dev server. The deployment goal is a stateless cloud architecture running on an **OCI Ampere A1 instance** (Always Free tier: up to 4 cores, 24 GB RAM) with co-located **PostgreSQL 16/17** and **Cloudflare R2** for zero-egress image storage with direct CDN serving. Backward compatibility with local development (SQLite + local fs) must be preserved via environment variable gating.

---

## Architecture Decisions

1. **No app factory refactor.** The module-level singleton in `app/__init__.py` works with gunicorn. Skipping saves significant test/config churn with zero production benefit.

2. **URL prefix at query time, not storage time.** `Photos.image_path` keeps the canonical format `/static/game/photos/<uuid>.webp`. A `PHOTO_BASE_URL` env var prefix is applied at API response time via `_resolve_photo_url()`. `photos.json` stays environment-agnostic.

3. **R2 key = `image_path.lstrip('/')`.** No new DB column needed. `static/game/photos/<uuid>.webp` is the R2 key.

4. **`R2_ENABLED` flag gates cloud behavior.** When `true`, uploads/deletes hit R2. When `false`/absent, local filesystem used. All 60 existing photos work unchanged.

5. **Compute + database co-located.** Flask app and PostgreSQL 16/17 run on the same OCI Ampere A1 VM. No separate database provider (Neon). App connects via Unix socket or `localhost:5432` — zero network latency, no cold starts.

6. **Persistent connection pool, no scale-to-zero gating.** Local PostgreSQL never suspends. No aggressive `pool_recycle` needed. Pool only reaps idle connections that exceed `pool_size`.

---

## Files to Modify

### 1. `requirements.txt` — Add 3 dependencies
- `psycopg2-binary==2.9.10` — PostgreSQL driver
- `boto3==1.36.0` — S3-compatible client for Cloudflare R2
- `gunicorn==23.0.0` — Production WSGI server

### 2. `app/config.py` — Add R2 and PostgreSQL config
- Add class attributes: `R2_ENABLED`, `R2_ENDPOINT_URL`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME`, `PHOTO_BASE_URL` — all read from env vars with sensible defaults (empty/false)
- Change default `DATABASE_URL` fallback: when unset in production, fall back to local PostgreSQL connection string:
  ```python
  default_db_url = 'postgresql://uwaguessr:<password>@localhost:5432/uwaguessr'
  ```
  Keep the env var check first (`os.environ.get('DATABASE_URL') or default_db_url`). For local dev, set `DATABASE_URL=sqlite:///app.db`.
- Add `SQLALCHEMY_ENGINE_OPTIONS`:
  ```python
  SQLALCHEMY_ENGINE_OPTIONS = {
      'pool_size': 10,
      'pool_pre_ping': True,
  }
  ```
  No `pool_recycle` — local PostgreSQL is always-on, no connection timeout issues. `pool_size=10` matches gunicorn workers (9) plus headroom.

### 3. `app/r2_storage.py` — **New file**: R2/S3 client wrapper
- `get_r2_client()` — creates boto3 S3 client with R2 endpoint, `s3v4` signature, `auto` region
- `upload_photo_bytes(bytes_data, key)` — `put_object` to R2 bucket
- `delete_photo_by_key(key)` — `delete_object` from R2 bucket

### 4. `app/image_upload.py` — Conditional R2 upload/delete
- `convert_to_webp()` — save to `io.BytesIO` buffer, then: if `R2_ENABLED` → upload to R2 via `upload_photo_bytes()`, else → write to `PHOTOS_DIR` as before
- `delete_photo_record()` — if `R2_ENABLED` → delete from R2 via `delete_photo_by_key()`, else → delete from local disk. DB row deleted either way.
- `sync_photos_to_json()` / `load_photos_from_json()` — unchanged (work with canonical paths)

### 5. `app/game_logic.py` — URL resolution helper
- Add `_resolve_photo_url(image_path)` — if `PHOTO_BASE_URL` is set, return `base.rstrip('/') + image_path`, else return path unchanged
- Modify `get_game_images()` — wrap `image_path` in `_resolve_photo_url()` in both code paths (random selection and challenge-specific)

### 6. `app/routes.py` — Resolve URLs in image API responses
- `api_list_photos()` — apply `_resolve_photo_url()` to returned `image_path`
- `api_confirm_image()` — apply `_resolve_photo_url()` to returned `imagePath`

### 7. `run.py` — Add migration CLI command
- `flask migrate-photos-to-r2` — reads all Photos rows, uploads corresponding local files to R2 at key `image_path.lstrip('/')`. Reports OK/SKIP per photo.

### 8. `app/test_config.py` — Add R2 defaults
- `R2_ENABLED = False`, `PHOTO_BASE_URL = ""` — ensures tests always run in local mode
- Keep `SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"` — tests never hit PostgreSQL

### 9. `uwaguessr.service` — **New file**: systemd service unit

```
[Unit]
Description=UWAGuessr Flask Application
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=uwaguessr
Group=uwaguessr
WorkingDirectory=/opt/uwaguessr
EnvironmentFile=/opt/uwaguessr/.env
ExecStart=/opt/uwaguessr/venv/bin/gunicorn app:app \
    --workers 9 \
    --worker-class sync \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --bind unix:/run/uwaguessr/gunicorn.sock
Restart=always
RestartSec=5
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

Notes:
- Socket binding at `/run/uwaguessr/gunicorn.sock` — Nginx proxies to this socket (zero TCP overhead vs `localhost:8000`)
- Worker count 9 = `2 × cores(4) + 1` — Ampere A1 maxes at 4 OCPU. Adjust down if using a smaller shape.
- `PrivateTmp=true` — isolates `/tmp`, harmless for this app
- `EnvironmentFile` — loads DATABASE_URL, UWAGUESSR_SECRET_KEY, R2_* vars, PHOTO_BASE_URL from a file outside the repo

### 10. `nginx.conf` — **New file**: Nginx reverse proxy configuration

```nginx
upstream uwaguessr_app {
    server unix:/run/uwaguessr/gunicorn.sock fail_timeout=0;
}

server {
    listen 80;
    server_name uwaguessr.com www.uwaguessr.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name uwaguessr.com www.uwaguessr.com;

    ssl_certificate     /etc/letsencrypt/live/uwaguessr.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/uwaguessr.com/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    client_max_body_size 50m;

    # Static assets served directly by Nginx (CSS, JS, static images)
    # R2-hosted game panoramas are NOT served from here — clients fetch those
    # directly from Cloudflare R2 CDN via PHOTO_BASE_URL.
    location /static/ {
        alias /opt/uwaguessr/app/static/;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }

    # Temp upload preview (admin only, ephemeral)
    location /instance/ {
        alias /opt/uwaguessr/instance/;
    }

    # All other requests → Gunicorn
    location / {
        proxy_pass http://uwaguessr_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }
}
```

Notes:
- Static CSS/JS served by Nginx directly (bypasses Gunicorn). Game panoramas (the large WebP files) are NOT in `/static/game/photos/` in production — those live on R2.
- `client_max_body_size 50m` accommodates large panorama uploads through the admin panel
- SSL managed by certbot (Let's Encrypt), cert paths updated automatically

---

## Files NOT Modified (No Changes Needed)

- `app/__init__.py` — singleton app works with gunicorn
- `app/models.py` — no schema changes (image_path stays canonical format)
- `app/controllers.py` — scoring/auth logic unchanged
- `app/static/js/game.js` — `imagePath` already comes resolved from API, Pannellum accepts CDN URLs
- `app/static/js/image-upload.js` — `image_path.split('/').pop()` works on CDN URLs; temp preview still uses `/instance/uploads/`
- `app/static/js/pano-utils.js` — `buildViewer()` passes URL directly to Pannellum
- `tests/conftest.py` — existing fixtures compatible; `TestConfig.R2_ENABLED=False` ensures local mode
- `photos.json` — stores canonical paths, no changes needed
- `.gitignore` — already excludes `.env`, `*.db`, `instance/`

---

## Environment Variables Summary

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `DATABASE_URL` | Production | `postgresql://uwaguessr:<pw>@localhost:5432/uwaguessr` | PostgreSQL connection string (or `sqlite:///app.db` for local dev) |
| `UWAGUESSR_SECRET_KEY` | Always | (none) | Flask secret key |
| `R2_ENABLED` | Production | `false` | `true` enables R2 storage |
| `R2_ENDPOINT_URL` | When R2 on | `""` | R2 S3 API endpoint (e.g. `https://<account-id>.r2.cloudflarestorage.com`) |
| `R2_ACCESS_KEY_ID` | When R2 on | `""` | R2 API token key |
| `R2_SECRET_ACCESS_KEY` | When R2 on | `""` | R2 API token secret |
| `R2_BUCKET_NAME` | When R2 on | `uwaguessr-photos` | R2 bucket name |
| `PHOTO_BASE_URL` | Production | `""` | CDN/public URL prefix for photos (e.g. `https://pub-<hash>.r2.dev`) |

All production env vars are stored in `/opt/uwaguessr/.env`, read by systemd via `EnvironmentFile`.

---

## Deployment Sequence

### Phase 1: Provision OCI Instance

1. In OCI dashboard: create Ampere A1 instance (Ubuntu 24.04 LTS, 4 OCPU, 24 GB RAM — Always Free eligible shape)
2. In OCI Virtual Cloud Network (VCN): open ingress ports **22** (SSH), **80** (HTTP), **443** (HTTPS) in the security list
3. SSH into the instance

### Phase 2: Install System Dependencies

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv postgresql nginx certbot python3-certbot-nginx
```

### Phase 3: Configure PostgreSQL

```bash
sudo -u postgres psql -c "CREATE USER uwaguessr WITH PASSWORD '<strong-password>';"
sudo -u postgres psql -c "CREATE DATABASE uwaguessr OWNER uwaguessr;"
sudo -u postgres psql -c "ALTER USER uwaguessr CREATEDB;"
```

For local socket auth (optional, more secure than password):
```bash
# In pg_hba.conf, ensure local connections use peer or md5:
# local   all   uwaguessr   peer
sudo systemctl restart postgresql
```

### Phase 4: Deploy Application Code

```bash
sudo useradd -m -s /bin/bash uwaguessr
sudo mkdir -p /opt/uwaguessr /run/uwaguessr
sudo chown uwaguessr:uwaguessr /opt/uwaguessr /run/uwaguessr
# Clone repo or rsync code to /opt/uwaguessr
cd /opt/uwaguessr
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Phase 5: Configure Environment

Create `/opt/uwaguessr/.env`:
```
DATABASE_URL=postgresql://uwaguessr:<password>@localhost:5432/uwaguessr
UWAGUESSR_SECRET_KEY=<generated-secret>
R2_ENABLED=true
R2_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
R2_ACCESS_KEY_ID=<r2-access-key>
R2_SECRET_ACCESS_KEY=<r2-secret-key>
R2_BUCKET_NAME=uwaguessr-photos
PHOTO_BASE_URL=https://pub-<hash>.r2.dev
```

Set permissions: `chmod 600 /opt/uwaguessr/.env && chown uwaguessr:uwaguessr /opt/uwaguessr/.env`

### Phase 6: Database Seeding

```bash
cd /opt/uwaguessr
source venv/bin/activate
flask db upgrade
flask load-photos
# Fix PostgreSQL sequence after explicit PID inserts:
sudo -u postgres psql -d uwaguessr -c "SELECT setval('photos_pid_seq', (SELECT MAX(pid) FROM photos))"
```

### Phase 7: Asset Migration to R2

```bash
cd /opt/uwaguessr
source venv/bin/activate
flask migrate-photos-to-r2
```

### Phase 8: Install Nginx Config

Copy `nginx.conf` to `/etc/nginx/sites-available/uwaguessr`, symlink to `sites-enabled`, test, reload:

```bash
sudo cp nginx.conf /etc/nginx/sites-available/uwaguessr
sudo ln -s /etc/nginx/sites-available/uwaguessr /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default  # remove default site
sudo nginx -t
sudo systemctl reload nginx
```

### Phase 9: Install systemd Service

```bash
sudo cp uwaguessr.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable uwaguessr
sudo systemctl start uwaguessr
```

### Phase 10: SSL Certificate

```bash
sudo certbot --nginx -d uwaguessr.com -d www.uwaguessr.com
```

Certbot auto-renews via systemd timer (installed by default).

### Phase 11: Open OCI OS Firewall

OCI Ubuntu images run iptables by default. Open ports 80 and 443:

```bash
sudo iptables -I INPUT 6 -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

Also open port 5432 if external PostgreSQL access is needed (optional, not recommended — keep DB traffic local).

### Phase 12: Configure R2 CORS

In Cloudflare R2 dashboard, add CORS rule for the bucket:
```json
{
  "AllowedOrigins": ["https://uwaguessr.com"],
  "AllowedMethods": ["GET"],
  "AllowedHeaders": ["*"],
  "MaxAgeSeconds": 3600
}
```

---

## Known Considerations

- **PostgreSQL sequence sync:** After `flask load-photos` inserts explicit `pid` values, run `SELECT setval('photos_pid_seq', (SELECT MAX(pid) FROM photos))` to prevent duplicate key errors on new uploads.
- **OCI iptables firewall:** Ubuntu on OCI runs an OS-level iptables firewall in addition to the VCN security list. Both must allow ports 80/443. Use `netfilter-persistent` to save rules across reboots.
- **gunicorn worker count:** Ampere A1 provides up to 4 OCPU and 24 GB RAM. Formula `2 × cores + 1 = 9` workers. Flask + gunicorn per-worker memory is ~100 MB, so 9 workers ≈ 900 MB — well within 24 GB. No OOM risk.
- **R2 CORS:** Pannellum loads images cross-origin. R2 bucket must allow GET from the deployment domain (configured in Phase 12).
- **Persistent disk:** Unlike Render, OCI VMs have persistent block storage (up to 200 GB on Always Free). `instance/uploads/` and `app/static/` survive reboots and deploys. Local photo directory is still unused in production (R2 is source of truth).
- **systemd journal:** All gunicorn stdout/stderr captured by journald. View logs: `journalctl -u uwaguessr -f`. Nginx logs at `/var/log/nginx/`.
- **PostgreSQL backups:** Schedule `pg_dump` via cron or systemd timer for automated backups. Not covered in this plan — configure separately.

---

## Verification

1. **Local dev unchanged:** `flask run` with no new env vars → app works with SQLite + local fs
2. **R2 upload:** Set `R2_ENABLED=true` + R2 credentials → admin uploads panorama → file appears in R2 bucket at `static/game/photos/<uuid>.webp` → `photos.image_path` = `/static/game/photos/<uuid>.webp`
3. **CDN serving:** Set `PHOTO_BASE_URL=https://pub-xxx.r2.dev` → `GET /api/game-images` returns `https://pub-xxx.r2.dev/static/game/photos/<uuid>.webp` → Pannellum renders panorama
4. **PostgreSQL:** Set `DATABASE_URL=postgresql://...` → `flask db upgrade` creates tables → app reads/writes correctly
5. **Tests pass:** `pytest tests/ -k "not selenium"` — all existing tests green with `R2_ENABLED=False`
6. **CLI migration:** `flask migrate-photos-to-r2` uploads all local photos, prints per-file status
7. **systemd service:** `sudo systemctl status uwaguessr` → active (running), `curl http://localhost:8000` → 200
8. **Nginx proxy:** `curl -H "Host: uwaguessr.com" http://localhost/` → 301 to https (or 200 if testing locally)
