#!/bin/bash

# complete-k8s-setup.sh - Complete setup for URL Shortener on Kubernetes

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }
print_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

echo "🚀 Complete Kubernetes Setup for URL Shortener"
echo "=============================================="

# Step 1: Pre-flight checks
print_step "1. Performing pre-flight checks..."

if ! command -v kubectl &> /dev/null; then
    print_error "kubectl is not installed or not in PATH"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed or not in PATH"
    exit 1
fi

if ! kubectl get nodes &>/dev/null; then
    print_error "kubectl not configured properly or cluster not accessible"
    exit 1
fi

print_status "Pre-flight checks passed ✓"

# Step 2: Stop existing Docker Compose services
print_step "2. Stopping existing Docker Compose services..."
if [ -f "docker-compose.yml" ]; then
    docker-compose down || print_warning "Docker Compose services may not be running"
    print_status "Docker Compose services stopped ✓"
else
    print_warning "docker-compose.yml not found, skipping..."
fi

# Step 3: Install metrics-server for HPA
print_step "3. Installing metrics-server for HPA..."
kubectl apply -f k8s/metrics-server.yaml
print_status "Metrics-server deployed ✓"

# Step 4: Build Docker images
print_step "4. Building Docker images locally..."

if [ ! -d "app" ]; then
    print_error "app directory not found"
    exit 1
fi

if [ ! -d "frontend" ]; then
    print_error "frontend directory not found"
    exit 1
fi

# Build API image
print_status "Building API image..."
docker build -t url_shortner_api:latest ./app/

# Build Frontend image
print_status "Building Frontend image..."
docker build -t url_shortner_frontend:latest ./frontend/

print_status "Docker images built successfully ✓"

# Step 5: Load images into kind cluster (if using kind)
print_step "5. Loading images into Kubernetes cluster..."

# Check if using kind
if kubectl config current-context | grep -q "kind"; then
    CLUSTER_NAME=$(kubectl config current-context | sed 's/kind-//')
    print_status "Detected kind cluster: $CLUSTER_NAME"
    
    kind load docker-image url_shortner_api:latest --name $CLUSTER_NAME
    kind load docker-image url_shortner_frontend:latest --name $CLUSTER_NAME
    print_status "Images loaded into kind cluster ✓"
else
    print_status "Not using kind cluster, images available locally ✓"
fi

# Step 6: Deploy to Kubernetes
print_step "6. Deploying to Kubernetes..."

# Create namespace
kubectl apply -f k8s/namespace.yaml
print_status "Namespace created ✓"

# Deploy MySQL
print_status "Deploying MySQL database..."
kubectl apply -f k8s/mysql-deployment.yaml

# Wait for MySQL to be ready
print_status "Waiting for MySQL to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/mysql -n url-shortener

# Deploy API
print_status "Deploying API service..."
kubectl apply -f k8s/api-deployment.yaml

# Deploy Frontend
print_status "Deploying Frontend service..."
kubectl apply -f k8s/frontend-deployment.yaml

# Wait for services to be ready
print_status "Waiting for services to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/api -n url-shortener
kubectl wait --for=condition=available --timeout=300s deployment/frontend -n url-shortener

print_status "Core services deployed ✓"

# Step 7: Setup HPA
print_step "7. Setting up Horizontal Pod Autoscaler..."

# Wait for metrics-server to be ready
print_status "Waiting for metrics-server to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/metrics-server -n kube-system || print_warning "Metrics-server may still be starting"

# Apply HPA
kubectl apply -f k8s/hpa.yaml
print_status "HPA configured ✓"

# Step 8: Deploy monitoring stack
print_step "8. Deploying monitoring stack..."

# Deploy Prometheus
kubectl apply -f k8s/prometheus/
print_status "Prometheus deployed ✓"

# Deploy Grafana
kubectl apply -f k8s/grafana/
print_status "Grafana deployed ✓"

# Wait for monitoring stack
print_status "Waiting for monitoring stack to be ready..."
sleep 30  # Give some time for initial startup

# Step 9: Display status and URLs
print_step "9. Deployment complete! Getting status..."

echo ""
echo "📊 DEPLOYMENT STATUS"
echo "===================="

print_status "Pods status:"
kubectl get pods -n url-shortener

echo ""
print_status "Services status:"
kubectl get services -n url-shortener

echo ""
print_status "HPA status:"
kubectl get hpa -n url-shortener

# Get access URLs
NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')
EXTERNAL_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="ExternalIP")].address}')

if [ -n "$EXTERNAL_IP" ]; then
    ACCESS_IP=$EXTERNAL_IP
else
    ACCESS_IP=$NODE_IP
fi

echo ""
echo "🌐 ACCESS URLS"
echo "=============="
echo "   Frontend:   http://$ACCESS_IP:30080"
echo "   Prometheus: http://$ACCESS_IP:30090"
echo "   Grafana:    http://$ACCESS_IP:30030"
echo "   Grafana Login: admin/admin"
echo ""

# Step 10: Provide useful commands
echo "🛠️  USEFUL COMMANDS"
echo "=================="
echo "Monitor pods:           kubectl get pods -n url-shortener -w"
echo "Check HPA:              kubectl get hpa -n url-shortener -w"
echo "Scale API manually:     kubectl scale deployment api --replicas=5 -n url-shortener"
echo "View API logs:          kubectl logs -f deployment/api -n url-shortener"
echo "View frontend logs:     kubectl logs -f deployment/frontend -n url-shortener"
echo "Test load (new terminal): kubectl apply -f k8s/load-test.yaml"
echo "Stop load test:         kubectl delete pod load-test -n url-shortener"
echo ""

# Step 11: Test HPA setup
print_step "10. Testing HPA setup..."
echo ""
print_status "Current HPA metrics:"
kubectl top pods -n url-shortener || print_warning "Metrics not yet available (normal for new deployments)"

echo ""
print_status "🎉 Setup Complete!"
echo ""
print_warning "Note: It may take 2-3 minutes for all metrics to become available."
print_warning "HPA scaling decisions are made every 30 seconds based on average CPU usage."
echo ""
print_status "To test auto-scaling:"
echo "1. Apply load test: kubectl apply -f k8s/load-test.yaml"  
echo "2. Watch HPA: kubectl get hpa -n url-shortener -w"
echo "3. Monitor scaling: kubectl get pods -n url-shortener -w"