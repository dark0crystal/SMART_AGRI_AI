# Smart Agri AI — Backend

Django REST API for the mobile app. Python dependencies are in `requirements.txt` (Django 6.0.3, djangorestframework, firebase-admin, PyTorch stack for image inference, scikit-learn for text).

## Stack and persistence

- **Runtime data** lives in **Google Cloud Firestore** (users, bilingual plant/disease catalog, diagnoses, `ai_logs`).
- **Django’s default database** is the built-in **`dummy`** engine (`config/settings.py`), so the API does **not** use SQLite or any SQL server for live requests. ORM model classes under `api/models.py` are kept for schema documentation and optional migration utilities; the app reads and writes through `api/firestore_repository.py`.
- **Firebase Admin SDK** verifies ID tokens, and optional **Firebase Storage** rules apply when validating diagnosis image URLs.

## Prerequisites

- **Python 3.12+** (match whatever version you used when pinning dependencies; 3.13/3.14 are fine if wheels install cleanly).

## First-time setup

From this directory (`backend/`):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python manage.py seed_firestore_catalog

cp .env.example .env
```

On Windows, activate the virtualenv with `.venv\Scripts\activate` instead of `source .venv/bin/activate`.

## Start the development server

With the virtualenv activated:

```bash
python manage.py runserver
```

The API base URL is **http://127.0.0.1:8000/api/**. Quick check:

- **GET** [http://127.0.0.1:8000/api/health/](http://127.0.0.1:8000/api/health/)

To bind another host or port:

```bash
python manage.py runserver 0.0.0.0:8765
```

## REST API overview

Unless noted, protected routes expect **`Authorization: Bearer <Firebase ID token>`**.

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `GET` | `/api/health/` | None | Liveness / JSON status |
| `POST` | `/api/users/sync/` | Firebase | Upsert the caller’s user row in Firestore (optional JSON `{"username": "..."}`) |
| `GET` | `/api/me/` | Firebase | Return the synced Firestore user profile |
| `GET` | `/api/diagnoses/` | Firebase | Paginated list of the caller’s diagnoses (`?page=`; page size **20**) |
| `POST` | `/api/diagnoses/` | Firebase | Create a diagnosis (image or text); runs vision / TF-IDF and writes diagnosis + `ai_logs` |
| `GET` | `/api/diagnoses/<id>/` | Firebase | Single diagnosis owned by the caller |

**Admin catalog** (Firestore user document must have **`role: "admin"`** or routes return **403**):

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/admin/catalog/plants/` | List plants |
| `GET` / `PATCH` | `/api/admin/catalog/plants/<plant_id>/` | Read or update plant fields (EN/AR) |
| `GET` | `/api/admin/catalog/plants/<plant_id>/diseases/` | List diseases for a plant |
| `GET` / `PATCH` | `/api/admin/catalog/diseases/<disease_id>/` | Read or update disease fields |

Updates merge into existing Firestore documents.

**Debug only** (`DJANGO_DEBUG=true`): **GET** `/api/debug/vision-test/` serves a small HTML form to upload an image and inspect PyTorch inference (including Witch’s Broom guard output). Returns **404** when `DEBUG` is false.

## Optional environment variables

| Variable | Purpose |
|----------|---------|
| `DJANGO_SECRET_KEY` | Secret key (required in production; dev default exists in settings) |
| `DJANGO_DEBUG` | `true` / `false` — controls debug mode and CORS behavior |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hosts (default: `localhost,127.0.0.1`) |
| `CORS_ALLOWED_ORIGINS` | Comma-separated origins when `DJANGO_DEBUG` is false |

### Firebase

