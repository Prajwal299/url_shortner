from flask import Flask, request, redirect, jsonify
import mysql.connector
import hashlib
import os

app = Flask(__name__)

# Connect to MySQL (env vars from Docker/K8s)
def get_db_connection():
    return mysql.connector.connect(
        host=os.environ.get('DB_HOST', 'mysql'),
        user=os.environ.get('DB_USER', 'admin'),
        password=os.environ.get('DB_PASS', 'root'),
        database=os.environ.get('DB_NAME', 'urlshortener')
    )

@app.route('/shorten', methods=['POST'])
def shorten():
    url = request.json.get('url')
    if not url:
        return jsonify({'error': 'Missing URL'}), 400
    hash_val = hashlib.md5(url.encode()).hexdigest()[:8]  # Simple hash for short code
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO urls (original, short) VALUES (%s, %s) ON DUPLICATE KEY UPDATE short=short", (url, hash_val))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'short_url': f'http://localhost:5000/{hash_val}'})

@app.route('/<short>')
def redirect_url(short):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT original FROM urls WHERE short = %s", (short,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    if result:
        return redirect(result[0])
    return jsonify({'error': 'Not found'}), 404

if __name__ == '__main__':
    # Create DB/table if not exists
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("CREATE DATABASE IF NOT EXISTS urlshortener")
    cursor.execute("USE urlshortener")
    cursor.execute("CREATE TABLE IF NOT EXISTS urls (original VARCHAR(255) PRIMARY KEY, short VARCHAR(255) UNIQUE)")
    conn.commit()
    cursor.close()
    conn.close()
    app.run(host='0.0.0.0', port=5000)