# Django Advanced Blog API

A backend-only blog project built with **Django** and **Django REST Framework**, focusing on applying advanced web development concepts in a practical project.

## About the Project

The main goal of this project is to learn and properly implement modern backend development concepts and technologies using Django.

The project focuses on building a clean and well-structured backend while working with APIs, authentication, database management, and other backend concepts.

This project includes backend development only and does not contain a frontend.

## Tech Stack

| Technology | Usage |
|------------|-------|
| Python 3.12 | Core language |
| Django 4.2 | Web framework |
| Django REST Framework 3.17 | API toolkit |
| SimpleJWT 5.5 | JWT authentication (rotation + blacklist) |
| google-auth 2.62 | Google Sign-In ID token verification |
| requests 2.32 | Bale OTP gateway HTTP client |
| django-filter 24.3 | API filtering |
| Pillow 12.2 | Image upload support |
| python-decouple 3.8 | Environment configuration |
| SQLite3 | Development database |
| Docker & Docker Compose | Containerization |

## Features

### Accounts & Authentication
- Custom email-based user model (`AbstractBaseUser`)
- Automatic profile creation via signal
- JWT login, refresh, and logout (token blacklisting)
- Google Sign-In (Gmail) — verifies Google ID tokens and returns the same JWT pair
- Phone OTP login via the **Bale.ai Gateway** (Safir `send_message`)
- Profile retrieval/update and password change endpoints
- Fully tested (`core/tests/`)

### Blog
- `Post`, `Category`, and `Tag` models
- Auto-generated Unicode slugs (Persian/English supported) with collision handling
- Slug-based routing (e.g. `/api/blog/posts/my-post-slug/`)
- `IsAuthorOrReadOnly` permission — only the author can edit/delete a post
- Optimized queries (`select_related` / `prefetch_related`)
- Filtering, searching, ordering, and pagination

## API Endpoints

### Accounts (`/api/accounts/`)

| Method | Endpoint | Access |
|--------|----------|--------|
| POST | `register/` | Public |
| POST | `login/` | Public |
| POST | `auth/google/` | Public |
| POST | `otp/request/` | Public (rate limited) |
| POST | `otp/verify/` | Public (rate limited) |
| POST | `token/refresh/` | Public |
| POST | `logout/` | Authenticated |
| GET / PATCH | `profile/me/` | Authenticated |
| POST | `change-password/` | Authenticated |

### Blog (`/api/blog/`)

| Method | Endpoint | Access |
|--------|----------|--------|
| GET / POST | `posts/` | Read public / Write authenticated |
| GET / PUT / PATCH / DELETE | `posts/{slug}/` | Read public / Write author |
| GET | `categories/` | Public |
| GET | `categories/{slug}/` | Public |
| GET / POST | `tags/` | Read public / Write authenticated |
| GET / PUT / PATCH / DELETE | `tags/{slug}/` | Read public / Write authenticated |

### Blog query parameters
- Filter: `?category=`, `?author=`, `?is_published=`
- Search: `?search=`
- Order: `?ordering=`
- Pagination: `?page=`

## Google Sign-In

The API uses the **ID token flow**: the client signs in with Google, sends the
returned `id_token` to Django, and Django responds with the project's regular
access/refresh JWT pair. No client secret or redirect URL is involved.

### 1. Create a Google OAuth client

