# Smart Canteen Management System

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg?logo=python)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.1.7-0C4B33.svg?logo=django)](https://www.djangoproject.com/)
[![Tests](https://img.shields.io/badge/Tests-30%20Passed-brightgreen.svg)]()
[![License](https://img.shields.io/badge/License-MIT-green.svg)]()

A full-featured, production-ready **Smart Canteen & Meal Subscription Platform** built with **Python 3.12** and **Django 5.1**. Designed for campus and corporate dining facilities, the system streamlines food ordering, daily meal subscription claims, automated inventory management, payment processing, and health tracking.

---

## 🌟 Key Features

### 1. 🔐 Role-Based Authentication & Profiles (`authentication`)
- Custom User Model (`CustomUser` extending `AbstractUser`) with role differentiation (`student`, `faculty`).
- Secure signup with standard password validation (min length, uppercase, lowercase, digit, special character).
- Full CSRF protection and session-to-database cart synchronization upon login.
- Dedicated user dashboard showing recent orders, status history, and token identifiers.

### 2. 🍲 Meal Subscription & Daily Claim Engine (`main`)
- **Subscription Plans**: Weekly, monthly, and quarterly meal plans with configurable meals-per-day quotas.
- **Daily Meal Claims**: Automated daily allowance tracking prevents over-claiming.
- **Atomic Transactions**: Database transactions (`transaction.atomic()`) ensure stock deductions and meal quota decrements are concurrency-safe.
- **Health & Calorie Dashboard**: Aggregates daily caloric intake from both ad-hoc orders and claimed subscription meals using Django ORM aggregation (`TruncDate`, `Sum`, `F`).

### 3. 🛒 Shopping Cart & Role-Based Coupons (`cart`)
- Database and session synchronized cart items with real-time stock bounds checking.
- Role-targeted discount coupons (`student` vs. `faculty`) with expiration dates and eligible product constraints.
- Real-time subtotal, discount, and grand total calculations.

### 4. 💳 Razorpay Payments & Order Fulfillment (`checkout`)
- Razorpay payment gateway integration for meal orders and subscription purchases.
- Server-side signature and payment verification (`razorpay.Client`).
- Unique order pickup token generation (e.g. `ORD10001`, `CLM20002`).
- Asynchronous status updates: transition notifications when meals move to `Processing` and `Delivered`/`Ready for Pickup`.
- Order feedback and rating system (1 to 5 stars) with testimonials showcase.

### 5. 🔔 Multi-Channel Notifications
- **Email Notifications**: Automated transactional emails on order placement and preparation status updates.
- **Web Push Notifications**: Browser push notifications powered by VAPID (`pywebpush`) when orders are ready for counter pickup.

---

## 🏗️ Architecture & App Structure

```
smart_canteen/
│
├── canteen/                  # Project configuration root
│   ├── settings.py           # Environment-configured settings (12-Factor App)
│   ├── urls.py               # Top-level URL routing
│   ├── wsgi.py / asgi.py     # WSGI/ASGI entrypoints with dotenv loading
│
├── authentication/           # User identity & account management
│   ├── forms.py              # SignUpForm & LoginForm with validation
│   ├── models.py             # CustomUser model (student / faculty roles)
│   ├── views.py              # Auth views (signup, login, logout, profile)
│   └── tests.py              # 11 unit/integration tests
│
├── main/                     # Core product catalog & subscription engine
│   ├── models.py             # Product, MealSubscriptionPlan, UserSubscription, etc.
│   ├── views.py              # Catalog, Search API, Plans, Claim Meal, Health
│   └── tests.py              # 7 unit/integration tests
│
├── cart/                     # Cart persistence & promotional discounts
│   ├── models.py             # CartItem, Coupon models
│   ├── context_processors.py # Global cart counter context processor
│   ├── views.py              # Cart add, update, delete, coupon application
│   └── tests.py              # 6 unit/integration tests
│
├── checkout/                 # Order lifecycle, Razorpay, feedback
│   ├── models.py             # Order, Feedback models
│   ├── utils.py              # VAPID webpush and post_save email signals
│   ├── views.py              # Checkout, Razorpay webhook/verification, reviews
│   └── tests.py              # 6 unit/integration tests
│
├── templates/                # Server-rendered HTML templates
├── static/                   # Static CSS, JS, vendor libraries
├── .env.example              # Template for environment configuration
├── Procfile                  # Production process definition (Gunicorn)
├── requirements.txt          # Python dependencies
└── manage.py                 # Django administrative entrypoint
```

---

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| **Backend** | Python 3.12, Django 5.1.7 |
| **Database** | SQLite (development) / PostgreSQL (production) |
| **Security** | Django CSRF, Python Dotenv, VAPID WebPush, Role RBAC |
| **Payments** | Razorpay Python SDK |
| **Static & Media** | WhiteNoise 6.9, Pillow |
| **Testing** | Django TestCase (`unittest` framework) — 30 automated tests |
| **Deployment** | Gunicorn 23.0, Render-ready Procfile |

---

## 🔒 Security Best Practices Implemented

- **Zero Hardcoded Secrets**: All sensitive keys (`SECRET_KEY`, Razorpay keys, Gmail app passwords, VAPID private keys) are decoupled into `.env` and loaded via `python-dotenv`.
- **Full CSRF Protection**: Removed all insecure `@csrf_exempt` decorators from authentication and state-changing views. All forms and fetch requests transmit `X-CSRFToken`.
- **Authorization & Ownership Checks**: Added `@login_required` on all cart and checkout endpoints; payment verification validates order ownership.
- **Git Hygiene**: Clean `.gitignore` untracking virtual environments, database files, compiled bytecode, and secrets.
- **Race Condition Prevention**: `transaction.atomic()` and `.refresh_from_db()` ensure stock deductions and subscription meal claims cannot be double-spent.

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.12+
- Git

### 2. Clone and Setup Environment

```bash
git clone https://github.com/your-username/smart_canteen.git
cd smart_canteen

# Create and activate virtual environment
python -m venv env

# On Windows (PowerShell):
.\env\Scripts\Activate.ps1

# On Linux / macOS:
source env/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your configuration:

```bash
cp .env.example .env
```

| Variable | Description | Default / Example |
|---|---|---|
| `SECRET_KEY` | Django cryptographic secret | (Auto-generated or custom string) |
| `DEBUG` | Enable debug mode (`True` for local dev) | `True` |
| `ALLOWED_HOSTS` | Comma-separated list of hostnames | `127.0.0.1,localhost` |
| `RAZORPAY_KEY_ID` | Razorpay API key ID | `rzp_test_...` |
| `RAZORPAY_KEY_SECRET` | Razorpay API key secret | `...` |
| `EMAIL_HOST_USER` | Gmail address for transactional emails | `your-email@gmail.com` |
| `EMAIL_HOST_PASSWORD` | Gmail App Password (16 characters) | `...` |
| `VAPID_PUBLIC_KEY` | Public key for browser push notifications | `...` |
| `VAPID_PRIVATE_KEY` | Private key for browser push notifications | `...` |
| `VAPID_ADMIN_EMAIL` | Admin contact for VAPID claims | `admin@example.com` |

### 5. Run Migrations & Seed Data

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 6. Start Development Server

```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000/` in your browser.

---

## 🧪 Running the Test Suite

The repository includes a comprehensive 30-test suite verifying models, forms, authorization boundaries, and API workflows across all apps.

```bash
# Run all tests
python manage.py test

# Run tests by app
python manage.py test authentication
python manage.py test cart
python manage.py test main
python manage.py test checkout
```

### Test Coverage Highlights:
- **`authentication` (11 tests)**: Custom user creation, password complexity checks, duplicate email/username rejection, login authentication, session cart sync, and logout.
- **`cart` (6 tests)**: Item addition, quantity increments, stock ceiling validation, cart deletion, coupon validation with role verification, and expiration date checks.
- **`main` (7 tests)**: Product search with missing image resilience, subscription duration and quota calculations, daily meal claim limits, and health dashboard calorie aggregations.
- **`checkout` (6 tests)**: Unauthenticated checkout redirect, empty/active cart totals, email dispatch only upon status change, feedback submission, and duplicate prevention.

---

## 🌐 Production Deployment

The project is preconfigured for deployment on platforms like Render or Heroku:

- **Procfile**: `web: gunicorn canteen.wsgi`
- **Static Assets**: WhiteNoise handles compressed static asset delivery automatically.
- Ensure all environment variables are added to the hosting environment dashboard.

---

## 📜 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.