# Testing Guide for Umbrella vs Individual Charts

## Quick Start

### Test Individual Chart
```bash
# Deploy just orders-service
helm install orders charts/orders-service --namespace app --create-namespace

# Verify
kubectl get pods -n app
curl http://<service-ip>:8080/metrics
```

### Test Umbrella Chart - All Services
```bash
# Deploy all services via umbrella
helm install microservices charts/microservices-umbrella --namespace app --create-namespace

# Verify all services
kubectl get pods -n app
kubectl get svc -n app
```

### Test Umbrella Chart - Selective Services
```bash
# Deploy only orders and inventory
helm install microservices charts/microservices-umbrella \
  --namespace app \
  --create-namespace \
  --set orders-service.enabled=true \
  --set inventory-service.enabled=true \
  --set payments-service.enabled=false \
  --set notifications-service.enabled=false
```

## Canary Deployment Testing

### Scenario 1: Individual Service Canary
**Use Case**: Update only orders-service, other services remain unchanged

```bash
# Initial deployment (stable)
helm install orders charts/orders-service \
  --namespace app \
  --set image.tag=v1.2.0 \
  --set replicaCount=3

# Canary deployment (new version with reduced replicas)
helm upgrade orders charts/orders-service \
  --namespace app \
  --set image.tag=v1.3.0 \
  --set replicaCount=1

# Verify canary
kubectl get pods -n app -l app=orders-service
# Should see: 1 pod with v1.3.0, 0 pods with v1.2.0 (as Helm does rolling update)

# Promote canary
helm upgrade orders charts/orders-service \
  --namespace app \
  --set image.tag=v1.3.0 \
  --set replicaCount=3
```

### Scenario 2: Umbrella Chart with Single Service Update
**Use Case**: Update one service while keeping others stable

```bash
# Initial deployment - all services v1.2.0
helm install microservices charts/microservices-umbrella \
  --namespace app \
  --set global.imageTag=v1.2.0

# Update only orders-service to v1.3.0
helm upgrade microservices charts/microservices-umbrella \
  --namespace app \
  --set orders-service.image.tag=v1.3.0 \
  --set orders-service.replicaCount=1

# Other services remain at v1.2.0
kubectl get pods -n app -o wide
```

### Scenario 3: Full Stack Canary via Umbrella
**Use Case**: Deploy new version of ALL services in canary mode

```bash
# Stable deployment
helm install microservices-stable charts/microservices-umbrella \
  --namespace app-stable \
  --set global.imageTag=v1.2.0

# Canary deployment (all services with new version)
helm install microservices-canary charts/microservices-umbrella \
  --namespace app-canary \
  --set global.imageTag=v1.3.0 \
  --set orders-service.replicaCount=1 \
  --set inventory-service.replicaCount=1 \
  --set payments-service.replicaCount=1 \
  --set notifications-service.replicaCount=1

# Compare both environments
kubectl get pods -n app-stable
kubectl get pods -n app-canary
```

## Harness CD Native Canary

### Individual Chart Pipeline
```yaml
# Harness service definition
service:
  name: orders-service
  identifier: orders_service

# Manifest
manifests:
  - manifest:
      identifier: orders_chart
      type: HelmChart
      spec:
        store:
          type: Git
          spec:
            paths:
              - charts/orders-service

# Canary execution
execution:
  steps:
    - step:
        type: K8sCanaryDeploy
        spec:
          instanceSelection:
            type: Count
            spec:
              count: 1
    - step:
        type: Verify
        spec:
          # Prometheus verification for orders-service only
    - step:
        type: K8sCanaryDelete
```

### Umbrella Chart Pipeline
```yaml
# Harness service definition
service:
  name: microservices-stack
  identifier: microservices_stack

# Manifest
manifests:
  - manifest:
      identifier: umbrella_chart
      type: HelmChart
      spec:
        store:
          type: Git
          spec:
            paths:
              - charts/microservices-umbrella

# Values override for canary
valuesPaths:
  - canary-values.yaml

# canary-values.yaml example:
# orders-service:
#   replicaCount: 1
#   image:
#     tag: <+artifact.tag>
```

## Performance Comparison

### Individual Chart Deployment
**Pros:**
- Faster deployment (only one service)
- Isolated failure domain
- Simpler rollback
- More granular control
- Easier to understand verification metrics