The backend uses the [Firebase Admin Python SDK](https://firebase.google.com/docs/admin/setup). Configure **one** credential source:

| Variable | Purpose |
|----------|---------|
| `FIREBASE_CREDENTIALS_PATH` | Absolute path or path relative to `backend/` for the service account JSON |
| `FIREBASE_CREDENTIALS_JSON` | Raw JSON string (e.g. one line) |
| `FIREBASE_CREDENTIALS_BASE64` | Base64-encoded service account JSON |

Optional overrides:

| Variable | Purpose |
|----------|---------|
| `FIREBASE_PROJECT_ID` | GCP / Firebase project id (usually inferred from the JSON) |
| `FIREBASE_STORAGE_BUCKET` | Default bucket id, e.g. `my-project.appspot.com` |
| `FIREBASE_DATABASE_URL` | Realtime Database URL (only if you use RTDB helpers) |

**Authentication:** Clients send `Authorization: Bearer <Firebase ID token>`. DRF uses `api.authentication.FirebaseAuthentication`; authenticated views read `request.user.uid` and `request.user.email`.

Users without an email (e.g. some guest / anonymous Firebase accounts) are normalized during **`POST /api/users/sync/`** to a synthetic address `{uid}@guest.local` so a unique Firestore user row can be stored. Prefer normal email/password or OAuth flows for production accounts.

**If `/api/users/sync/` returns 500 or 503 “Firebase Admin not configured”:** the process has no service account. In [Firebase Console](https://console.firebase.google.com/) → **Project settings** → **Service accounts** → **Generate new private key**, save the JSON outside git and point `FIREBASE_CREDENTIALS_PATH` at it in `backend/.env`. Restart `runserver`. Client `GoogleService-Info.plist` / `google-services.json` are **not** sufficient for the server — it needs the **Admin** JSON.

**Firestore / Storage:** Import helpers from `api.firebase_client` (`get_firestore_client`, `get_storage_bucket`, …). Initialization is lazy on first use.

### Image URL allowlist (diagnosis uploads)

If set, **`POST /api/diagnoses/`** with `input_type: image` rejects `image_url` values that do not start with one of the configured HTTPS prefixes (intended for Firebase Storage URLs).

| Variable | Purpose |
|----------|---------|
| `ALLOWED_STORAGE_IMAGE_URL_PREFIXES` | Comma-separated URL prefixes, e.g. `https://firebasestorage.googleapis.com/` |

## Vision model (image diagnosis)

Image diagnoses use an in-process **PyTorch + timm** checkpoint (same format as `models/train_all_models.py` / `models/app.py`). Default weights path is **`models/final_model.pth`** relative to this `backend/` directory.

- Install dependencies with `pip install -r requirements.txt`. PyTorch wheels are large. For **GPU/CUDA**, use the selector at [pytorch.org](https://pytorch.org/get-started/locally/) instead of the default CPU wheels if needed.
- After pulling the project, ensure the `.pth` file exists at that path (or set `VISION_MODEL_PATH`). Checkpoint files are often omitted from git because of size; copy your trained `final_model.pth` into `backend/models/` when deploying.

### Vision-related environment variables

| Variable | Purpose |
|----------|---------|
| `VISION_MODEL_PATH` | Path to `final_model.pth` (absolute or relative to `backend/`) |
| `VISION_MIN_CONFIDENCE` | If the model’s top probability is below this (default `0.35`), the stored disease is treated as unknown / low confidence |
| `VISION_IMAGE_MAX_BYTES` | Max download size for `image_url` (default 10 MiB) |
| `VISION_IMAGE_DOWNLOAD_TIMEOUT` | HTTP timeout seconds for downloading the image (default `30`) |
| `VISION_UNKNOWN_DISEASE_NAME_EN` | English catalog name for the fallback disease row (default `Unknown / low confidence`) |
| `VISION_MODEL_NAME` | Fallback timm architecture when checkpoint has no `config.model` (default `efficientnet_b1`) |
| `VISION_WITCH_BROOM_LABEL` | Class label name used by the Witch’s Broom guard (default `Witch's Broom`) |
| `VISION_WITCH_BROOM_MAX_DIFF` | Guard threshold: max difference between top-1 and Witch’s Broom prob before forcing Witch’s Broom (default `0.35`) |
| `VISION_LOG_CLASS_PROBS` | If `true`/`1`/`yes`, include richer class-probability debug in logs (default `true`) |

**Text diagnosis:** `POST` with `input_type: text` uses a TF-IDF cosine similarity model (`tfidf_v1` in `ai_logs`). Disease description files are loaded from `TEXT_MODEL_PATH` (default `models/text_classes/`). Minimum similarity is controlled by `TEXT_MIN_CONFIDENCE` (default `0.10`).

### Gradio demo (`models/app.py`)

From `backend/models/` (with the same virtualenv and packages as the API):

```bash
cd models
python app.py --model-path final_model.pth
```

The script adds the parent `backend/` directory to `sys.path` so it can import the shared `vision` package.

## Firestore data initialization

- Seed the lemon catalog: `python manage.py seed_firestore_catalog`
- Optional one-time migration from a legacy SQLite file: `python manage.py backfill_sqlite_to_firestore --sqlite-path ./db.sqlite3`
- Compare counts after migration: `python manage.py check_firestore_parity --sqlite-path ./db.sqlite3`

Runtime API persistence is **Firestore only**; the dummy Django database is not used for application data.
