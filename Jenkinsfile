pipeline {
    agent any
    environment {
        AWS_REGION = 'ap-south-1'
        ECR_REGISTRY = '934556830376.dkr.ecr.ap-south-1.amazonaws.com'
        ECR_API_REPO = 'url-shortener-api'
        ECR_FRONTEND_REPO = 'url-shortener-frontend'
        IMAGE_TAG = "${BUILD_NUMBER}"
        NAMESPACE = 'url-shortener'
        // Set kubeconfig path directly
        KUBECONFIG_PATH = '/var/lib/jenkins/.kube/config'
    }
    stages {
        stage('Verify Setup') {
            steps {
                script {
                    echo "Code already checked out by Jenkins"
                    sh 'ls -la'
                    sh 'docker --version || echo "Docker not found"'
                    sh 'kubectl version --client || echo "kubectl not found"'
                    sh 'aws --version || echo "AWS CLI not found"'
                }
            }
        }
        
        stage('Build Images') {
            steps {
                script {
                    echo "Building Docker images..."
                    sh "docker build -t ${ECR_REGISTRY}/${ECR_API_REPO}:${IMAGE_TAG} ./app"
                    sh "docker tag ${ECR_REGISTRY}/${ECR_API_REPO}:${IMAGE_TAG} ${ECR_REGISTRY}/${ECR_API_REPO}:latest"
                    
                    sh "docker build -t ${ECR_REGISTRY}/${ECR_FRONTEND_REPO}:${IMAGE_TAG} ./frontend"
                    sh "docker tag ${ECR_REGISTRY}/${ECR_FRONTEND_REPO}:${IMAGE_TAG} ${ECR_REGISTRY}/${ECR_FRONTEND_REPO}:latest"
                }
            }
        }
        
        stage('Push to ECR') {
            steps {
                script {
                    echo "Pushing images to ECR..."
                    sh """
                    aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}
                    docker push ${ECR_REGISTRY}/${ECR_API_REPO}:${IMAGE_TAG}
                    docker push ${ECR_REGISTRY}/${ECR_API_REPO}:latest
                    docker push ${ECR_REGISTRY}/${ECR_FRONTEND_REPO}:${IMAGE_TAG}
                    docker push ${ECR_REGISTRY}/${ECR_FRONTEND_REPO}:latest
                    """
                }
            }
        }
        
        stage('Deploy to Kubernetes') {
            steps {
                script {
                    echo "Deploying to Kubernetes - Replacing old pods with new ones..."
                    sh '''
                    # Create deployment script
                    cat > k8s-deploy.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Starting Kubernetes Deployment ==="
echo "Image Tag: ${IMAGE_TAG}"
echo "Namespace: ${NAMESPACE}"

# Check if kubeconfig exists
if [ ! -f "${KUBECONFIG_PATH}" ]; then
    echo "Kubeconfig not found at ${KUBECONFIG_PATH}"
    echo "Trying default locations..."
    
    # Try common locations
    for path in "/home/jenkins/.kube/config" "/root/.kube/config" "~/.kube/config"; do
        if [ -f "$path" ]; then
            export KUBECONFIG="$path"
            echo "Found kubeconfig at: $path"
            break
        fi
    done
    
    if [ -z "$KUBECONFIG" ]; then
        echo "ERROR: No kubeconfig found. Please set up kubectl configuration."
        exit 1
    fi
else
    export KUBECONFIG="${KUBECONFIG_PATH}"
fi

echo "Using kubeconfig: $KUBECONFIG"

# Test kubectl connectivity
echo "Testing kubectl connection..."
kubectl version --client
kubectl cluster-info || echo "Warning: Cannot connect to cluster"

# Create namespace if it doesn't exist
echo "Creating namespace ${NAMESPACE}..."
kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -

# Apply all Kubernetes manifests
echo "Applying Kubernetes manifests..."
if [ -d "k8s" ]; then
    kubectl apply -f k8s/ || echo "Some manifests failed to apply"
else
    echo "k8s directory not found, skipping manifest application"
fi

# Update deployments with new images (this replaces old pods)
echo "Updating API deployment with new image..."
kubectl set image deployment/api api=${ECR_REGISTRY}/${ECR_API_REPO}:${IMAGE_TAG} -n ${NAMESPACE} --record || \
kubectl create deployment api --image=${ECR_REGISTRY}/${ECR_API_REPO}:${IMAGE_TAG} -n ${NAMESPACE}

echo "Updating Frontend deployment with new image..."
kubectl set image deployment/frontend frontend=${ECR_REGISTRY}/${ECR_FRONTEND_REPO}:${IMAGE_TAG} -n ${NAMESPACE} --record || \
kubectl create deployment frontend --image=${ECR_REGISTRY}/${ECR_FRONTEND_REPO}:${IMAGE_TAG} -n ${NAMESPACE}

# Wait for rollout to complete (this ensures old pods are replaced)
echo "Waiting for API deployment rollout..."
kubectl rollout status deployment/api -n ${NAMESPACE} --timeout=300s

echo "Waiting for Frontend deployment rollout..."
kubectl rollout status deployment/frontend -n ${NAMESPACE} --timeout=300s

echo "=== Deployment Status ==="
kubectl get deployments -n ${NAMESPACE}
kubectl get pods -n ${NAMESPACE}

echo "=== Pod Events (Last 10) ==="
kubectl get events -n ${NAMESPACE} --sort-by='.lastTimestamp' | tail -10

echo "Deployment completed successfully! Old pods replaced with new ones."
EOF

                    chmod +x k8s-deploy.sh
                    ./k8s-deploy.sh
                    '''
                }
            }
        }
        
        stage('Verify Deployment') {
            steps {
                script {
                    sh '''
                    echo "=== Final Deployment Verification ==="
                    
                    # Set kubeconfig
                    if [ -f "${KUBECONFIG_PATH}" ]; then
                        export KUBECONFIG="${KUBECONFIG_PATH}"
                    fi
                    
                    echo "Deployments:"
                    kubectl get deployments -n ${NAMESPACE} || echo "Could not get deployments"
                    
                    echo "Pods:"
                    kubectl get pods -n ${NAMESPACE} || echo "Could not get pods"
                    
                    echo "Services:"
                    kubectl get services -n ${NAMESPACE} || echo "Could not get services"
                    
                    echo "Pod details with images:"
                    kubectl describe pods -n ${NAMESPACE} | grep -A 5 -B 5 "Image:" || true
                    '''
                }
            }
        }
    }
    
    post {
        always {
            script {
                sh '''
                echo "Cleaning up local Docker images..."
                docker rmi ${ECR_REGISTRY}/${ECR_API_REPO}:${IMAGE_TAG} || true
                docker rmi ${ECR_REGISTRY}/${ECR_API_REPO}:latest || true
                docker rmi ${ECR_REGISTRY}/${ECR_FRONTEND_REPO}:${IMAGE_TAG} || true
                docker rmi ${ECR_REGISTRY}/${ECR_FRONTEND_REPO}:latest || true
                '''
            }
        }
        success {
            echo "✅ Deployment successful! Old pods replaced with new ones."
        }
        failure {
            echo "❌ Deployment failed!"
        }
    }
}