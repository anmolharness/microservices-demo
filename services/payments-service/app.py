from flask import Flask, jsonify, request
from prometheus_client import Counter, Histogram, generate_latest, REGISTRY
import time
import random

app = Flask(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration', ['method', 'endpoint'])
PAYMENTS_PROCESSED = Counter('payments_processed_total', 'Total payments processed')
PAYMENTS_FAILED = Counter('payments_failed_total', 'Total payments that failed')
PAYMENT_AMOUNT = Histogram('payment_amount_dollars', 'Payment amounts in dollars')

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "service": "payments-service"}), 200

@app.route('/metrics')
def metrics():
    return generate_latest(REGISTRY)

@app.route('/payments/process', methods=['POST'])
def process_payment():
    start_time = time.time()
    try:
        # Simulate payment processing (faster in v1.1.0)
        time.sleep(random.uniform(0.05, 0.2))

        amount = random.uniform(10, 500)
        PAYMENT_AMOUNT.observe(amount)

        # Simulate 2% payment failure rate (improved from 5%)
        if random.random() < 0.02:
            PAYMENTS_FAILED.inc()
            REQUEST_COUNT.labels(method='POST', endpoint='/payments/process', status='402').inc()
            return jsonify({"error": "Payment declined"}), 402

        PAYMENTS_PROCESSED.inc()
        REQUEST_COUNT.labels(method='POST', endpoint='/payments/process', status='200').inc()
        REQUEST_DURATION.labels(method='POST', endpoint='/payments/process').observe(time.time() - start_time)

        return jsonify({
            "status": "success",
            "transaction_id": f"txn_{random.randint(10000, 99999)}",
            "amount": round(amount, 2)
        }), 200
    except Exception as e:
        PAYMENTS_FAILED.inc()
        REQUEST_COUNT.labels(method='POST', endpoint='/payments/process', status='500').inc()
        return jsonify({"error": str(e)}), 500

@app.route('/payments/status/<transaction_id>', methods=['GET'])
def payment_status(transaction_id):
    start_time = time.time()
    try:
        time.sleep(random.uniform(0.01, 0.05))

        REQUEST_COUNT.labels(method='GET', endpoint='/payments/status', status='200').inc()
        REQUEST_DURATION.labels(method='GET', endpoint='/payments/status').observe(time.time() - start_time)

        return jsonify({
            "transaction_id": transaction_id,
            "status": random.choice(["completed", "pending", "processing"])
        }), 200
    except Exception as e:
        REQUEST_COUNT.labels(method='GET', endpoint='/payments/status', status='500').inc()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
