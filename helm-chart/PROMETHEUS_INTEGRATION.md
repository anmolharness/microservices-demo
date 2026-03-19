# Prometheus Integration Guide

## Overview

The Online Boutique helm chart now supports exporting metrics to Prometheus via the OpenTelemetry Collector.

## Configuration

### Enable Prometheus Exporter

In your `values.yaml` or Harness override values:

```yaml
opentelemetryCollector:
  create: true
  name: opentelemetrycollector
  projectId: "not-needed-for-prometheus"  # Only required for Google Cloud

  prometheus:
    enabled: true      # Enable Prometheus exporter
    port: 8889        # Prometheus metrics port
    path: "/metrics"  # Metrics endpoint path

googleCloudOperations:
  profiler: false
  tracing: false
  metrics: false      # Disable Google Cloud metrics if using Prometheus only
```

### How It Works

```
All 11 Microservices → OpenTelemetry Collector (port 4317)
                              ↓
                    Prometheus Endpoint (port 8889/metrics)
                              ↓
                    Your Prometheus Server (scrapes)
```

## Deployment with Harness

### Option 1: Override in Harness Service

In your Harness service definition, add:

```yaml
# Service Override Values
opentelemetryCollector:
  create: true
  prometheus:
    enabled: true
```

### Option 2: Environment-Specific Overrides

**Production:**
```yaml
opentelemetryCollector:
  create: true
  prometheus:
    enabled: true
    port: 8889
```

**Development:**
```yaml
opentelemetryCollector:
  create: true
  prometheus:
    enabled: false  # Disable Prometheus in dev
```

## Prometheus Configuration

### Auto-Discovery (if configured)

The Service includes annotations for Prometheus auto-discovery:

```yaml
annotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "8889"
  prometheus.io/path: "/metrics"
```

### Manual Scrape Config

If not using auto-discovery, add to your Prometheus config:

```yaml
scrape_configs:
  - job_name: 'onlineboutique'
    kubernetes_sd_configs:
      - role: service
    relabel_configs:
      - source_labels: [__meta_kubernetes_service_name]
        action: keep
        regex: opentelemetrycollector
      - source_labels: [__meta_kubernetes_service_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      - source_labels: [__meta_kubernetes_service_annotation_prometheus_io_port]
        action: replace
        target_label: __address__
        regex: ([^:]+)(?::\d+)?;(\d+)
        replacement: $1:$2
```

### ServiceMonitor (Prometheus Operator)

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: onlineboutique
  namespace: default
spec:
  selector:
    matchLabels:
      app: opentelemetrycollector
  endpoints:
  - port: prometheus
    interval: 30s
    path: /metrics
```

## Available Metrics

The OpenTelemetry Collector exports metrics from all services:

- **adservice** - Ad serving metrics
- **cartservice** - Shopping cart operations
- **checkoutservice** - Checkout flow metrics
- **currencyservice** - Currency conversion requests
- **emailservice** - Email notification metrics
- **frontend** - Web UI metrics
- **loadgenerator** - Load testing metrics
- **paymentservice** - Payment processing
- **productcatalogservice** - Product catalog queries
- **recommendationservice** - Recommendation engine
- **shippingservice** - Shipping calculations

## Dual Export (Prometheus + Google Cloud)

You can export to both Prometheus and Google Cloud simultaneously:

```yaml
opentelemetryCollector:
  create: true
  prometheus:
    enabled: true

googleCloudOperations:
  metrics: true  # Also send to Google Cloud
```

## Testing

1. Deploy the application with Prometheus enabled
2. Port-forward to the collector:
   ```bash
   kubectl port-forward svc/opentelemetrycollector 8889:8889
   ```
3. Check metrics endpoint:
   ```bash
   curl http://localhost:8889/metrics
   ```

## Troubleshooting

### No metrics appearing

1. Check OpenTelemetry Collector logs:
   ```bash
   kubectl logs -l app=opentelemetrycollector
   ```

2. Verify services are sending metrics:
   ```bash
   kubectl logs -l app=frontend | grep COLLECTOR_SERVICE_ADDR
   ```
   Should show: `COLLECTOR_SERVICE_ADDR=opentelemetrycollector:4317`

3. Check Prometheus scrape targets:
   - Go to Prometheus UI → Status → Targets
   - Look for `opentelemetrycollector` service

### Port conflicts

If port 8889 conflicts, change in values.yaml:
```yaml
opentelemetryCollector:
  prometheus:
    port: 9090  # Or any other available port
```

## Architecture Decision

**Why collect at the OTel Collector instead of each service?**

- ✅ Single scrape target for Prometheus
- ✅ All services' metrics automatically included
- ✅ Easier to manage and configure
- ✅ Standard OpenTelemetry → Prometheus pattern
- ✅ Can switch backends without changing service code