1. Open the [Google Cloud Console](https://console.cloud.google.com/) and create (or select) a project.
2. Configure **APIs & Services → OAuth consent screen** (External). While the app is in
   testing, add your Google account under **Test users**.
3. Go to **Credentials → Create credentials → OAuth client ID → Web application**
   (use **Android** / **iOS** instead for a native app).
4. Add your frontend origins to **Authorized JavaScript origins**, e.g.
   `http://localhost:3000` and `http://127.0.0.1:8000`.
5. Copy the **Client ID** (not the secret) into `.env`:

```env
GOOGLE_OAUTH_CLIENT_ID=1234567890-abc.apps.googleusercontent.com
```

### 2. Exchange the Google token for JWTs

```http
POST /api/accounts/auth/google/
Content-Type: application/json

{ "id_token": "<credential returned by Google Identity Services>" }
```

Successful response (same shape as `login/`):

```json
{
  "refresh": "...",
  "access": "...",
  "id": 1,
  "email": "user@gmail.com",
  "first_name": "Ali"
}
```

Invalid, expired, or unverified Google tokens return `400` with an
`id_token` error. The access token is used exactly like a password-login
access token: `Authorization: Bearer <access>`.

### 3. Frontend example

```html
<script src="https://accounts.google.com/gsi/client" async defer></script>
<div id="gsi-button"></div>
<script>
  google.accounts.id.initialize({
    client_id: "YOUR_GOOGLE_CLIENT_ID",
    callback: async ({ credential }) => {
      const response = await fetch("/api/accounts/auth/google/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id_token: credential }),
      });
      const data = await response.json(); // { access, refresh, ... }
      localStorage.setItem("access", data.access);
    },
  });

  google.accounts.id.renderButton(document.getElementById("gsi-button"), {
    theme: "outline",
    size: "large",
  });
</script>
```

If the frontend is served from a different origin than the API, install and
configure `django-cors-headers` and add that origin to `CORS_ALLOWED_ORIGINS`.

### Testing with Docker

The compose setup publishes the API on **port 9000**. Register
`http://localhost:9000` (and `http://127.0.0.1:9000` if you use that host) as an
authorized JavaScript origin in Google Cloud Console.

Rebuild once so the container installs `google-auth`, then start it:

```bash
docker compose up --build
```

The container applies migrations automatically on startup. Open the dev-only
test page:

```text
http://localhost:9000/static/google-test.html
```

The page signs in with Google, prints the decoded ID token claims, and lets you
exercise `auth/google/`, `profile/me/`, `token/refresh/`, `logout/`, and an
invalid token. Its source is `core/core/staticfiles/google-test.html`.

### Account linking

- A verified Google email is automatically linked to an existing password
  account with the same address.
- If the email is already linked to a different Google account (`sub`),
  the request is rejected.
- Google-only users get an unusable password; they can still use every
  authenticated endpoint with their JWTs.

## Phone OTP Login (Bale.ai Gateway)

Users can sign in with an Iranian mobile number (`09xxxxxxxxx`). A one-time
code is delivered as an SMS/Bale message through the
[Bale Gateway](https://docs.bale.ai/gateway) (Safir `send_message`, bot OTP
message), and verification returns the project's regular access/refresh JWT
pair.

### Flow

```http
POST /api/accounts/otp/request/
Content-Type: application/json

{ "phone": "09123456789" }
```

Response: `{ "detail": "OTP code sent successfully.", "expires_in": 120, "message_id": "..." }`

```http
POST /api/accounts/otp/verify/
Content-Type: application/json

{ "phone": "09123456789", "code": "123456" }
```

Successful response — same shape as `login/` (JWT pair + user metadata).
`09..`, `+98..` and `98..` phone spellings are interchangeable.

### Gateway setup (`.env`)

```env
# Safir v3 send_message route (default): bot OTP message
BALE_API_ACCESS_KEY=your-bale-api-access-key
BALE_BOT_ID=123456789

# Optional legacy route: OAuth client_credentials + /send_otp
BALE_OTP_GATEWAY=v3
BALE_OTP_CLIENT_ID=...
BALE_OTP_CLIENT_SECRET=...

# Flow tuning
OTP_CODE_LENGTH=6          # 3-8 digits (gateway contract)
OTP_TTL_SECONDS=120        # code lifetime
OTP_PHONE_HOURLY_LIMIT=30  # Bale contract: max 30 sends/hour per phone
OTP_MAX_ATTEMPTS=5         # wrong guesses before lock-out
```

### Security design

- Codes are generated with a CSPRNG and **never stored in plaintext** — only a
  salted SHA-256 hash, verified with a constant-time comparison.
- A code is single-use (atomically claimed), expires after `OTP_TTL_SECONDS`,
  and self-locks after `OTP_MAX_ATTEMPTS` wrong guesses (atomic attempt
  counter, so parallel guesses cannot bypass the lock-out).
- Local DRF throttling (`1/min` request, `5/min` verify) on top of the
  gateway's own limits; gateway errors map to clean `400/402/404/429/502`
  responses without leaking credentials.
- The gateway wallet balance is never exposed in public API responses.
- A dev-only browser test page lives at `/api/accounts/otp/test/` and is only
  registered when `DEBUG=True`.

### Account linking

- Verifying an OTP for a phone number that already owns an account logs that
  account in (its status must be active).
- An authenticated caller whose account has **no phone yet** claims the
  verified number and gets it linked instead of creating a duplicate account.
- Phone-only users are created with e-mail placeholder `{phone}@otp.local`
  and an unusable password; they can use every authenticated endpoint with
  their JWTs.

## Installation

### Local setup

```bash
python -m venv venv

# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and set a real `SECRET_KEY`, then:

```bash
cd core
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```

API available at `http://127.0.0.1:8000/`.

### Docker

```bash
docker-compose up --build
```

Access the app at `http://localhost:9000/`.

## Running Tests

The test suite uses **pytest** (gateway mocks/fixtures are pytest-native).
Run it from the repository root, where `pytest.ini` points at `core/tests`:

```bash
pytest
```

Filter to just the OTP flow:

```bash
pytest core/tests/test_otp.py
```

## Project Structure

```text
django-advanced-project/
├── core/
│   ├── accounts/          # Authentication, profile, JWT
│   ├── blog/               # Post, Category, Tag
│   ├── core/               # Settings, URLs, WSGI/ASGI
│   │   └── settings/       # base, development, production
│   └── manage.py
├── docker-compose.yml
├── dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

## Notes & Known Limitations

- The project currently uses **SQLite** for development; switch to PostgreSQL for production.
- `core.settings` is loaded via `DJANGO_SETTINGS_MODULE`; production deployment should point to `core.settings.production`.
- This is a backend-only project with no frontend included.

## Status

Actively in development.
