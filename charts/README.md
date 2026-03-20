# Microservices Helm Charts - Umbrella Pattern

This directory contains Helm charts using the umbrella pattern, where each microservice is packaged as an independent chart, and an umbrella chart orchestrates them all.

## Architecture

### Individual Service Charts
Each microservice has its own independent Helm chart:
- `orders-service/` - Orders management service
- `inventory-service/` - Inventory and stock management service
- `payments-service/` - Payment processing service
- `notifications-service/` - Notification delivery service

### Umbrella Chart
The `microservices-umbrella/` chart includes all services as dependencies, allowing:
- Full-stack deployment with a single command
- Individual service enable/disable via values
- Centralized configuration with per-service overrides
- Independent versioning of each service

## Deployment Options

### Option 1: Deploy Individual Services
Deploy a single service independently:

```bash
# Deploy only orders-service
helm install orders ./charts/orders-service \
  --namespace app \
  --create-namespace

# Deploy only payments-service with custom values
helm install payments ./charts/payments-service \
  --namespace app \
  --set replicaCount=3 \
  --set image.tag=v1.3.0
```

### Option 2: Deploy All Services via Umbrella Chart
Deploy all services together:

```bash
# First, update dependencies
cd charts/microservices-umbrella
helm dependency update

# Deploy all services
helm install microservices ./charts/microservices-umbrella \
  --namespace app \
  --create-namespace

# Or with custom values
helm install microservices ./charts/microservices-umbrella \
  --namespace app \
  --values custom-values.yaml
```

### Option 3: Selective Service Deployment via Umbrella
Deploy only specific services using the umbrella chart:

```bash
# Deploy only orders and inventory services
helm install microservices ./charts/microservices-umbrella \
  --namespace app \
  --set orders-service.enabled=true \
  --set inventory-service.enabled=true \
  --set payments-service.enabled=false \
  --set notifications-service.enabled=false
```

## Harness CD Native Canary Deployment

### Individual Service Canary
When deploying individual charts, Harness can perform native canary on a single service:

**Harness Pipeline Configuration:**
```yaml
service:
  name: orders-service
  identifier: orders_service

manifests:
  - manifest:
      identifier: orders_chart
      type: HelmChart
      spec:
        store:
          type: Git
          spec:
            connectorRef: github_connector
            gitFetchType: Branch
            folderPath: charts/orders-service
```

**Execution Strategy:**
- Canary Deployment with verification
- Traffic split: 25% → 50% → 100%
- Prometheus metrics verification at each phase

### Umbrella Chart Canary
When deploying the umbrella chart, you can:

1. **Full-stack canary**: All services deploy together in canary fashion
2. **Selective service updates**: Update only specific services while keeping others stable

**Example values override for canary:**
```yaml
# Production values (stable)
orders-service:
  image:
    tag: v1.2.0
  replicaCount: 3

# Canary values (new version)
orders-service:
  image:
    tag: v1.3.0-canary
  replicaCount: 1
```

## Testing Canary Behavior

### Test 1: Individual Service Canary
```bash
# Deploy stable version
helm install orders ./charts/orders-service \
  --namespace app \
  --set image.tag=v1.2.0 \
  --set replicaCount=3

# Upgrade with canary (manual test)
helm upgrade orders ./charts/orders-service \
  --namespace app \
  --set image.tag=v1.3.0 \
  --set replicaCount=1
```

### Test 2: Umbrella Chart with Single Service Update
```bash
# Initial deployment (all services v1.2.0)
helm install microservices ./charts/microservices-umbrella \
  --namespace app

# Update only orders-service to v1.3.0
helm upgrade microservices ./charts/microservices-umbrella \
  --namespace app \
  --set orders-service.image.tag=v1.3.0
```

### Test 3: Full Stack Canary via Umbrella
```bash
# Deploy with all services in canary
helm install microservices ./charts/microservices-umbrella \
  --namespace app \
  --set global.imageTag=v1.3.0-canary \
  --set orders-service.replicaCount=1 \
  --set inventory-service.replicaCount=1 \
  --set payments-service.replicaCount=1 \
  --set notifications-service.replicaCount=1
```

## Configuration

### Per-Service Configuration
Each service chart has its own `values.yaml` with:
- Replica count
- Image registry/repository/tag
- Resource requests/limits
- Probe configurations
- Prometheus scraping settings

### Umbrella Configuration
The umbrella chart's `values.yaml` allows:
- Enabling/disabling individual services
- Overriding any service-specific value
- Setting global values (image registry, pull secrets)

### Value Precedence
Values are merged in this order (highest precedence last):
1. Individual chart defaults (`charts/orders-service/values.yaml`)
2. Umbrella chart defaults (`charts/microservices-umbrella/values.yaml`)
3. Custom values file (`--values custom.yaml`)
4. Command-line overrides (`--set key=value`)

## Harness Verification Setup

### Individual Service Verification
```yaml
# Verify only the service being deployed
healthSources:
  - identifier: prometheus_orders
    type: Prometheus
    spec:
      connectorRef: prometheus_connector
      metricPacks:
        - identifier: Performance
      metricDefinitions:
        - identifier: error_rate
          metricName: Error Rate
          query: |
            sum(rate(http_requests_total{app="orders-service",status=~"5.."}[5m]))
```

### Umbrella Chart Verification
```yaml
# Verify all services in the stack
healthSources:
  - identifier: prometheus_all_services
    type: Prometheus
    spec:
      connectorRef: prometheus_connector
      metricDefinitions:
        - identifier: overall_error_rate
          metricName: Overall Error Rate
          query: |
            sum(rate(http_requests_total{namespace="app",status=~"5.."}[5m]))

        - identifier: service_availability
          metricName: Service Availability
          query: |
            count(up{namespace="app"} == 1)
```

## Benefits of This Approach

### Individual Charts
- ✅ Deploy services independently
- ✅ Version each service separately
- ✅ Faster canary deployments (single service)
- ✅ Isolated rollbacks
- ✅ Clear ownership boundaries

### Umbrella Chart
- ✅ Deploy full stack with one command
- ✅ Centralized configuration management
- ✅ Consistent versioning across services
- ✅ Environment-specific overrides
- ✅ Simplified multi-service updates

## Next Steps

1. **Package charts**: `helm package charts/orders-service`
2. **Push to registry**: Upload charts to Harness or OCI registry
3. **Configure Harness CD**: Create pipelines for both individual and umbrella deployments
4. **Test canary strategies**: Compare performance of individual vs umbrella canaries
5. **Set up verification**: Configure Prometheus queries for each deployment type

## Commands Reference

```bash
# Lint charts
helm lint charts/orders-service
helm lint charts/microservices-umbrella

# Template rendering (dry-run)
helm template test charts/orders-service
helm template test charts/microservices-umbrella

# Update umbrella dependencies
cd charts/microservices-umbrella
helm dependency update
helm dependency list

# Install with dry-run
helm install test charts/microservices-umbrella --dry-run --debug

# List releases
helm list -n app

# Upgrade
helm upgrade microservices charts/microservices-umbrella -n app

# Rollback
helm rollback microservices 1 -n app

# Uninstall
helm uninstall microservices -n app
```
