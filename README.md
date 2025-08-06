# Genly.ai  – AI-Powered Smart Email Generator & Bulk Sender

Genly.ai is a powerful, Gmail-integrated web application that helps users generate and send high-quality, tone-adapted emails using cutting-edge NLP models (e.g., Mistral 7B via OpenRouter). It offers both **single** and **bulk email** workflows, advanced preview options, Gmail API integration, CSV-based personalization, and mobile-first flexibility.

---

## 🌟 Key Features

- 🔐 Secure Google OAuth login (Django Allauth)
- ✨ Generate emails using context + tone (e.g., professional, casual, apologetic)
- 🧠 Powered by OpenRouter's Mistral 7B or similar LLM
- 📝 Real-time editable subject and body
- 📤 Single Email Flow:
  - Desktop: Redirects to Gmail compose
  - Mobile: Sends directly via Gmail API
- 📎 Supports attachments (especially on mobile)
- 📂 Bulk Email Flow:
  - Upload CSV with fields like `{{name}}`, `{{email}}`
  - Personalized email generation using Jinja2 templates
  - Full preview before sending
- 📱 Responsive UI for mobile and desktop
- 🌐 Works like Yet Another Mail Merge (YAMM) with AI

---

## 📁 Folder Structure

```
genly-ai/
│
├── templates/
│   ├── landing.html
│   ├── home.html
│   ├── mobile_preview.html
│   └── redirect_to_gmail.html
│
├── static/
│   └── favicon.png
│
├── core/
│   ├── views.py
│   ├── urls.py
│   └── ...
├── .env.example
├── manage.py
└── requirements.txt
```

---

## 🛠 Tech Stack

- **Framework:** Django
- **Frontend:** HTML, CSS, Jinja2 templates
- **Auth:** Google Login (Django Allauth)
- **NLP Engine:** Mistral 7B via OpenRouter API
- **Gmail API:** OAuth2 + Gmail send
- **Templating:** Jinja2 for field injection in bulk mode

---

## ⚙️ Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/genly-ai.git
cd genly-ai
```

### 2. Create Virtual Environment

```bash
python -m venv env
source env/bin/activate  # Windows: env\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Create `.env` File

```env
SECRET_KEY=your_django_secret_key
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_CREDENTIALS_JSON={"web": {...}}  # As one line
OPENROUTER_API_KEY=your_openrouter_key
```

### 5. Migrate & Run Server

```bash
python manage.py migrate
python manage.py runserver
```

Then open [http://localhost:8000](http://localhost:8000)

---

## 🧠 How It Works

1. User logs in with Google
2. Provides email context + tone
3. AI generates subject + body
4. User previews and edits result
5. Email is sent directly or redirected to Gmail (based on device)
6. For bulk: upload CSV → fields like `{{name}}` auto-filled → preview → send

---

## 🧪 Example Use Cases

- HR sending personalized onboarding emails
- Freelancers responding to leads with appropriate tone
- Marketing teams running bulk outreach with dynamic content

---

## 📌 TODO

- [ ] Add multilingual email generation
- [ ] Enable email scheduling
- [ ] Save drafts/history for reuse
- [ ] Improve mobile UX further
- [ ] Add basic unit tests

---

## 📄 License
This project is licensed under the [CC BY-NC 4.0 License](https://creativecommons.org/licenses/by-nc/4.0/) — non-commercial use only.

---

## 🙌 Author

Built by [Sharik Hassan](https://github.com/shark4real)
