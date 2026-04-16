import pytest
import json
from unittest.mock import patch, MagicMock
from app import app


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
    assert data['service'] == 'orders-service'


def test_metrics_endpoint(client):
    """Test the /metrics endpoint returns Prometheus metrics."""
    response = client.get('/metrics')
    assert response.status_code == 200
    assert response.content_type == 'text/plain; charset=utf-8'
    assert b'http_requests_total' in response.data


@patch('app.requests.get')
def test_get_orders_success(mock_get, client):
    """Test GET /orders endpoint returns orders successfully."""
    mock_get.return_value = MagicMock(status_code=200)

    response = client.get('/orders')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'orders' in data
    assert len(data['orders']) == 2
    assert data['orders'][0]['item'] == 'laptop'
    assert data['orders'][1]['item'] == 'mouse'


@patch('app.requests.get')
def test_get_orders_with_inventory_service_failure(mock_get, client):
    """Test GET /orders still succeeds even if inventory service fails."""
    mock_get.side_effect = Exception("Connection error")

    response = client.get('/orders')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'orders' in data


@patch('app.random.random')
@patch('app.requests.post')
def test_create_order_success(mock_post, mock_random, client):
    """Test POST /orders/create creates order successfully."""
    mock_random.return_value = 0.5  # Ensure no failure
    mock_post.return_value = MagicMock(status_code=200)

    response = client.post('/orders/create')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['message'] == 'Order created'
    assert 'order_id' in data
    assert 1000 <= data['order_id'] <= 9999


@patch('app.random.random')
def test_create_order_failure(mock_random, client):
    """Test POST /orders/create handles random failures."""
    mock_random.return_value = 0.01  # Force failure (< 0.02)

    response = client.post('/orders/create')
    assert response.status_code == 500
    data = json.loads(response.data)
    assert 'error' in data
    assert data['error'] == 'Order creation failed'


@patch('app.random.random')
@patch('app.requests.post')
def test_create_order_external_service_failures(mock_post, mock_random, client):
    """Test POST /orders/create handles external service failures gracefully."""
    mock_random.return_value = 0.5  # Ensure no internal failure
    mock_post.side_effect = Exception("Service unavailable")

    # Should still succeed even if external services fail
    response = client.post('/orders/create')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['message'] == 'Order created'


def test_metrics_updated_after_requests(client):
    """Test that metrics are updated after making requests."""
    # Make some requests
    client.get('/health')
    client.get('/orders')

    # Check metrics
    response = client.get('/metrics')
    assert response.status_code == 200
    assert b'http_requests_total' in response.data
