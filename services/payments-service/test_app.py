import pytest
import json
from unittest.mock import patch
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
    assert data['service'] == 'payments-service'


def test_metrics_endpoint(client):
    """Test the /metrics endpoint returns Prometheus metrics."""
    response = client.get('/metrics')
    assert response.status_code == 200
    assert response.content_type == 'text/plain; charset=utf-8'
    assert b'http_requests_total' in response.data
    assert b'payments_processed_total' in response.data


@patch('app.random.random')
@patch('app.random.uniform')
def test_process_payment_success(mock_uniform, mock_random, client):
    """Test POST /payments/process successfully processes payment."""
    mock_random.return_value = 0.5  # Ensure no failure
    mock_uniform.return_value = 100.50

    response = client.post('/payments/process')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert 'transaction_id' in data
    assert data['transaction_id'].startswith('txn_')
    assert 'amount' in data
    assert isinstance(data['amount'], (int, float))


@patch('app.random.random')
def test_process_payment_declined(mock_random, client):
    """Test POST /payments/process handles declined payments."""
    mock_random.return_value = 0.005  # Force failure (< 0.01)

    response = client.post('/payments/process')
    assert response.status_code == 402
    data = json.loads(response.data)
    assert 'error' in data
    assert data['error'] == 'Payment declined'


def test_process_payment_amount_range(client):
    """Test that payment amounts are within expected range."""
    # Make multiple requests to check amount range
    for _ in range(10):
        response = client.post('/payments/process')
        if response.status_code == 200:
            data = json.loads(response.data)
            assert 10 <= data['amount'] <= 500


def test_process_payment_transaction_id_format(client):
    """Test that transaction IDs follow expected format."""
    response = client.post('/payments/process')
    if response.status_code == 200:
        data = json.loads(response.data)
        txn_id = data['transaction_id']
        assert txn_id.startswith('txn_')
        # Extract numeric part
        numeric_part = int(txn_id.split('_')[1])
        assert 10000 <= numeric_part <= 99999


def test_payment_status_endpoint(client):
    """Test GET /payments/status/<transaction_id> returns payment status."""
    txn_id = 'txn_12345'
    response = client.get(f'/payments/status/{txn_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['transaction_id'] == txn_id
    assert 'status' in data
    assert data['status'] in ['completed', 'pending', 'processing']


def test_payment_status_multiple_transactions(client):
    """Test payment status for different transaction IDs."""
    transaction_ids = ['txn_11111', 'txn_22222', 'txn_33333']

    for txn_id in transaction_ids:
        response = client.get(f'/payments/status/{txn_id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['transaction_id'] == txn_id
        assert data['status'] in ['completed', 'pending', 'processing']


def test_metrics_updated_after_payment(client):
    """Test that metrics are updated after payment processing."""
    # Process payment
    client.post('/payments/process')

    # Check metrics
    response = client.get('/metrics')
    assert response.status_code == 200
    metrics_data = response.data.decode('utf-8')
    assert 'payments_processed_total' in metrics_data or 'payments_failed_total' in metrics_data


def test_payment_amount_histogram_metric(client):
    """Test that payment amounts are tracked in histogram."""
    # Process several payments
    for _ in range(5):
        client.post('/payments/process')

    # Check metrics
    response = client.get('/metrics')
    assert response.status_code == 200
    assert b'payment_amount_dollars' in response.data
