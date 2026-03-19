from flask import Flask, jsonify, request
from prometheus_client import Counter, Histogram, generate_latest, REGISTRY
import time
import random

app = Flask(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration', ['method', 'endpoint'])
NOTIFICATIONS_SENT = Counter('notifications_sent_total', 'Total notifications sent', ['type'])
NOTIFICATIONS_FAILED = Counter('notifications_failed_total', 'Total notifications that failed', ['type'])

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "service": "notifications-service"}), 200

@app.route('/metrics')
def metrics():
    return generate_latest(REGISTRY)

@app.route('/notifications/send', methods=['POST'])
def send_notification():
    start_time = time.time()
    try:
        # Simulate notification sending
        time.sleep(random.uniform(0.02, 0.1))

        notification_type = random.choice(['email', 'sms', 'push'])

        # Simulate 1% failure rate (improved from 3%)
        if random.random() < 0.01:
            NOTIFICATIONS_FAILED.labels(type=notification_type).inc()
            REQUEST_COUNT.labels(method='POST', endpoint='/notifications/send', status='500').inc()
            return jsonify({"error": "Notification delivery failed"}), 500

        NOTIFICATIONS_SENT.labels(type=notification_type).inc()
        REQUEST_COUNT.labels(method='POST', endpoint='/notifications/send', status='200').inc()
        REQUEST_DURATION.labels(method='POST', endpoint='/notifications/send').observe(time.time() - start_time)

        return jsonify({
            "status": "sent",
            "type": notification_type,
            "notification_id": f"notif_{random.randint(1000, 9999)}"
        }), 200
    except Exception as e:
        NOTIFICATIONS_FAILED.labels(type='unknown').inc()
        REQUEST_COUNT.labels(method='POST', endpoint='/notifications/send', status='500').inc()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
