#!/bin/bash

set -e

echo "🚀 Starting Kubernetes deployment for URL Shortener"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    print_error "kubectl is not installed or not in PATH"
    exit 1
fi

# Check if cluster is accessible
if ! kubectl cluster-info &> /dev/null; then
    print_error "Cannot connect to Kubernetes cluster"
    exit 1
fi

print_success "Connected to Kubernetes cluster"

# Step 1: Build Docker images locally
print_status "Building Docker images..."

# Check if Dockerfiles exist
if [[ ! -f "./app/Dockerfile" ]]; then
    print_error "app/Dockerfile not found"
    exit 1
fi

if [[ ! -f "./frontend/Dockerfile" ]]; then
    print_error "frontend/Dockerfile not found"
    exit 1
fi

# Build images
docker build -t url_shortener-api:latest ./app
docker build -t url_shortener-frontend:latest ./frontend

print_success "Docker images built successfully"

# Step 2: Create data directory for MySQL PV
print_status "Creating MySQL data directory on master node..."
sudo mkdir -p /mnt/mysql-data
sudo chmod 777 /mnt/mysql-data

print_success "MySQL data directory created"

# Step 3: Apply Kubernetes manifests
print_status "Applying Kubernetes manifests..."

# Create namespace
kubectl apply -f k8s/namespace.yaml
print_success "Namespace created"

# Apply MySQL deployment
kubectl apply -f k8s/mysql-deployment.yaml
print_success "MySQL deployment created"

# Wait for MySQL to be ready
print_status "Waiting for MySQL to be ready..."
kubectl wait --for=condition=ready pod -l app=mysql -n url_shortener --timeout=300s
print_success "MySQL is ready"

# Apply API deployment
kubectl apply -f k8s/api-deployment.yaml
print_success "API deployment created"

# Apply frontend deployment
kubectl apply -f k8s/frontend-deployment.yaml
print_success "Frontend deployment created"

# Wait for API and frontend to be ready
print_status "Waiting for API pods to be ready..."
kubectl wait --for=condition=ready pod -l app=api -n url_shortener --timeout=300s

print_status "Waiting for frontend pods to be ready..."
kubectl wait --for=condition=ready pod -l app=frontend -n url_shortener --timeout=300s

print_success "All applications are ready"

# Apply HPA
kubectl apply -f k8s/hpa.yaml
print_success "HPA configuration applied"

# Step 4: Display deployment status
print_status "Deployment Summary:"
echo "===================="

kubectl get all -n url_shortener

echo ""
print_status "Services:"
kubectl get svc -n url_shortener

echo ""
print_status "HPA Status:"
kubectl get hpa -n url_shortener

# Get node IP
NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="ExternalIP")].address}')
if [[ -z "$NODE_IP" ]]; then
    NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')
fi

echo ""
print_success "🎉 Deployment completed successfully!"
echo ""
echo "Access your application:"
echo "Frontend: http://${NODE_IP}:30080"
echo "API: http://${NODE_IP}:30081"
echo ""
echo "To monitor the deployment:"
echo "kubectl get pods -n url_shortener -w"
echo ""
echo "To check logs:"
echo "kubectl logs -l app=api -n url_shortener"
echo "kubectl logs -l app=frontend -n url_shortener"
echo "kubectl logs -l app=mysql -n url_shortener"

print_status "Deployment script completed!"