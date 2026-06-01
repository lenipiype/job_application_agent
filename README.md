# AI-Powered Job Application Agent

An advanced, production-grade, and secure AI-powered Telegram Bot that fully automates the job application process for student employment in Graz, Austria.

The bot generates highly tailored, professional German application emails using OpenAI's **GPT-4o**, validates recruiter email targets, parses attachment payloads, presents interactive **Send / Edit / Cancel** options via inline keyboards, sends applications securely using SMTP (with 3x backoff retries), and logs history to an isolated SQLite database.

---

## 💻 Tech Stack & Architecture

- **Core Engine**: Python 3.12, Flask (for `/health` endpoint checks)
- **User Interface**: `python-telegram-bot` (v21.x) ConversationHandler utilizing dynamic inline keyboards
- **AI Generation**: OpenAI API (**GPT-4o** model)
- **Email Transfer**: Secure `smtplib` utilizing `STARTTLS` on port 587
- **Database Logs**: SQLite3 (Standard Library)
- **Containerization**: Multi-stage Docker running under a dedicated non-privileged user (`appuser` UID `10001`)
- **CI/CD Automation**: GitHub Actions pipeline covering lint checking (Ruff), unit testing (pytest), container registry packaging (GHCR), and OCI cloud deployment via secure SSH

---

## 📁 Repository Structure

```text
job_application_agent/
│
├── .github/
│   └── workflows/
│       └── ci.yml             # Automated CI/CD (Ruff -> Pytest -> Docker Build -> GHCR -> OCI SSH Deploy)
│
├── documents/                 # PDF Resumes, CVs, and credentials sorted by category
│   ├── Cafe/
│   ├── Kitchen/
│   └── Warehouse/
│
├── tests/                     # Isolated Pytest Unit Testing Suite
│   ├── __init__.py
│   ├── test_ai_generator.py   # OpenAI draft formatting & robust parse tests
│   ├── test_db.py             # SQLite schema creation & stats aggregation tests
│   └── test_email_sender.py   # Attachment globbing, SMTP connect, & retry backoff tests
│
├── src/                       # Refactored Modular Codebase
│   ├── __init__.py
│   ├── config.py              # Environment loading, logging, and Whitelist filters
│   ├── database.py            # SQLite connections, inserts, history, and stats
│   ├── email_sender.py        # PDF scanning, multipart mail construction, and backoff SMTP retries
│   ├── ai_generator.py        # GPT-4o application drafting and tag parser
│   └── bot.py                 # Telegram Bot conversation handler states & command routers
│
├── main.py                    # Dual-thread Entry Point: background Flask server + Telegram polling loop
├── Dockerfile                 # Multi-stage secure non-root Docker build
├── docker-compose.yml         # Container runner mapping database storage and port 10000
├── requirements.txt           # Python dependency bounds
├── pyproject.toml             # Ruff linter and Pytest parameters
└── README.md                  # Project Documentation
```

---

## ⚙️ Environment Variables Required

Create a `.env` file in the project root:

```env
TELEGRAM_TOKEN=your_telegram_bot_token
OPENAI_API_KEY=your_openai_api_key
EMAIL_ADDRESS=lenipiype7@gmail.com
SMTP_SERVER=smtp-relay.brevo.com
SMTP_PORT=587
SMTP_LOGIN=aa7b3d001@smtp-brevo.com
SMTP_PASSWORD=your_brevo_smtp_password
ALLOWED_USER_IDS=your_telegram_user_id_comma_separated
DB_PATH=data/applications.db
PORT=10000
```

---

## 🚀 Quickstart Guide

### 1. Local Development (using virtualenv / pip)
Ensure you have Python 3.12+ installed.

```bash
# Clone the repository
git clone https://github.com/lenipiype/job_application_agent.git
cd job_application_agent

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install pytest ruff

# Set up environment variables (.env)
cp .env.example .env  # configure your keys in .env

# Run unit tests
pytest -v

# Run Ruff linter checks
ruff check .

# Start the application
python main.py
```

### 2. Local Development (using Docker Compose)
```bash
# Start the container and build locally
docker-compose up --build -d

# Check running container health
curl http://localhost:10000/health
```

---

## 🤖 Telegram Bot Commands

- `/start` - Initiates the step-by-step job application wizard (cancels any active state).
- `/history` - Pulls and renders the last 10 applications logged in SQLite.
- `/stats` - Displays total applications successfully sent, categorized by group.
- `/cancel` - Aborts the current process at any step and wipes progress cache.

---

## 🔒 Security & Safety Principles

1. **User Whitelisting**: The bot contains a whitelist check (`ALLOWED_USER_IDS`). If set, only matching user IDs can interact with the bot, silently rejecting unauthorized users to protect your credentials.
2. **Non-Root Docker Execution**: The `Dockerfile` creates a non-root system user (`appuser` with UID `10001`). If compromised, the container has zero administrative root access to the host.
3. **Data Protection**: Local databases (`*.db`) and folders (`data/`) are fully ignored in `.dockerignore` to prevent accidental credential leakage into public GitHub Container registries.

---

## 🔄 Automated CI/CD & Cloud Deployment

This project is built for **zero-click deployment** on push merges to the `main` branch:

1. **Ruff** checks Python PEP8 formatting.
2. **Pytest** runs the comprehensive test suite.
3. **Docker Build-Push** compiles the container and publishes it to **GitHub Container Registry (GHCR)**.
4. **Deploy Step (SSH to Oracle VM)**:
   - Connects to your Oracle VM instance.
   - Pre-creates runtime directory folders (`data/`, `documents/`) and assigns wide write permissions (`chmod 777`) so the non-root container can successfully write the SQLite db.
   - Automatically compiles the `.env` configuration file directly from GitHub repository Secrets.
   - Pulls down the newly built image and restarts the container safely.
