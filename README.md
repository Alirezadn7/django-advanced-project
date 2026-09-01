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
- Profile retrieval/update and password change endpoints
- Fully tested (`accounts/tests.py`)

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

```bash
cd core
python manage.py test accounts
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
