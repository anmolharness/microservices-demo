import pytest
import json
from app import app, inventory


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_health_endpoint(client):
    """Test the /health endpoint returns healthy status."""
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'
    assert data['service'] == 'inventory-service'


def test_metrics_endpoint(client):
    """Test the /metrics endpoint returns Prometheus metrics."""
    response = client.get('/metrics')
    assert response.status_code == 200
    assert response.content_type == 'text/plain; charset=utf-8'
    assert b'http_requests_total' in response.data
    assert b'inventory_items_count' in response.data


def test_get_inventory_success(client):
    """Test GET /inventory returns all inventory items."""
    response = client.get('/inventory')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'inventory' in data
    assert 'laptop' in data['inventory']
    assert 'mouse' in data['inventory']
    assert 'keyboard' in data['inventory']
    assert 'monitor' in data['inventory']


def test_get_inventory_values(client):
    """Test GET /inventory returns correct inventory counts."""
    response = client.get('/inventory')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['inventory']['laptop'] == 50
    assert data['inventory']['mouse'] == 200
    assert data['inventory']['keyboard'] == 150
    assert data['inventory']['monitor'] == 75


def test_get_item_existing(client):
    """Test GET /inventory/<item> returns specific item successfully."""
    response = client.get('/inventory/laptop')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['item'] == 'laptop'
    assert data['quantity'] == 50


def test_get_item_all_items(client):
    """Test GET /inventory/<item> for all items in inventory."""
    for item_name, expected_quantity in inventory.items():
        response = client.get(f'/inventory/{item_name}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['item'] == item_name
        assert data['quantity'] == expected_quantity


def test_get_item_not_found(client):
    """Test GET /inventory/<item> returns 404 for non-existent items."""
    response = client.get('/inventory/nonexistent')
    assert response.status_code == 404
    data = json.loads(response.data)
    assert 'error' in data
    assert data['error'] == 'Item not found'


def test_inventory_checks_metric(client):
    """Test that inventory_checks_total metric increments."""
    # Get initial metrics
    response = client.get('/metrics')
    initial_metrics = response.data.decode('utf-8')

    # Make inventory requests
    client.get('/inventory')
    client.get('/inventory')

    # Check metrics updated
    response = client.get('/metrics')
    assert response.status_code == 200
    assert b'inventory_checks_total' in response.data


def test_cache_hits_metric(client):
    """Test that cache hits are tracked in metrics."""
    # Make multiple requests to trigger cache
    for _ in range(5):
        client.get('/inventory')

    # Check metrics
    response = client.get('/metrics')
    assert response.status_code == 200
    assert b'inventory_cache_hits_total' in response.data


def test_low_stock_alerts_in_metrics(client):
    """Test that low stock alerts are present in metrics."""
    response = client.get('/metrics')
    assert response.status_code == 200
    assert b'inventory_low_stock_alert' in response.data

    # laptop (50) and monitor (75) should have low stock alerts
    metrics_text = response.data.decode('utf-8')
    assert 'inventory_low_stock_alert{item="laptop"}' in metrics_text
    assert 'inventory_low_stock_alert{item="monitor"}' in metrics_text
