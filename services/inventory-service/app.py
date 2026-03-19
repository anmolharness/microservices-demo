from flask import Flask, jsonify
from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY
import time
import random

app = Flask(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration', ['method', 'endpoint'])
INVENTORY_ITEMS = Gauge('inventory_items_count', 'Current inventory item count', ['item'])
INVENTORY_CHECKS = Counter('inventory_checks_total', 'Total inventory checks')
LOW_STOCK_ALERTS = Gauge('inventory_low_stock_alert', 'Low stock alert (1 if below threshold)', ['item'])
INVENTORY_CACHE_HITS = Counter('inventory_cache_hits_total', 'Total cache hits (v1.2.0 feature)')

# Initialize some inventory
inventory = {
    "laptop": 50,
    "mouse": 200,
    "keyboard": 150,
    "monitor": 75
}

LOW_STOCK_THRESHOLD = 100

for item, count in inventory.items():
    INVENTORY_ITEMS.labels(item=item).set(count)
    # Set low stock alert if below threshold
    LOW_STOCK_ALERTS.labels(item=item).set(1 if count < LOW_STOCK_THRESHOLD else 0)

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "service": "inventory-service"}), 200

@app.route('/metrics')
def metrics():
    return generate_latest(REGISTRY), 200, {'Content-Type': 'text/plain; charset=utf-8'}

@app.route('/inventory', methods=['GET'])
def get_inventory():
    start_time = time.time()
    try:
        time.sleep(random.uniform(0.01, 0.05))

        INVENTORY_CHECKS.inc()
        # Simulate cache hit 80% of the time in v1.2.0
        if random.random() < 0.8:
            INVENTORY_CACHE_HITS.inc()

        REQUEST_COUNT.labels(method='GET', endpoint='/inventory', status='200').inc()
        REQUEST_DURATION.labels(method='GET', endpoint='/inventory').observe(time.time() - start_time)

        return jsonify({"inventory": inventory}), 200
    except Exception as e:
        REQUEST_COUNT.labels(method='GET', endpoint='/inventory', status='500').inc()
        return jsonify({"error": str(e)}), 500

@app.route('/inventory/<item>', methods=['GET'])
def get_item(item):
    start_time = time.time()
    try:
        time.sleep(random.uniform(0.01, 0.05))

        if item in inventory:
            REQUEST_COUNT.labels(method='GET', endpoint=f'/inventory/{item}', status='200').inc()
            REQUEST_DURATION.labels(method='GET', endpoint='/inventory/item').observe(time.time() - start_time)
            return jsonify({"item": item, "quantity": inventory[item]}), 200
        else:
            REQUEST_COUNT.labels(method='GET', endpoint=f'/inventory/{item}', status='404').inc()
            return jsonify({"error": "Item not found"}), 404
    except Exception as e:
        REQUEST_COUNT.labels(method='GET', endpoint='/inventory/item', status='500').inc()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
