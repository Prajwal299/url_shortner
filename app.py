from flask import Flask, request, redirect, jsonify
import mysql.connector
import hashlib
import os
import logging
import time

app = Flask(__name__)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def get_db_connection():
    try:
        return mysql.connector.connect(
            host=os.environ.get('DB_HOST', 'mysql'),
            user=os.environ.get('DB_USER', 'admin'),
            password=os.environ.get('DB_PASS', 'root'),
            database=os.environ.get('DB_NAME', 'urlshortener')
        )
    except mysql.connector.Error as e:
        logger.error(f"Database connection failed: {e}")
        raise

# Initialize database with retries
for attempt in range(5):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS urlshortener")
        cursor.execute("USE urlshortener")
        cursor.execute("CREATE TABLE IF NOT EXISTS urls (original VARCHAR(255) PRIMARY KEY, short VARCHAR(255) UNIQUE)")
        conn.commit()
        cursor.close()
        conn.close()
        logger.info("Database and table initialized successfully")
        break
    except Exception as e:
        logger.error(f"Database initialization failed (attempt {attempt + 1}/5): {e}")
        if attempt < 4:
            time.sleep(5)  # Wait 5 seconds before retrying
        else:
            logger.error("Failed to initialize database after 5 attempts")
            raise

@app.route('/shorten', methods=['POST'])
def shorten():
    try:
        if not request.is_json:
            logger.error("Request is not JSON")
            return jsonify({'error': 'Content-Type must be application/json'}), 400
        url = request.json.get('url')
        if not url:
            logger.error("Missing URL in request")
            return jsonify({'error': 'Missing URL'}), 400
        hash_val = hashlib.md5(url.encode()).hexdigest()[:8]
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO urls (original, short) VALUES (%s, %s) ON DUPLICATE KEY UPDATE short=short", (url, hash_val))
        conn.commit()
        cursor.close()
        conn.close()
        short_url = f'http://3.110.114.163:5000/{hash_val}'
        logger.info(f"Shortened URL: {url} -> {short_url}")
        return jsonify({'short_url': short_url})
    except Exception as e:
        logger.error(f"Error in /shorten: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/<short>')
def redirect_url(short):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT original FROM urls WHERE short = %s", (short,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        if result:
            logger.info(f"Redirecting short code {short} to {result[0]}")
            return redirect(result[0])
        logger.warning(f"Short code not found: {short}")
        return jsonify({'error': 'Not found'}), 404
    except Exception as e:
        logger.error(f"Error in redirect_url: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
