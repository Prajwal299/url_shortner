# from flask import Flask, request, redirect, jsonify
# import mysql.connector
# import hashlib
# import os
# import logging
# import time

# app = Flask(__name__)

# logging.basicConfig(level=logging.DEBUG)
# logger = logging.getLogger(__name__)

# def get_db_connection():
#     try:
#         return mysql.connector.connect(
#             host=os.environ.get('DB_HOST', 'mysql'),
#             user=os.environ.get('DB_USER', 'admin'),
#             password=os.environ.get('DB_PASS', 'root'),
#             database=os.environ.get('DB_NAME', 'urlshortener')
#         )
#     except mysql.connector.Error as e:
#         logger.error(f"Database connection failed: {e}")
#         raise

# # Initialize database with retries
# for attempt in range(5):
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("CREATE DATABASE IF NOT EXISTS urlshortener")
#         cursor.execute("USE urlshortener")
#         cursor.execute("CREATE TABLE IF NOT EXISTS urls (original VARCHAR(255) PRIMARY KEY, short VARCHAR(255) UNIQUE)")
#         conn.commit()
#         cursor.close()
#         conn.close()
#         logger.info("Database and table initialized successfully")
#         break
#     except Exception as e:
#         logger.error(f"Database initialization failed (attempt {attempt + 1}/5): {e}")
#         if attempt < 4:
#             time.sleep(5)  # Wait 5 seconds before retrying
#         else:
#             logger.error("Failed to initialize database after 5 attempts")
#             raise

# @app.route('/shorten', methods=['POST'])
# def shorten():
#     try:
#         if not request.is_json:
#             logger.error("Request is not JSON")
#             return jsonify({'error': 'Content-Type must be application/json'}), 400
#         url = request.json.get('url')
#         if not url:
#             logger.error("Missing URL in request")
#             return jsonify({'error': 'Missing URL'}), 400
#         hash_val = hashlib.md5(url.encode()).hexdigest()[:8]
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("INSERT INTO urls (original, short) VALUES (%s, %s) ON DUPLICATE KEY UPDATE short=short", (url, hash_val))
#         conn.commit()
#         cursor.close()
#         conn.close()
#         short_url = f'http://3.110.114.163:5000/{hash_val}'
#         logger.info(f"Shortened URL: {url} -> {short_url}")
#         return jsonify({'short_url': short_url})
#     except Exception as e:
#         logger.error(f"Error in /shorten: {e}")
#         return jsonify({'error': str(e)}), 500

# @app.route('/<short>')
# def redirect_url(short):
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT original FROM urls WHERE short = %s", (short,))
#         result = cursor.fetchone()
#         cursor.close()
#         conn.close()
#         if result:
#             logger.info(f"Redirecting short code {short} to {result[0]}")
#             return redirect(result[0])
#         logger.warning(f"Short code not found: {short}")
#         return jsonify({'error': 'Not found'}), 404
#     except Exception as e:
#         logger.error(f"Error in redirect_url: {e}")
#         return jsonify({'error': str(e)}), 500

# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=5000)



from flask import Flask, request, redirect, jsonify
import mysql.connector
import hashlib
import os
import logging
import time
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from datetime import datetime

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter(
    'url_shortener_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_DURATION = Histogram(
    'url_shortener_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

ACTIVE_URLS = Gauge(
    'url_shortener_active_urls_total',
    'Total number of active shortened URLs'
)

DATABASE_CONNECTIONS = Gauge(
    'url_shortener_database_connections_active',
    'Number of active database connections'
)

URL_SHORTENING_REQUESTS = Counter(
    'url_shortener_urls_shortened_total',
    'Total number of URLs shortened'
)

URL_REDIRECTS = Counter(
    'url_shortener_redirects_total',
    'Total number of URL redirects',
    ['status']
)

DATABASE_ERRORS = Counter(
    'url_shortener_database_errors_total',
    'Total number of database errors'
)

# Flask request middleware for metrics
@app.before_request
def before_request():
    request.start_time = time.time()

@app.after_request
def after_request(response):
    # Record request metrics
    duration = time.time() - request.start_time
    
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.endpoint or 'unknown',
        status_code=response.status_code
    ).inc()
    
    REQUEST_DURATION.labels(
        method=request.method,
        endpoint=request.endpoint or 'unknown'
    ).observe(duration)
    
    return response

def get_db_connection():
    try:
        DATABASE_CONNECTIONS.inc()
        conn = mysql.connector.connect(
            host=os.environ.get('DB_HOST', 'mysql'),
            user=os.environ.get('DB_USER', 'admin'),
            password=os.environ.get('DB_PASS', 'root'),
            database=os.environ.get('DB_NAME', 'urlshortener'),
            autocommit=True
        )
        return conn
    except mysql.connector.Error as e:
        DATABASE_ERRORS.inc()
        DATABASE_CONNECTIONS.dec()
        logger.error(f"Database connection failed: {e}")
        raise

def close_db_connection(conn):
    if conn:
        conn.close()
        DATABASE_CONNECTIONS.dec()

