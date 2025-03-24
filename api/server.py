"""---------------------------------Imports---------------------------------"""
# Flask and task scheduling
from flask import Flask, Blueprint, request, jsonify, send_from_directory, render_template

from flask_cors import CORS
from flask_apscheduler import APScheduler

# External API and environment variables
import requests
import os
import openai

# PostgreSQL integration
import psycopg2

# Config and safe file handling
import json
from filelock import FileLock

"""---------------------------------Global Variables---------------------------------"""
# Environment and configuration paths
NEWS_API_KEY = os.environ.get("NEWSAPI_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_KEY")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
LOCK_PATH = CONFIG_PATH + ".lock"
LOCK_TIMEOUT = 5  # seconds to wait on lock

# PostgreSQL DB settings
DB_NAME = "news" #modify this to your postgres database name
DB_USER = "postgres" #modify this to your postgres username
DB_PASSWORD = "1111" #modify this to your postgres password
DB_HOST = "localhost" #modify this to your postgres host
DB_PORT = "5432" #modify this to your postgres port

# APScheduler instance
scheduler = APScheduler()

# Factory pattern for creating Flask app
def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.register_blueprint(bp)
    return app


"""---------------------------------API Functions---------------------------------"""
"""-openai functions-"""
# Use OpenAI to summarize a given news article

def summarize_text(text, topic = "technology"):
    """
    Uses OpenAI GPT to generate a short summary of a given text. Force the summary to be related to a specific topic.
    """
    if not OPENAI_API_KEY:
        print("OpenAI API key is missing! Set it as an environment variable.")
        return None

    try:
        client = openai.OpenAI(api_key = OPENAI_API_KEY)
        prompt = "You will be provided with a news article. Your goal is to extract a summary of 3 sentences. The summary should be related to {topic}."
        response = client.chat.completions.create(
            model="gpt-4o-mini-2024-07-18", # GPT-4o-mini model with cheapest price
            messages=[
                {"role": "system", 
                 "content": prompt,
                 },
                {"role": "user", 
                 "content": [{"type": "text", "text": text}]
                 }
            ],
            temperature=0.5 # Higher temperature means more randomness
        )
        return response.choices[0].message.content
    except Exception as e:
        print("Error in summarize_text:", e)
        return None
    
# Use OpenAI to generate a trend analysis summary from multiple article summaries
def analyze_trend(summary_list, topic = "technology"):
    """
    Uses OpenAI GPT to generate a trend analysis of a given list of summary. Force the summary to be related to a specific topic.
    """
    if not OPENAI_API_KEY:
        print("OpenAI API key is missing! Set it as an environment variable.")
        return None

    try:
        client = openai.OpenAI(api_key = OPENAI_API_KEY)
        prompt = "You are a trend analyst. Your goal is to summary the trend of {topic} based on the date and content. The summary is about the trend of {topic} and in clear bullet points."
        response = client.chat.completions.create(
            model="gpt-4o-mini-2024-07-18", # GPT-4o-mini model with cheapest price
            messages=[
                {"role": "system", 
                 "content": prompt
                 },
                {"role": "user", 
                 "content": summary_list
                 }
            ],
            temperature=0.5 # Higher temperature means more randomness
        )
        return response.choices[0].message.content
    except Exception as e:
        print("Error in analyze_trend:", e)
        return None

"""-news functions-"""
# Fetch news articles from the News API
def fetch_news(topic, size = 10, sortBy = 'relevancy', language = 'en'):
    """
    Fetch news articles from the News API.
    """
    url = f"https://newsapi.org/v2/everything?q={topic}&pageSize={size}&sortBy={sortBy}&language={language}&apiKey={NEWS_API_KEY}"
    response = requests.get(url)
    if response.status_code == 200: # Success
        articles = response.json().get("articles", [])
        return [
            {
                "title": article["title"],
                "source": article["source"]["name"],
                "published_date": article["publishedAt"],
                "content": article["content"],
                "url": article["url"], #URL needs to be unique to avoid duplicates in the database
                "summary": summarize_text(article['content'], topic), # Generate summary and store it in the database
                "topic": topic.lower() #all the topics are stored in lowercase to avoid case sensitivity issues in PostgreSQL
            }
            for article in articles if article["content"]  # Filter out empty articles
        ]
    else:
        print(f"Error fetching news: {response.status_code}")
        return []

"""-database functions-"""
# Connect to the PostgreSQL database
def connect_db():
    """
    Establish a connection to the PostgreSQL database.
    """
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        ) # Connect to the database with the given credentials
        return conn
    except Exception as e:
        print("Database connection failed:", e)
        return None

