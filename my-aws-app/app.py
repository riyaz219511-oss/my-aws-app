from flask import Flask, render_template, request, jsonify
import boto3
import os
import pymysql
import logging

app = Flask(__name__)

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# RDS Config (set these as Elastic Beanstalk environment variables)
DB_HOST     = os.environ.get("RDS_HOSTNAME", "localhost")
DB_USER     = os.environ.get("RDS_USERNAME", "admin")
DB_PASSWORD = os.environ.get("RDS_PASSWORD", "password")
DB_NAME     = os.environ.get("RDS_DB_NAME", "myappdb")
DB_PORT     = int(os.environ.get("RDS_PORT", 3306))

# S3 Config
S3_BUCKET = os.environ.get("S3_BUCKET", "my-app-bucket")

def get_db_connection():
    """Get a connection to the RDS MySQL database."""
    try:
        conn = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            port=DB_PORT,
            cursorclass=pymysql.cursors.DictCursor
        )
        return conn
    except Exception as e:
        logger.error(f"DB Connection failed: {e}")
        return None


def init_db():
    """Create table if it doesn't exist."""
    conn = get_db_connection()
    if conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    content VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        conn.commit()
        conn.close()


@app.route("/")
def index():
    """Home page - shows messages from RDS."""
    messages = []
    conn = get_db_connection()
    if conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM messages ORDER BY created_at DESC LIMIT 10")
            messages = cursor.fetchall()
        conn.close()
    return render_template("index.html", messages=messages)


@app.route("/add-message", methods=["POST"])
def add_message():
    """Add a message to RDS."""
    content = request.form.get("content", "")
    if content:
        conn = get_db_connection()
        if conn:
            with conn.cursor() as cursor:
                cursor.execute("INSERT INTO messages (content) VALUES (%s)", (content,))
            conn.commit()
            conn.close()
            logger.info(f"Message added: {content}")
    return jsonify({"status": "ok", "message": content})


@app.route("/upload", methods=["POST"])
def upload_file():
    """Upload a file to S3."""
    file = request.files.get("file")
    if file:
        try:
            s3 = boto3.client("s3")
            s3.upload_fileobj(file, S3_BUCKET, f"static/{file.filename}")
            logger.info(f"File uploaded to S3: {file.filename}")
            return jsonify({"status": "ok", "filename": file.filename})
        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            return jsonify({"status": "error", "error": str(e)}), 500
    return jsonify({"status": "error", "error": "No file provided"}), 400


@app.route("/health")
def health():
    """Health check endpoint for EBS."""
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=False)
