# Microservices Testing Guide

This directory contains four microservices with comprehensive unit tests.

## Services

1. **orders-service** - Handles order creation and retrieval
2. **inventory-service** - Manages product inventory
3. **payments-service** - Processes payments
4. **notifications-service** - Sends notifications

## Running Tests

### Install Dependencies

For each service, install the required packages:

```bash
cd services/<service-name>
pip install -r requirements.txt
```

### Run Tests

Run tests for a specific service:

```bash
cd services/orders-service
pytest

# With coverage
pytest --cov=app --cov-report=html
```

Run all tests from the services directory:

```bash
# From the services directory
for service in orders-service inventory-service payments-service notifications-service; do
    echo "Testing $service..."
    cd $service && pytest && cd ..
done
```

### Test Coverage

Each service includes comprehensive unit tests covering:

- Health check endpoints
- Prometheus metrics endpoints
- All business logic endpoints
- Success and failure scenarios
- External service integration (with mocking)
- Metric tracking and updates

## Test Statistics

- **orders-service**: 8 tests covering all endpoints
- **inventory-service**: 11 tests covering inventory management
- **payments-service**: 9 tests covering payment processing
- **notifications-service**: 10 tests covering notification delivery

Total: **38 unit tests** across all services
