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
python manage.py migrate
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

## Admin and database

- Create a superuser: `python manage.py createsuperuser`
- Admin UI: **http://127.0.0.1:8000/admin/**
- Default database: SQLite at `db.sqlite3` (ignored by git via `.gitignore`)
