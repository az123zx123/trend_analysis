# 📰 News Trend Tracker

A full-stack application that periodically fetches news by topic, summarizes the content using OpenAI, and analyzes emerging trends — all accessible through a React-based frontend and Flask backend.

## 🚀 Features

- 🔍 Search and summarize news articles by topic
- 🧠 AI-powered trend analysis using OpenAI GPT
- 🔁 Scheduled background jobs with APScheduler
- 🔧 Configurable topics and scheduling via `config.json`
- 🌐 Interactive React frontend with live data display
- 🗃️ PostgreSQL database for storing articles and summaries

---

## 📦 Tech Stack

| Layer       | Tech           |
|-------------|----------------|
| Frontend    | React |
| Backend     | Flask + Flask-APScheduler |
| AI          | OpenAI GPT-4o |
| Database    | PostgreSQL |
| Deployment  | Gunicorn |
---

## 🛠️ Setup Instructions

### 1. Install system dependencies
```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git curl postgresql postgresql-contrib nginx nodejs npm
```

### 2. Set Up PostgreSQL (If not already)
Replace the user name and password. Update DB config in server.py accordingly.
```bash
sudo -u postgres psql
# Inside psql shell:
CREATE DATABASE news;
CREATE USER news_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE news TO news_user;
\q
```

### 3. Configure Environment Variables
Set the following before running the app:
```bash
export OPENAI_KEY=your_openai_api_key
export NEWSAPI_KEY=your_newsapi_api_key
```

###  4. Clone the Repository
```bash
git clone https://github.com/az123zx123/trend_analysis.git
cd trend_analysis
```

### 5. Run setup script
This builds frontend, copies files, installs dependencies, initializes the DB, and starts server.
```bash
chmod +x setup.sh
./setup.sh
```

### 6. Run the App
```bash
python3 ./api/server.py 
```
Or in production:
```bash
gunicorn server:app --bind 0.0.0.0:5000 --workers 4
```

# Getting Started with Create React App

This project was bootstrapped with [Create React App](https://github.com/facebook/create-react-app).