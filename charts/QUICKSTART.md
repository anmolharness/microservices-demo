# Quick Start - Umbrella Chart Setup

## What Was Created

```
charts/
├── orders-service/              # Independent chart for orders service
│   ├── Chart.yaml
│   ├── values.yaml
│   ├── .helmignore
│   └── templates/
│       ├── deployment.yaml
│       ├── service.yaml
│       └── _helpers.tpl
│
├── inventory-service/           # Independent chart for inventory service
│   ├── Chart.yaml
│   ├── values.yaml
│   └── templates/...
│
├── payments-service/            # Independent chart for payments service
│   ├── Chart.yaml
│   ├── values.yaml
│   └── templates/...
│
├── notifications-service/       # Independent chart for notifications service
│   ├── Chart.yaml
│   ├── values.yaml
│   └── templates/...
│
├── microservices-umbrella/      # Umbrella chart (orchestrates all services)
│   ├── Chart.yaml               # Defines dependencies on all 4 services
│   ├── values.yaml              # Can override any service values
│   ├── Chart.lock               # Locked dependency versions
│   └── charts/                  # Extracted subchart dependencies
│       ├── orders-service/
│       ├── inventory-service/
│       ├── payments-service/
│       └── notifications-service/
│
├── README.md                    # Complete documentation
├── TESTING.md                   # Testing scenarios and comparisons
└── QUICKSTART.md               # This file
```

## Deployment Options

### Option 1: Deploy Individual Service
```bash
# Deploy only orders-service
helm install orders charts/orders-service -n app --create-namespace

# Verify
kubectl get pods -n app
```

### Option 2: Deploy All Services via Umbrella
```bash
# Deploy the full stack
helm install microservices charts/microservices-umbrella -n app --create-namespace

# Verify all 4 services are running
kubectl get pods -n app
# Expected: 8 pods (2 replicas × 4 services)
```

### Option 3: Deploy Specific Services via Umbrella
```bash
# Deploy only orders and inventory (disable others)
helm install microservices charts/microservices-umbrella -n app \
  --set payments-service.enabled=false \
  --set notifications-service.enabled=false
```

## Test Before Deploying

```bash
# Test individual chart
helm template test charts/orders-service

# Test umbrella chart
helm template test charts/microservices-umbrella

# Lint charts
helm lint charts/orders-service
helm lint charts/microservices-umbrella
```

## Harness CD Integration

### Individual Service Pipeline
**Best for**: Frequent independent deployments, service-specific canaries

```yaml
service:
  name: orders-service
manifests:
  - type: HelmChart
    spec:
      paths:
        - charts/orders-service
```

**Canary Strategy**: Deploy only orders-service with verification

### Umbrella Chart Pipeline
**Best for**: Full-stack deployments, coordinated releases

```yaml
service:
  name: microservices-stack
manifests:
  - type: HelmChart
    spec:
      paths:
        - charts/microservices-umbrella
```

**Canary Strategy**: Deploy all services together with combined verification

## Updating Dependencies

If you modify an individual service chart and want to update the umbrella chart:

```bash
cd charts/microservices-umbrella

# Update dependencies (re-package from source charts)
helm dependency update

# Extract the .tgz files (required for Helm v4)
cd charts
for f in *.tgz; do tar -xzf "$f"; done
cd ../..

# Test
helm template test charts/microservices-umbrella
```

## Next Steps

1. **Read full documentation**: See `charts/README.md` for detailed architecture
2. **Review test scenarios**: Check `charts/TESTING.md` for canary testing strategies
3. **Deploy to Harness**: Create pipelines for both individual and umbrella charts
4. **Compare performance**: Test native canary with both deployment patterns
5. **Customize values**: Modify `values.yaml` files for your environment

## Key Benefits

### Individual Charts
- ✅ Deploy services independently
- ✅ Faster deployment (single service)
- ✅ Service-specific versioning
- ✅ Isolated canary testing
- ✅ Smaller blast radius

### Umbrella Chart
- ✅ Deploy full stack with one command
- ✅ Centralized configuration
- ✅ Environment-specific overrides
- ✅ Coordinated multi-service updates
- ✅ Integration testing

## Common Commands

```bash
# Deploy individual service
helm install <release-name> charts/<service-name> -n <namespace>

# Deploy umbrella (all services)
helm install <release-name> charts/microservices-umbrella -n <namespace>

# Upgrade individual service
helm upgrade <release-name> charts/<service-name> -n <namespace> \
  --set image.tag=v1.3.0

# Upgrade one service in umbrella
helm upgrade <release-name> charts/microservices-umbrella -n <namespace> \
  --set orders-service.image.tag=v1.3.0

# List releases
helm list -n <namespace>

# Uninstall
helm uninstall <release-name> -n <namespace>
```

## Troubleshooting

**Problem**: `helm template` fails with "missing dependencies"
```bash
cd charts/microservices-umbrella
helm dependency update
cd charts && for f in *.tgz; do tar -xzf "$f"; done
```

**Problem**: Image pull errors
```bash
# Verify imagePullSecrets in values.yaml matches your k8s secret
kubectl get secrets -n app
```

**Problem**: Services not discovered by Prometheus
```bash
# Check service annotations
kubectl get svc -n app -o yaml | grep prometheus
```

For more details, see `charts/README.md` and `charts/TESTING.md`.
