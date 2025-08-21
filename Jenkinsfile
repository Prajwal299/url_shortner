=pipeline {
    agent any
    environment {
        IMAGE_TAG = "${BUILD_NUMBER}"
        NAMESPACE = 'url-shortener'
        REGISTRY = '3.110.114.163:5000'
        API_IMAGE = "${REGISTRY}/url-shortener-api"
        FRONTEND_IMAGE = "${REGISTRY}/url-shortener-frontend"
    }
    options {
        timeout(time: 20, unit: 'MINUTES')
        retry(1)
    }
    stages {
        stage('Verify Environment') {
            steps {
                script {
                    echo "Checking available tools..."
                    sh '''
                    echo "=== Environment Check ==="
                    echo "Current directory: $(pwd)"
                    echo "Available files:"
                    ls -la
                    echo "=== Tool Availability ==="
                    docker --version && echo "✅ Docker available" || echo "❌ Docker not found"
                    kubectl version --client && echo "✅ kubectl available" || echo "❌ kubectl not found"
                    echo "=== Registry Check ==="
                    curl -s http://${REGISTRY}/v2/ && echo "✅ Registry available" || echo "❌ Registry not accessible"
                    echo "=== Jenkins User Check ==="
                    whoami
                    groups
                    echo "=== Disk Space ==="
                    df -h
                    '''
                }
            }
        }
        stage('Build Application Images') {
            steps {
                script {
                    echo "Building Docker images..."
                    timeout(time: 15, unit: 'MINUTES') {
                        sh '''
                        set -e
                        echo "=== Cleaning up old images ==="
                        docker image prune -f --filter "until=48h" || true
                        echo "=== Building API image ==="
                        docker build -t ${REGISTRY}/url-shortener-api:$IMAGE_TAG -t ${REGISTRY}/url-shortener-api:latest ./app || {
                            echo "❌ API build failed!"
                            df -h
                            docker system df
                            exit 1
                        }
                        echo "=== Building Frontend image ==="
                        docker build -t ${REGISTRY}/url-shortener-frontend:$IMAGE_TAG -t ${REGISTRY}/url-shortener-frontend:latest ./frontend || {
                            echo "❌ Frontend build failed!"
                            df -h
                            docker system df
                            exit 1
                        }
                        echo "✅ Images built successfully"
                        docker images | grep ${REGISTRY}
                        '''
                    }
                }
            }
        }
        stage('Push to Local Registry') {
            steps {
                script {
                    echo "Pushing images to local registry..."
                    sh '''
                    set -e
                    echo "=== Testing registry connectivity ==="
                    curl -f http://${REGISTRY}/v2/ || {
                        echo "❌ Registry not accessible via HTTP"
                        echo "Please ensure Docker registry is running on ${REGISTRY}"
                        echo "Run: docker run -d -p 5000:5000 --name registry --restart=always registry:2"
                        exit 1
                    }
                    
                    echo "=== Pushing API image ==="
                    docker push ${REGISTRY}/url-shortener-api:$IMAGE_TAG || {
                        echo "❌ Failed to push API image!"
                        echo "Make sure Docker daemon is configured for insecure registry ${REGISTRY}"
                        exit 1
                    }
                    docker push ${REGISTRY}/url-shortener-api:latest
                    
                    echo "=== Pushing Frontend image ==="
                    docker push ${REGISTRY}/url-shortener-frontend:$IMAGE_TAG || {
                        echo "❌ Failed to push frontend image!"
                        exit 1
                    }
                    docker push ${REGISTRY}/url-shortener-frontend:latest
                    echo "✅ Images pushed to local registry"
                    '''
                }
            }
        }
        stage('Deploy to Kubernetes') {
            steps {
                script {
                    echo "Deploying to Kubernetes..."
                    sh '''
                    set -e
                    # Create temporary kubeconfig using environment variables or service account
                    export KUBECONFIG=$(mktemp)
                    
                    # Try to build kubeconfig from environment variables first
                    if [ ! -z "$K8S_SERVER_URL" ] && [ ! -z "$K8S_TOKEN" ]; then
                        echo "=== Using K8S credentials from environment ==="
                        kubectl config set-cluster k8s-cluster --server=$K8S_SERVER_URL --insecure-skip-tls-verify=true
                        kubectl config set-credentials jenkins --token=$K8S_TOKEN
                        kubectl config set-context k8s-context --cluster=k8s-cluster --user=jenkins --namespace=$NAMESPACE
                        kubectl config use-context k8s-context
                    else
                        echo "=== No K8S credentials found ==="
                        echo "Please set K8S_SERVER_URL and K8S_TOKEN environment variables"
                        echo "Or configure Jenkins credentials with IDs: k8s-server-url, k8s-token"
                        echo "For now, skipping Kubernetes deployment..."
                        rm -f $KUBECONFIG
                        exit 0
                    fi
                    
                    echo "=== Testing Kubernetes connectivity ==="
                    kubectl cluster-info || {
                        echo "❌ Cannot connect to Kubernetes cluster"
                        rm -f $KUBECONFIG
                        exit 1
                    }
                    
                    echo "=== Creating namespace ==="
                    kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
                    
                    echo "=== Applying manifests ==="
                    kubectl apply -f k8s/ --recursive || echo "Some manifests may have failed"
                    
                    # Update image tags for existing deployments
                    kubectl set image deployment/api api=${REGISTRY}/url-shortener-api:$IMAGE_TAG -n $NAMESPACE --record || echo "API deployment may not exist yet"
                    kubectl set image deployment/frontend frontend=${REGISTRY}/url-shortener-frontend:$IMAGE_TAG -n $NAMESPACE --record || echo "Frontend deployment may not exist yet"
                    
                    echo "=== Checking deployment status ==="
                    kubectl get pods -n $NAMESPACE || echo "No pods found yet"
                    
                    # Clean up temporary kubeconfig
                    rm -f $KUBECONFIG
                    '''
                }
            }
        }
    }
    post {
        always {
            sh '''
            echo "Cleaning up..."
            docker image prune -f --filter "until=48h" || true
            docker container prune -f || true
            echo "=== Final System Status ==="
            docker system df
            '''
        }
        success {
            echo """
            ✅ DEPLOYMENT SUCCESSFUL!
            📋 What happened:
            • Built new images with tag: $IMAGE_TAG
            • Pushed images to registry
            • Deployed to Kubernetes (if configured)
            🔗 Access your application:
            • Frontend: http://3.110.114.163:30300
            • API: http://3.110.114.163:30500
            """
        }
        failure {
            echo """
            ❌ Deployment failed! 
            🔍 Check:
            • Registry running: docker run -d -p 5000:5000 --name registry registry:2
            • Jenkins docker access: sudo usermod -aG docker jenkins
            • K8S credentials: Set K8S_SERVER_URL and K8S_TOKEN
            """
        }
    }
}