**Cons:**
- Multiple pipeline executions for full stack update
- Need to manage service dependencies manually
- More Helm releases to track

### Umbrella Chart Deployment
**Pros:**
- Single deployment for full stack
- Centralized configuration
- Easier environment parity
- Simpler to deploy related changes across services
- Better for integration testing

**Cons:**
- Slower deployment (all services)
- Larger blast radius if issues occur
- More complex verification (need to check all services)
- Rollback affects all services

## Verification Queries

### Individual Service Verification (orders-service)
```promql
# Error rate
sum(rate(http_requests_total{app="orders-service",status=~"5.."}[5m])) /
sum(rate(http_requests_total{app="orders-service"}[5m]))

# Latency P95
histogram_quantile(0.95,
  rate(http_request_duration_seconds_bucket{app="orders-service"}[5m])
)

# Orders created rate
rate(orders_created_total[5m])
```

### Umbrella Chart Verification (all services)
```promql
# Overall error rate
sum(rate(http_requests_total{namespace="app",status=~"5.."}[5m])) /
sum(rate(http_requests_total{namespace="app"}[5m]))

# Service availability
count(up{namespace="app"} == 1)

# Per-service error rate
sum by (app) (rate(http_requests_total{namespace="app",status=~"5.."}[5m]))
```

## Recommendations

### When to Use Individual Charts:
1. ✅ Independent service updates (frequent deployments)
2. ✅ Different release cadences per service
3. ✅ Service-specific canary testing
4. ✅ Microservices owned by different teams
5. ✅ Need fine-grained deployment control

### When to Use Umbrella Chart:
1. ✅ Full stack deployments to new environments
2. ✅ Coordinated multi-service releases
3. ✅ Integration testing across all services
4. ✅ Standardized configuration across services
5. ✅ Simpler management of environment-specific overrides

### Best Practice: Use Both!
- **Production**: Individual charts for each service (independent canary)
- **Staging/Dev**: Umbrella chart (faster full-stack deployment)
- **Harness Pipelines**: Create both types for flexibility

## Example Harness Workflows

### Workflow 1: Microservice Update (Individual Chart)
```
Trigger: Code commit to orders-service
  ↓
Build & Push Docker Image (v1.3.0)
  ↓
Deploy Canary (charts/orders-service, replicaCount: 1)
  ↓
Verify (Prometheus metrics for orders-service)
  ↓
Promote (replicaCount: 3)
  ↓
Notify
```

### Workflow 2: Full Stack Update (Umbrella Chart)
```
Trigger: Manual or scheduled
  ↓
Build & Push All Images (v1.3.0)
  ↓
Deploy Canary (charts/microservices-umbrella, all replicas: 1)
  ↓
Verify (Prometheus metrics for all services + integration tests)
  ↓
Promote (all replicas: 3)
  ↓
Notify
```

## Testing Commands

```bash
# Lint all charts
helm lint charts/*/

# Template all individual charts
for chart in orders-service inventory-service payments-service notifications-service; do
  echo "=== $chart ==="
  helm template test charts/$chart | grep -E "^kind:"
done

# Template umbrella chart
helm template test charts/microservices-umbrella | grep -E "^kind:"

# Dry-run installation
helm install test charts/microservices-umbrella --dry-run=client

# Check dependencies
cd charts/microservices-umbrella
helm dependency list

# Package charts for distribution
helm package charts/orders-service -d packaged/
helm package charts/microservices-umbrella -d packaged/

# Test with different value overrides
helm template test charts/microservices-umbrella \
  --values test-values.yaml \
  --set orders-service.replicaCount=5
```

## Troubleshooting

### Issue: Umbrella chart can't find dependencies
```bash
cd charts/microservices-umbrella
helm dependency update
# Then extract .tgz files to directories
cd charts
for f in *.tgz; do tar -xzf "$f"; done
```

### Issue: Image pull errors
```bash
# Verify imagePullSecrets exist
kubectl get secrets -n app

# Create if missing
kubectl create secret docker-registry harness-registry \
  --docker-server=pkg.harness.io \
  --docker-username=<username> \
  --docker-password=<password> \
  -n app
```

### Issue: Prometheus not scraping services
```bash
# Verify annotations
kubectl get svc -n app -o yaml | grep prometheus

# Check Prometheus targets
kubectl port-forward -n monitoring svc/prometheus-server 9090:80
# Visit http://localhost:9090/targets
```
