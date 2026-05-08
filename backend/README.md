# Smart Agri AI — Backend

Django REST API for the project. Python dependencies are listed in `requirements.txt`.

## Prerequisites

- Python 3.12+ (3.14 is fine if your environment matches the one used to generate `requirements.txt`)

## First-time setup

From this directory (`backend/`):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py seed_firestore_catalog
```

On Windows, activate the virtualenv with `.venv\Scripts\activate` instead of `source .venv/bin/activate`.

## Start the development server

With the virtualenv activated:

```bash
python manage.py runserver
```

The API defaults to **http://127.0.0.1:8000/**. Example check:

- **GET** [http://127.0.0.1:8000/api/health/](http://127.0.0.1:8000/api/health/)

To bind another host or port:

```bash
python manage.py runserver 0.0.0.0:8765
```

## Optional environment variables

| Variable | Purpose |
|----------|---------|
| `DJANGO_SECRET_KEY` | Secret key (required in production; dev default exists in settings) |
| `DJANGO_DEBUG` | `true` / `false` — controls debug mode |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hosts (default: `localhost,127.0.0.1`) |
| `CORS_ALLOWED_ORIGINS` | Comma-separated origins when `DJANGO_DEBUG` is false |

### Firebase

The backend uses the [Firebase Admin Python SDK](https://firebase.google.com/docs/admin/setup). Configure **one** credential source:

| Variable | Purpose |
|----------|---------|
| `FIREBASE_CREDENTIALS_PATH` | Absolute or project-relative path to the service account JSON file |
| `FIREBASE_CREDENTIALS_JSON` | Raw JSON string (e.g. one-line) — common in some hosts |
| `FIREBASE_CREDENTIALS_BASE64` | Base64-encoded service account JSON |

Optional overrides:

| Variable | Purpose |
|----------|---------|
| `FIREBASE_PROJECT_ID` | GCP / Firebase project id (usually inferred from the JSON) |
| `FIREBASE_STORAGE_BUCKET` | Default bucket id, e.g. `my-project.appspot.com` |
| `FIREBASE_DATABASE_URL` | Realtime Database URL, e.g. `https://my-project-default-rtdb.firebaseio.com` |

- **Auth:** Clients send `Authorization: Bearer <Firebase ID token>`. DRF uses `api.authentication.FirebaseAuthentication`; views can use `IsAuthenticated` and read `request.user.uid` / `request.user.email`.
- **Guest / anonymous sign-in (Flutter):** In [Firebase Console](https://console.firebase.google.com/) → your project → **Authentication** → **Sign-in method**, enable **Anonymous**. If it stays disabled, `signInAnonymously()` fails (often with a generic “internal error” on iOS). The backend maps missing emails to `{uid}@guest.local` when syncing users.

**If `/api/users/sync/` returns 500 or 503 “Firebase Admin not configured”:** the Django process has no service account. In [Firebase Console](https://console.firebase.google.com/) → **Project settings** → **Service accounts** → **Generate new private key**, save the JSON file somewhere safe (do not commit it). Set in `backend/.env`, for example:

`FIREBASE_CREDENTIALS_PATH=/absolute/path/to/your-project-firebase-adminsdk-xxxxx.json`

Restart `runserver` so `load_dotenv` picks it up. The Flutter `GoogleService-Info.plist` / `google-services.json` are **not** a substitute — the server needs this **Admin** JSON.
- **Firestore / Storage / RTDB:** Import helpers from `api.firebase_client` (`get_firestore_client`, `get_storage_bucket`, `get_rtdb_reference`). The app initializes lazily on first use.

### Admin catalog API

Firestore user documents must have `role: "admin"` for these routes (otherwise **403**). All use `Authorization: Bearer <Firebase ID token>`.

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/admin/catalog/plants/` | List plants |
| `GET` / `PATCH` | `/api/admin/catalog/plants/<plant_id>/` | Read or update plant names/descriptions (EN/AR) |
| `GET` | `/api/admin/catalog/plants/<plant_id>/diseases/` | List diseases for a plant |
| `GET` / `PATCH` | `/api/admin/catalog/diseases/<disease_id>/` | Read or update disease names, descriptions, causes, treatment (EN/AR) |

Updates merge into the existing Firestore documents.

## Vision model (image diagnosis)

Image diagnoses use an in-process **PyTorch + timm** checkpoint (same format as `models/train_all_models.py` / `models/app.py`). Default weights path is **`models/final_model.pth`** relative to this `backend/` directory.

- Install dependencies with `pip install -r requirements.txt`. PyTorch wheels are large. For **GPU/CUDA**, use the selector at [pytorch.org](https://pytorch.org/get-started/locally/) instead of the default CPU wheels if needed.
- After pulling the project, ensure the `.pth` file exists at that path (or set `VISION_MODEL_PATH`). Checkpoint files are not always committed to git because of size; copy your trained `final_model.pth` into `backend/models/` when deploying.

### Vision-related environment variables

| Variable | Purpose |
|----------|---------|
| `VISION_MODEL_PATH` | Path to `final_model.pth` (absolute or relative to `backend/`) |
| `VISION_MIN_CONFIDENCE` | If the model’s top probability is below this (default `0.35`), the stored disease is **Unknown / low confidence** |
| `VISION_IMAGE_MAX_BYTES` | Max download size for `image_url` (default 10 MiB) |
| `VISION_IMAGE_DOWNLOAD_TIMEOUT` | HTTP timeout seconds for downloading the image (default `30`) |
| `VISION_UNKNOWN_DISEASE_NAME_EN` | English `Disease.name_en` for the fallback row (default `Unknown / low confidence`) |
| `VISION_MODEL_NAME` | Fallback timm architecture when checkpoint has no `config.model` (default `efficientnet_b1`) |

**Text diagnosis:** `POST` with `input_type: text` uses a TF-IDF cosine similarity model (`tfidf_v1` in `ai_logs`). Disease description files are loaded from `TEXT_MODEL_PATH` (default `models/text_classes/`). The minimum similarity threshold is controlled by `TEXT_MIN_CONFIDENCE` (default `0.10`).

### Gradio demo (`models/app.py`)

From `backend/models/` (with the same virtualenv and packages as the API):

```bash
cd models
python app.py --model-path final_model.pth
```

The script adds the parent `backend/` directory to `sys.path` so it can import the shared `vision` package.

## Firestore data initialization

- Seed the lemon catalog in Firestore: `python manage.py seed_firestore_catalog`
- Optional one-time legacy migration from SQLite: `python manage.py backfill_sqlite_to_firestore --sqlite-path ./db.sqlite3`
- Validate migration parity by counts: `python manage.py check_firestore_parity --sqlite-path ./db.sqlite3`
- Runtime persistence is Firebase Firestore only; Django does not use SQLite for app tables anymore.