# Create the news_articles table if it doesn't exist
def create_tables():
    """
    Create the news_articles table if it doesn't exist.
    """
    conn = connect_db()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS news_articles (
                id serial PRIMARY KEY,
                title text,
                source text,
                published_date timestamp,
                summary text,
                topic text,
                url text NOT NULL UNIQUE,
                fetched_at timestamp NOT NULL DEFAULT NOW()
            );
        """) # Create a table with the given columns if it doesn't exist. URL is set to be unique to avoid duplicates.
        conn.commit()
        cursor.close()
        conn.close()
        print("Database tables created successfully.")

# Store the given list of articles in the database
def store_news(articles):
    """
    Store the given list of articles in the database.
    """
    conn = connect_db()
    if conn:
        cursor = conn.cursor()
        print("Database tables connected successfully")
        for article in articles:
            try:
                SQL = "INSERT INTO news_articles (title, source, published_date, summary, topic, url) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (url) DO NOTHING;"
                data = (article["title"], article["source"], article["published_date"], article["summary"], article["topic"], article["url"])
                cursor.execute(SQL, data) #The SQL representation of many data types is often different from their Python string representation. In order to make it easier to build correctly formatted SQL strings, psycopg2 introduced the sql module that provides support for SQL value placeholders, SQL identifiers, SQL literals, and SQL functions.
            except Exception as e:
                print(f"Error inserting article: {e}")
        conn.commit()
        cursor.close()
        conn.close()

def load_summary(topic, size = 5):
    """
    Load the latest news articles for the given topic from the database.
    """
    conn = connect_db()
    if conn:
        cursor = conn.cursor()
        print("Database tables connected successfully")
        cursor.execute("""
        SELECT id, title, summary, published_date, url FROM news_articles
        WHERE topic LIKE %s
        ORDER BY published_date DESC
        LIMIT %s;
    """, (f"%{topic.lower()}%", size)) #The % is a wildcard character that represents zero or more characters. The LIKE operator is used in a WHERE clause to search for a specified pattern in a column.
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results

def formatted_report(topic):
    """
    Load and format the latest news articles for the given topic.
    """
    articles = load_summary(topic)
    if len(articles) < 5: # If there are less than 5 articles, fetch new ones
        run_topic_pipeline(topic)
        articles = load_summary(topic)
    formatted = [
        {
            "id": a[0],
            "title": a[1],
            "summary": a[2],
            "published_date": a[3].strftime("%Y-%m-%d"),
            "url": a[4]
        }
        for a in articles
    ] # Format the articles as a list of dictionaries to be later converted to JSON
    return formatted

def format_articles_for_prompt(articles):
    return "\n\n".join(
        f"[{a['published_date']}] {a['title']}\nSummary: {a['summary']}"
        for a in articles
    ) #OpenAI GPT-4o-mini model requires the input to be in a specific format. The format_articles_for_prompt function takes a list of articles and formats them as a single string with each article separated by a newline character.

"""-scheduler functions-"""
# Run the news pipeline for the given topic and store the articles at scheduled intervals
def run_topic_pipeline(topic):
    articles = fetch_news(topic)
    store_news(articles)
    print("Pipeline ran successfully for", topic)
    
# Load current config
def load_config():
    with FileLock(LOCK_PATH, timeout=LOCK_TIMEOUT): #FileLock is used to prevent multiple processes from accessing the same file at the same time. This is important when multiple processes are trying to read or write to the same file.
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)

#save updated config
def save_config(data):
    with FileLock(LOCK_PATH, timeout=LOCK_TIMEOUT): #FileLock is used to prevent multiple processes from accessing the same file at the same time. This is important when multiple processes are trying to read or write to the same file.
        with open(CONFIG_PATH, "w") as f:
            json.dump(data, f, indent=2)


@scheduler.task('interval', id='my_job', seconds=3600) # Run the job every hour
def my_job():
    try:
        config = load_config()
    except Exception as e:
        print(f"Error loading config: {e}")
    for i, job in enumerate(config["jobs"]):
        topic = job["topic"]
        try:
            run_topic_pipeline(topic)
        except Exception as e:
            print(f"Error running pipeline for {topic}: {e}")

"""---------------------------------API Routes---------------------------------"""
bp = Blueprint('/', __name__, url_prefix='/') # Create a Blueprint for the API routes

@bp.route("/")
def serve_index():
    return render_template("index.html")

# Optional: serve static files like JS/CSS
@bp.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

@bp.route("/search", methods=["GET"])
def get_articles():
    topic = request.args.get("topic", "").lower()
    if not topic:
        return jsonify({"error": "Missing 'topic' query parameter"}), 400
    formatted = formatted_report(topic)
    return jsonify({"topic": topic, "count": len(formatted), "articles": formatted})

@bp.route("/trend", methods=["GET"])
def get_trend():
    topic = request.args.get("topic", "").lower()
    if not topic:
        return jsonify({"error": "Missing 'topic' query parameter"}), 400
    formatted = formatted_report(topic)
    prompt = format_articles_for_prompt(formatted)
    trend = analyze_trend(prompt,topic)
    return jsonify({"topic": topic, "trend_analysis": trend})

@bp.route("/scheduler", methods=["GET"])
def get_schedule():
    status = "running" if scheduler.running else "not running"
    return jsonify({"scheduler_status": status})

# GET all scheduled topics
@bp.route("/topics", methods=["GET"])
def get_topics():
    config = load_config()
    return jsonify(config["jobs"])

# POST new topic
@bp.route("/topics", methods=["POST"])
def add_topic():
    data = request.get_json()
    topic = data.get("class")

    if not topic:
        return jsonify({"error": "Missing topic or schedule"}), 400

    config = load_config()

    # Avoid duplicates
    if any(job["topic"] == topic for job in config["jobs"]):
        return jsonify({"error": "Topic already exists"}), 409

    config["jobs"].append({"topic": topic})
    save_config(config)
    return jsonify({"message": f"Added topic '{topic}'"}), 201

# DELETE topic
@bp.route("/topics-delete", methods=["DELETE"])
def delete_topic():
    data = request.get_json()
    topic = data.get("class")
    if not topic:
        return jsonify({"error": "Missing topic or schedule"}), 400
    config = load_config()
    original_count = len(config["jobs"])
    config["jobs"] = [job for job in config["jobs"] if job["topic"] != topic] # Remove the topic from the list

    if len(config["jobs"]) == original_count: # No topic was deleted
        return jsonify({"error": "Topic not found"}), 404

    save_config(config)
    return jsonify({"message": f"Deleted topic '{topic}'"}), 200

if __name__ == '__main__':
    create_tables()
    app = create_app()
    scheduler.init_app(app)
    scheduler.start()
    CORS(app)
    app.run(debug=False, host="0.0.0.0", port=5000)