def update_active_urls_count():
    """Update the gauge with current URL count"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM urls")
        count = cursor.fetchone()[0]
        ACTIVE_URLS.set(count)
        cursor.close()
        close_db_connection(conn)
    except Exception as e:
        logger.error(f"Error updating URL count: {e}")
        DATABASE_ERRORS.inc()

# Initialize database with retries
for attempt in range(5):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS urlshortener")
        cursor.execute("USE urlshortener")
        cursor.execute("CREATE TABLE IF NOT EXISTS urls (original VARCHAR(255) PRIMARY KEY, short VARCHAR(255) UNIQUE)")
        cursor.close()
        close_db_connection(conn)
        logger.info("Database and table initialized successfully")
        
        # Initialize metrics
        update_active_urls_count()
        break
    except Exception as e:
        logger.error(f"Database initialization failed (attempt {attempt + 1}/5): {e}")
        if attempt < 4:
            time.sleep(5)  # Wait 5 seconds before retrying
        else:
            logger.error("Failed to initialize database after 5 attempts")
            raise

@app.route('/')
def home():
    return jsonify({
        'message': 'URL Shortener API',
        'version': '1.0.0',
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/health')
def health_check():
    """Kubernetes health check endpoint"""
    try:
        # Check database connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        close_db_connection(conn)
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        DATABASE_ERRORS.inc()
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/metrics')
def metrics():
    """Prometheus metrics endpoint"""
    try:
        # Update dynamic metrics before serving
        update_active_urls_count()
        return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}
    except Exception as e:
        logger.error(f"Error generating metrics: {e}")
        return jsonify({'error': 'Metrics unavailable'}), 500

@app.route('/shorten', methods=['POST'])
def shorten():
    conn = None
    try:
        if not request.is_json:
            logger.error("Request is not JSON")
            return jsonify({'error': 'Content-Type must be application/json'}), 400
        
        url = request.json.get('url')
        if not url:
            logger.error("Missing URL in request")
            return jsonify({'error': 'Missing URL'}), 400
        
        # Validate URL format (basic validation)
        if not (url.startswith('http://') or url.startswith('https://')):
            url = 'http://' + url
        
        hash_val = hashlib.md5(url.encode()).hexdigest()[:8]
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if URL already exists
        cursor.execute("SELECT short FROM urls WHERE original = %s", (url,))
        existing = cursor.fetchone()
        
        if existing:
            short_url = f'http://3.110.114.163:30080/api/{existing[0]}'
            logger.info(f"URL already exists: {url} -> {short_url}")
        else:
            cursor.execute("INSERT INTO urls (original, short) VALUES (%s, %s)", (url, hash_val))
            short_url = f'http://3.110.114.163:30080/api/{hash_val}'
            logger.info(f"New URL shortened: {url} -> {short_url}")
            URL_SHORTENING_REQUESTS.inc()
        
        cursor.close()
        close_db_connection(conn)
        
        # Update metrics
        update_active_urls_count()
        
        return jsonify({
            'short_url': short_url,
            'original_url': url,
            'short_code': hash_val,
            'timestamp': datetime.now().isoformat()
        })
        
    except mysql.connector.Error as e:
        DATABASE_ERRORS.inc()
        logger.error(f"Database error in /shorten: {e}")
        if conn:
            close_db_connection(conn)
        return jsonify({'error': 'Database error occurred'}), 500
    except Exception as e:
        logger.error(f"Error in /shorten: {e}")
        if conn:
            close_db_connection(conn)
        return jsonify({'error': str(e)}), 500

@app.route('/<short>')
def redirect_url(short):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT original FROM urls WHERE short = %s", (short,))
        result = cursor.fetchone()
        cursor.close()
        close_db_connection(conn)
        
        if result:
            logger.info(f"Redirecting short code {short} to {result[0]}")
            URL_REDIRECTS.labels(status='success').inc()
            return redirect(result[0])
        else:
            logger.warning(f"Short code not found: {short}")
            URL_REDIRECTS.labels(status='not_found').inc()
            return jsonify({
                'error': 'Short URL not found',
                'short_code': short,
                'timestamp': datetime.now().isoformat()
            }), 404
            
    except mysql.connector.Error as e:
        DATABASE_ERRORS.inc()
        logger.error(f"Database error in redirect_url: {e}")
        if conn:
            close_db_connection(conn)
        URL_REDIRECTS.labels(status='error').inc()
        return jsonify({'error': 'Database error occurred'}), 500
    except Exception as e:
        logger.error(f"Error in redirect_url: {e}")
        if conn:
            close_db_connection(conn)
        URL_REDIRECTS.labels(status='error').inc()
        return jsonify({'error': str(e)}), 500

@app.route('/stats')
def stats():
    """Get statistics about the URL shortener"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get total URLs
        cursor.execute("SELECT COUNT(*) FROM urls")
        total_urls = cursor.fetchone()[0]
        
        # Get recent URLs (if you have timestamp column)
        cursor.execute("SELECT original, short FROM urls ORDER BY original DESC LIMIT 10")
        recent_urls = cursor.fetchall()
        
        cursor.close()
        close_db_connection(conn)
        
        return jsonify({
            'total_urls': total_urls,
            'recent_urls': [{'original': url[0], 'short': url[1]} for url in recent_urls],
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        DATABASE_ERRORS.inc()
        logger.error(f"Error in /stats: {e}")
        if conn:
            close_db_connection(conn)
        return jsonify({'error': str(e)}), 500

# Error handlers with metrics
@app.errorhandler(404)
def not_found(error):
    REQUEST_COUNT.labels(method=request.method, endpoint='404', status_code='404').inc()
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    REQUEST_COUNT.labels(method=request.method, endpoint='500', status_code='500').inc()
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)