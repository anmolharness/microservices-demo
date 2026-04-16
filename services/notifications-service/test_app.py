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
    assert data['service'] == 'notifications-service'


def test_metrics_endpoint(client):
    """Test the /metrics endpoint returns Prometheus metrics."""
    response = client.get('/metrics')
    assert response.status_code == 200
    assert response.content_type == 'text/plain; charset=utf-8'
    assert b'http_requests_total' in response.data
    assert b'notifications_sent_total' in response.data


@patch('app.random.random')
@patch('app.random.choice')
def test_send_notification_success(mock_choice, mock_random, client):
    """Test POST /notifications/send successfully sends notification."""
    mock_random.return_value = 0.5  # Ensure no failure
    mock_choice.return_value = 'email'

    response = client.post('/notifications/send')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'sent'
    assert data['type'] == 'email'
    assert 'notification_id' in data
    assert data['notification_id'].startswith('notif_')


@patch('app.random.random')
def test_send_notification_failure(mock_random, client):
    """Test POST /notifications/send handles delivery failures."""
    mock_random.return_value = 0.005  # Force failure (< 0.01)

    response = client.post('/notifications/send')
    assert response.status_code == 500
    data = json.loads(response.data)
    assert 'error' in data
    assert data['error'] == 'Notification delivery failed'


def test_send_notification_types(client):
    """Test that notification types are one of the expected values."""
    # Send multiple notifications
    for _ in range(10):
        response = client.post('/notifications/send')
        if response.status_code == 200:
            data = json.loads(response.data)
            assert data['type'] in ['email', 'sms', 'push']


def test_notification_id_format(client):
    """Test that notification IDs follow expected format."""
    response = client.post('/notifications/send')
    if response.status_code == 200:
        data = json.loads(response.data)
        notif_id = data['notification_id']
        assert notif_id.startswith('notif_')
        # Extract numeric part
        numeric_part = int(notif_id.split('_')[1])
        assert 1000 <= numeric_part <= 9999


@patch('app.random.choice')
def test_send_email_notification(mock_choice, client):
    """Test sending email notification specifically."""
    mock_choice.return_value = 'email'

    response = client.post('/notifications/send')
    if response.status_code == 200:
        data = json.loads(response.data)
        assert data['type'] == 'email'


@patch('app.random.choice')
def test_send_sms_notification(mock_choice, client):
    """Test sending SMS notification specifically."""
    mock_choice.return_value = 'sms'

    response = client.post('/notifications/send')
    if response.status_code == 200:
        data = json.loads(response.data)
        assert data['type'] == 'sms'


@patch('app.random.choice')
def test_send_push_notification(mock_choice, client):
    """Test sending push notification specifically."""
    mock_choice.return_value = 'push'

    response = client.post('/notifications/send')
    if response.status_code == 200:
        data = json.loads(response.data)
        assert data['type'] == 'push'


def test_metrics_by_notification_type(client):
    """Test that metrics are tracked by notification type."""
    # Send notifications
    for _ in range(5):
        client.post('/notifications/send')

    # Check metrics
    response = client.get('/metrics')
    assert response.status_code == 200
    metrics_data = response.data.decode('utf-8')
    assert 'notifications_sent_total{type=' in metrics_data or 'notifications_failed_total{type=' in metrics_data


def test_multiple_notifications_success(client):
    """Test sending multiple notifications."""
    notification_ids = []

    for _ in range(3):
        response = client.post('/notifications/send')
        if response.status_code == 200:
            data = json.loads(response.data)
            notification_ids.append(data['notification_id'])

    # Ensure unique notification IDs
    assert len(notification_ids) == len(set(notification_ids))
