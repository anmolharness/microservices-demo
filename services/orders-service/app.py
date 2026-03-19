from flask import Flask, jsonify
from prometheus_client import Counter, Histogram, generate_latest, REGISTRY
import time
import random
import requests

app = Flask(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration', ['method', 'endpoint'])
REQUEST_LATENCY = Histogram('order_request_latency_seconds', 'Order request latency', buckets=[0.1, 0.25, 0.5, 1.0, 2.5])
ORDERS_CREATED = Counter('orders_created_total', 'Total orders created')
ORDERS_FAILED = Counter('orders_failed_total', 'Total orders that failed')

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "service": "orders-service"}), 200

@app.route('/metrics')
def metrics():
    return generate_latest(REGISTRY), 200, {'Content-Type': 'text/plain; charset=utf-8'}

@app.route('/orders', methods=['GET'])
def get_orders():
    start_time = time.time()
    try:
        # Simulate some work
        time.sleep(random.uniform(0.01, 0.1))

        # Call inventory service
        try:
            requests.get('http://inventory-service:8080/inventory', timeout=2)
        except:
            pass

        REQUEST_COUNT.labels(method='GET', endpoint='/orders', status='200').inc()
        REQUEST_DURATION.labels(method='GET', endpoint='/orders').observe(time.time() - start_time)

        return jsonify({
            "orders": [
                {"id": "1", "item": "laptop", "quantity": 2},
                {"id": "2", "item": "mouse", "quantity": 5}
            ]
        }), 200
    except Exception as e:
        REQUEST_COUNT.labels(method='GET', endpoint='/orders', status='500').inc()
        return jsonify({"error": str(e)}), 500

@app.route('/orders/create', methods=['POST'])
def create_order():
    start_time = time.time()
    try:
        # Simulate work and random failures (faster in v1.2.0)
        time.sleep(random.uniform(0.03, 0.15))

        if random.random() < 0.02:  # 2% failure rate (improved from 5%)
            ORDERS_FAILED.inc()
            REQUEST_COUNT.labels(method='POST', endpoint='/orders/create', status='500').inc()
            REQUEST_LATENCY.observe(time.time() - start_time)
            return jsonify({"error": "Order creation failed"}), 500

        # Call payments service
        try:
            requests.post('http://payments-service:8080/payments/process', timeout=2)
        except:
            pass

        # Call notifications service
        try:
            requests.post('http://notifications-service:8080/notifications/send', timeout=2)
        except:
            pass

        ORDERS_CREATED.inc()
        REQUEST_COUNT.labels(method='POST', endpoint='/orders/create', status='200').inc()
        REQUEST_DURATION.labels(method='POST', endpoint='/orders/create').observe(time.time() - start_time)
        REQUEST_LATENCY.observe(time.time() - start_time)

        return jsonify({"message": "Order created", "order_id": random.randint(1000, 9999)}), 200
    except Exception as e:
        ORDERS_FAILED.inc()
        REQUEST_COUNT.labels(method='POST', endpoint='/orders/create', status='500').inc()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
