# Microservices Demo with Prometheus Metrics

A simple microservices application designed for demonstrating Kubernetes deployments, Helm charts, and Prometheus monitoring integration with Harness CD.

## Architecture

This demo consists of 4 microservices:

1. **orders-service**: Handles order management, calls inventory, payments, and notifications
2. **inventory-service**: Manages inventory and stock levels
3. **payments-service**: Processes payments
4. **notifications-service**: Sends notifications (email, SMS, push)

All services expose Prometheus metrics at `/metrics` endpoint.

## Metrics Exposed

Each service exports the following metrics:

### Common Metrics (All Services)
- `http_requests_total` - Total HTTP requests by method, endpoint, and status
- `http_request_duration_seconds` - HTTP request latency histogram

### Service-Specific Metrics

**orders-service:**
- `orders_created_total` - Total orders created
- `orders_failed_total` - Total orders that failed

**inventory-service:**
- `inventory_items_count` - Current inventory count by item (gauge)
- `inventory_checks_total` - Total inventory checks

**payments-service:**
- `payments_processed_total` - Total payments processed
- `payments_failed_total` - Total failed payments
- `payment_amount_dollars` - Payment amounts histogram

**notifications-service:**
- `notifications_sent_total` - Total notifications sent by type
- `notifications_failed_total` - Total failed notifications by type

## Building Docker Images

### Build all services:

```bash
# Build orders-service
docker build -t orders-service:latest ./services/orders-service

# Build inventory-service
docker build -t inventory-service:latest ./services/inventory-service

# Build payments-service
docker build -t payments-service:latest ./services/payments-service

# Build notifications-service
docker build -t notifications-service:latest ./services/notifications-service
```

### Tag and push to your registry (example with Docker Hub):

```bash
# Tag images
docker tag orders-service:latest your-registry/orders-service:v1.0.0
docker tag inventory-service:latest your-registry/inventory-service:v1.0.0
docker tag payments-service:latest your-registry/payments-service:v1.0.0
docker tag notifications-service:latest your-registry/notifications-service:v1.0.0

# Push images
docker push your-registry/orders-service:v1.0.0
docker push your-registry/inventory-service:v1.0.0
docker push your-registry/payments-service:v1.0.0
docker push your-registry/notifications-service:v1.0.0
```

## Deploying with Helm

### Install the chart:

```bash
# Using local images (for local testing)
helm install microservices-demo ./helm-chart --create-namespace --namespace app

# Using images from your registry
helm install microservices-demo ./helm-chart \
  --set global.imageRegistry=your-registry.io/ \
  --set global.imageTag=v1.0.0 \
  --create-namespace \
  --namespace app
```

### Upgrade deployment:

```bash
helm upgrade microservices-demo ./helm-chart \
  --set global.imageTag=v1.0.1 \
  --namespace app
```

### Uninstall:

```bash
helm uninstall microservices-demo --namespace app
```

## Accessing Metrics

### Port-forward to access metrics locally:

```bash
# Orders service
kubectl port-forward -n app svc/orders-service 8080:8080
curl http://localhost:8080/metrics

# Inventory service
kubectl port-forward -n app svc/inventory-service 8081:8080
curl http://localhost:8081/metrics

# Payments service
kubectl port-forward -n app svc/payments-service 8082:8080
curl http://localhost:8082/metrics

# Notifications service
kubectl port-forward -n app svc/notifications-service 8083:8080
curl http://localhost:8083/metrics
```

### Health checks:

```bash
curl http://localhost:8080/health
```

## Prometheus Integration

All services are annotated for Prometheus auto-discovery:

```yaml
annotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "8080"
  prometheus.io/path: "/metrics"
```

### Sample Prometheus scrape config:

```yaml
scrape_configs:
  - job_name: 'kubernetes-services'
    kubernetes_sd_configs:
      - role: service
    relabel_configs:
      - source_labels: [__meta_kubernetes_service_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      - source_labels: [__meta_kubernetes_service_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)
      - source_labels: [__address__, __meta_kubernetes_service_annotation_prometheus_io_port]
        action: replace
        target_label: __address__
        regex: ([^:]+)(?::\d+)?;(\d+)
        replacement: $1:$2
```

## Useful PromQL Queries for Harness Verification

### Check all services are healthy (pod count):

```promql
# Count running pods for each service
count(up{namespace="app"} == 1) by (job)

# Success rate for orders service
rate(http_requests_total{app="orders-service",status="200"}[5m])
/
rate(http_requests_total{app="orders-service"}[5m])

# Error rate across all services
sum(rate(http_requests_total{namespace="app",status=~"5.."}[5m]))

# Request latency P95
histogram_quantile(0.95,
  rate(http_request_duration_seconds_bucket{namespace="app"}[5m])
)

# Total orders created
rate(orders_created_total[5m])

# Payment failure rate
rate(payments_failed_total[5m]) / rate(payments_processed_total[5m])
```

## Load Generator

The Helm chart includes an optional load generator that continuously calls all services to generate metrics:

```bash
# Enable/disable in values.yaml
loadGenerator:
  enabled: true
```

## Harness CD Integration

This chart is designed for use with Harness Continuous Delivery with:
- Canary deployments
- Prometheus-based continuous verification
- Multi-service health validation

### Sample Harness verification queries:

1. **Service Availability**: `up{namespace="app"}`
2. **Error Rate**: `sum(rate(http_requests_total{namespace="app",status=~"5.."}[5m]))`
3. **Success Rate**: `sum(rate(http_requests_total{namespace="app",status="200"}[5m]))`
4. **Response Time**: `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{namespace="app"}[5m]))`

## Development

### Running locally:

```bash
# Orders service
cd services/orders-service
pip install -r requirements.txt
python app.py

# Access at http://localhost:8080
```

### Testing endpoints:

```bash
# Health check
curl http://localhost:8080/health

# Get orders
curl http://localhost:8080/orders

# Create order
curl -X POST http://localhost:8080/orders/create

# Metrics
curl http://localhost:8080/metrics
```

## Project Structure

```
.
├── README.md
├── services/
│   ├── orders-service/
│   │   ├── app.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   ├── inventory-service/
│   │   ├── app.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   ├── payments-service/
│   │   ├── app.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   └── notifications-service/
│       ├── app.py
│       ├── requirements.txt
│       └── Dockerfile
└── helm-chart/
    ├── Chart.yaml
    ├── values.yaml
    └── templates/
        ├── orders-service.yaml
        ├── inventory-service.yaml
        ├── payments-service.yaml
        ├── notifications-service.yaml
        └── load-generator.yaml
```

## License

Apache License 2.0
