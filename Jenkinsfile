pipeline {
    agent any
    environment {
        IMAGE_TAG = "${BUILD_NUMBER}"
        NAMESPACE = 'url-shortener'
        REGISTRY = '3.110.114.163:5000'
        API_IMAGE = "${REGISTRY}/url-shortener-api"
        FRONTEND_IMAGE = "${REGISTRY}/url-shortener-frontend"
        KUBECONFIG = '/var/lib/jenkins/.kube/config'
    }
    options {
        timeout(time: 20, unit: 'MINUTES')
        retry(1)
    }
    stages {
        stage('Verify Environment') {
            steps {
                script {
                    echo "🔍 Checking available tools..."
                    sh '''
                    echo "=== Environment Check ==="
                    echo "Current directory: $(pwd)"
                    echo "Available files:"
                    ls -la
                    echo "=== Tool Availability ==="
                    docker --version && echo "✅ Docker available" || echo "❌ Docker not found"
                    kubectl --kubeconfig=$KUBECONFIG version --client && echo "✅ kubectl available" || echo "❌ kubectl not found"
                    echo "=== Registry Check ==="
                    curl -f http://${REGISTRY}/v2/ && echo "✅ Registry available" || echo "❌ Registry not accessible"
                    echo "=== Jenkins User Check ==="
                    whoami
                    groups
                    echo "=== Disk Space ==="
                    df -h
                    echo "=== Kubernetes Config ==="
                    ls -l $KUBECONFIG && echo "✅ kubeconfig found" || echo "❌ kubeconfig not found"
                    '''
                }
            }
        }
        stage('Build Application Images') {
            steps {
                script {
                    echo "🔨 Building Docker images..."
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
        stage('Configure Docker for Registry') {
            steps {
                script {
                    echo "⚙️ Configuring Docker for insecure registry..."
                    sh '''
                    # Check if daemon.json exists and configure insecure registry
                    sudo mkdir -p /etc/docker
                    if [ ! -f /etc/docker/daemon.json ]; then
                        echo '{"insecure-registries":["'${REGISTRY}'"]}' | sudo tee /etc/docker/daemon.json
                    else
                        # Update existing daemon.json (simplified - may need more complex logic)
                        echo '{"insecure-registries":["'${REGISTRY}'"]}' | sudo tee /etc/docker/daemon.json
                    fi
                    
                    # Restart Docker daemon
                    sudo systemctl restart docker
                    
                    # Wait for Docker to be ready
                    sleep 10
                    docker info | grep -i registry || echo "Registry info not available"
                    '''
                }
            }
        }
        stage('Push to Local Registry') {
            steps {
                script {
                    echo "📤 Pushing images to local registry..."
                    sh '''
                    set -e
                    echo "=== Testing registry connectivity ==="
                    curl -f http://${REGISTRY}/v2/ || {
                        echo "❌ Registry not accessible via HTTP"
                        exit 1
                    }
                    
                    echo "=== Pushing API image ==="
                    docker push ${REGISTRY}/url-shortener-api:$IMAGE_TAG || {
                        echo "❌ Failed to push API image!"
                        docker info | grep -A 5 "Insecure Registries"
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
                    echo "☸️ Deploying to Kubernetes..."
                    sh '''
                    set -e
                    if [ ! -f "$KUBECONFIG" ]; then
                        echo "❌ kubeconfig not found at $KUBECONFIG"
                        echo "Creating directory and placeholder..."
                        mkdir -p $(dirname $KUBECONFIG)
                        echo "Please configure your kubeconfig file at $KUBECONFIG"
                        exit 1
                    fi
                    
                    echo "=== Testing Kubernetes connectivity ==="
                    kubectl --kubeconfig=$KUBECONFIG cluster-info || {
                        echo "❌ Cannot connect to Kubernetes cluster"
                        exit 1
                    }
                    
                    echo "=== Cleaning up old pods ==="
                    kubectl --kubeconfig=$KUBECONFIG delete pod -n $NAMESPACE -l app=api --force --grace-period=0 || true
                    kubectl --kubeconfig=$KUBECONFIG delete pod -n $NAMESPACE -l app=frontend --force --grace-period=0 || true
                    
                    echo "=== Applying manifests ==="
                    kubectl --kubeconfig=$KUBECONFIG apply -f k8s/namespace.yaml
                    kubectl --kubeconfig=$KUBECONFIG apply -f k8s/mysql-deployment.yaml
                    
                    # Update image tags
                    kubectl --kubeconfig=$KUBECONFIG set image deployment/api api=${REGISTRY}/url-shortener-api:$IMAGE_TAG -n $NAMESPACE --record || echo "API deployment may not exist yet"
                    kubectl --kubeconfig=$KUBECONFIG set image deployment/frontend frontend=${REGISTRY}/url-shortener-frontend:$IMAGE_TAG -n $NAMESPACE --record || echo "Frontend deployment may not exist yet"
                    
                    kubectl --kubeconfig=$KUBECONFIG apply -f k8s/api-deployment.yaml
                    kubectl --kubeconfig=$KUBECONFIG apply -f k8s/frontend-deployment.yaml
                    
                    echo "=== Waiting for rollouts ==="
                    kubectl --kubeconfig=$KUBECONFIG rollout status deployment/api -n $NAMESPACE --timeout=300s
                    kubectl --kubeconfig=$KUBECONFIG rollout status deployment/frontend -n $NAMESPACE --timeout=300s
                    echo "✅ Deployment completed"
                    kubectl --kubeconfig=$KUBECONFIG get pods -n $NAMESPACE
                    '''
                }
            }
        }
        stage('Verify Deployment') {
            steps {
                script {
                    echo "🏥 Verifying deployment..."
                    sh '''
                    if [ ! -f "$KUBECONFIG" ]; then
                        echo "❌ kubeconfig not found at $KUBECONFIG"
                        exit 1
                    fi
                    echo "=== Deployment Status ==="
                    kubectl --kubeconfig=$KUBECONFIG get deployments -n $NAMESPACE
                    echo "=== Pod Status ==="
                    kubectl --kubeconfig=$KUBECONFIG get pods -n $NAMESPACE
                    echo "=== Service Status ==="
                    kubectl --kubeconfig=$KUBECONFIG get services -n $NAMESPACE
                    '''
                }
            }
        }
    }
    post {
        always {
            sh '''
            echo "🧹 Cleaning up..."
            docker image prune -f --filter "until=48h" || true
            docker container prune -f || true
            echo "=== Final System Status ==="
            docker system df
            '''
        }
        success {
            echo """
            ✅ 🎉 DEPLOYMENT SUCCESSFUL! 🎉 ✅
            📋 What happened:
            • Built new images with tag: $IMAGE_TAG
            • Replaced old pods with new ones
            • Application is running with latest code
            🔗 Access your application:
            • Frontend: http://3.110.114.163:30300
            • API: http://3.110.114.163:30500
            """
        }
        failure {
            echo """
            ❌ Deployment failed! 
            🔍 Common issues to check:
            • Docker build issues (check Dockerfile, network)
            • Local registry connectivity (http://3.110.114.163:5000)
            • Kubernetes connectivity or manifest errors
            • Missing kubeconfig at $KUBECONFIG
            Check the logs above for details.
            """
        }
    }
}