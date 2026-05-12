# AI Job Application Agent

An AI-powered Telegram bot that helps automate student job applications in Graz, Austria.

The bot generates professional German job application emails using OpenAI, attaches the correct CV/documents based on the selected job category, asks for user confirmation, and automatically sends the application email using SMTP.

---

# Features

- Telegram-based workflow
- AI-generated German job applications
- Multiple job categories
- Automatic PDF attachment handling
- Approval/cancel confirmation system
- SMTP email sending with Brevo
- Local development + Railway deployment support

---

# Workflow

1. User starts the Telegram bot using `/start`
2. Bot asks for job category:
   - Kitchen
   - Cafe
   - Warehouse
3. User sends:
   - Job description
   - Recruiter/company email
4. AI generates:
   - German subject line
   - Short German application email
5. Bot shows:
   - Generated email
   - Attached files
6. User chooses:
   - APPROVE
   - CANCEL
7. If approved:
   - Bot sends email automatically with attachments

---

# Tech Stack

- Python
- python-telegram-bot
- OpenAI API
- Brevo SMTP
- Flask
- Railway
- dotenv

---

# Project Structure

```text
job_application_agent/
│
├── documents/
│   ├── Kitchen/
│   ├── Cafe/
│   └── Warehouse/
│
├── main.py
├── requirements.txt
├── .env
├── .gitignore
└── README.md
