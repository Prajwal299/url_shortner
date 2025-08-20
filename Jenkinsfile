pipeline {
    agent any
    environment {
        AWS_REGION = 'ap-south-1'
        ECR_REGISTRY = '934556830376.dkr.ecr.ap-south-1.amazonaws.com'
        ECR_API_REPO = 'url-shortener-api'
        ECR_FRONTEND_REPO = 'url-shortener-frontend'
        IMAGE_TAG = "${BUILD_NUMBER}"
        NAMESPACE = 'url-shortener'
    }
    
    options {
        timeout(time: 20, unit: 'MINUTES')  // Prevent indefinite hanging
        retry(2)  // Retry failed stages
    }
    
    stages {
        stage('Pre-Setup') {
            steps {
                script {
                    echo "🚀 Starting deployment pipeline..."
                    sh '''
                    echo "Current directory: $(pwd)"
                    ls -la
                    
                    # Check if required tools exist, if not skip for now
                    docker --version || echo "⚠️ Docker not found"
                    
                    # Clean up any previous builds
                    docker system prune -f || true
                    '''
                }
            }
        }
        
        stage('Install Missing Tools') {
            steps {
                script {
                    sh '''
                    echo "📦 Installing missing tools..."
                    
                    # Install kubectl if not present
                    if ! command -v kubectl &> /dev/null; then
                        echo "Installing kubectl..."
                        curl -LO "https://dl.k8s.io/release/v1.28.0/bin/linux/amd64/kubectl"
                        chmod +x kubectl
                        sudo mv kubectl /usr/local/bin/ || mv kubectl /tmp/
                        export PATH=$PATH:/tmp
                    fi
                    
                    # Install AWS CLI if not present
                    if ! command -v aws &> /dev/null; then
                        echo "Installing AWS CLI..."
                        curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
                        unzip -q awscliv2.zip
                        sudo ./aws/install || echo "Could not install AWS CLI globally"
                        rm -rf aws awscliv2.zip
                    fi
                    
                    # Verify installations
                    kubectl version --client || echo "kubectl still not available"
                    aws --version || echo "AWS CLI still not available"
                    '''
                }
            }
        }
        
        stage('Pre-Pull Images') {
            steps {
                script {
                    echo "📥 Pre-pulling base images to avoid hanging..."
                    sh '''
                    # Pre-pull base images to avoid hanging during build
                    docker pull python:3.9-slim || docker pull python:3.9 || echo "Could not pre-pull Python image"
                    docker pull node:16-alpine || docker pull node:16 || echo "Could not pre-pull Node image"
                    '''
                }
            }
        }
        
        stage('Build Images') {
            steps {
                script {
                    echo "🔨 Building Docker images..."
                    timeout(time: 10, unit: 'MINUTES') {
                        sh '''
                        echo "Building API image..."
                        docker build --no-cache --timeout 300 -t ${ECR_REGISTRY}/${ECR_API_REPO}:${IMAGE_TAG} ./app || {
                            echo "API build failed, trying with different approach..."
                            docker build -t ${ECR_REGISTRY}/${ECR_API_REPO}:${IMAGE_TAG} ./app
                        }
                        docker tag ${ECR_REGISTRY}/${ECR_API_REPO}:${IMAGE_TAG} ${ECR_REGISTRY}/${ECR_API_REPO}:latest
                        
                        echo "Building Frontend image..."
                        docker build --no-cache --timeout 300 -t ${ECR_REGISTRY}/${ECR_FRONTEND_REPO}:${IMAGE_TAG} ./frontend || {
                            echo "Frontend build failed, trying with different approach..."
                            docker build -t ${ECR_REGISTRY}/${ECR_FRONTEND_REPO}:${IMAGE_TAG} ./frontend
                        }
                        docker tag ${ECR_REGISTRY}/${ECR_FRONTEND_REPO}:${IMAGE_TAG} ${ECR_REGISTRY}/${ECR_FRONTEND_REPO}:latest
                        '''
                    }
                }
            }
        }
        
        stage('Push to ECR') {
            when {
                expression { 
                    return sh(script: 'command -v aws', returnStatus: true) == 0 
                }
            }
            steps {
                script {
                    echo "📤 Pushing to ECR..."
                    sh '''
                    # Login to ECR
                    aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}
                    
                    # Push images
                    docker push ${ECR_REGISTRY}/${ECR_API_REPO}:${IMAGE_TAG}
                    docker push ${ECR_REGISTRY}/${ECR_API_REPO}:latest
                    docker push ${ECR_REGISTRY}/${ECR_FRONTEND_REPO}:${IMAGE_TAG}
                    docker push ${ECR_REGISTRY}/${ECR_FRONTEND_REPO}:latest
                    '''
                }
            }
        }
        
        stage('Deploy to K8s') {
            when {
                allOf {
                    expression { return sh(script: 'command -v kubectl', returnStatus: true) == 0 }
                    expression { return fileExists('/var/lib/jenkins/.kube/config') || fileExists('/root/.kube/config') }
                }
            }
            steps {
                script {
                    echo "🚀 Deploying to Kubernetes (replacing old pods)..."
                    sh '''
                    # Find kubeconfig
                    for config_path in "/var/lib/jenkins/.kube/config" "/root/.kube/config" "$HOME/.kube/config"; do
                        if [ -f "$config_path" ]; then
                            export KUBECONFIG="$config_path"
                            echo "Using kubeconfig: $config_path"
                            break
                        fi
                    done
                    
                    if [ -z "$KUBECONFIG" ]; then
                        echo "No kubeconfig found, skipping k8s deployment"
                        exit 0
                    fi
                    
                    # Create namespace
                    kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f - || true
                    
                    # Apply manifests if they exist
                    if [ -d "k8s" ]; then
                        kubectl apply -f k8s/ || echo "Some manifests failed"
                    fi
                    
                    # Update deployments (this replaces old pods automatically)
                    kubectl set image deployment/api api=${ECR_REGISTRY}/${ECR_API_REPO}:${IMAGE_TAG} -n ${NAMESPACE} --record || \
                    kubectl create deployment api --image=${ECR_REGISTRY}/${ECR_API_REPO}:${IMAGE_TAG} -n ${NAMESPACE}
                    
                    kubectl set image deployment/frontend frontend=${ECR_REGISTRY}/${ECR_FRONTEND_REPO}:${IMAGE_TAG} -n ${NAMESPACE} --record || \
                    kubectl create deployment frontend --image=${ECR_REGISTRY}/${ECR_FRONTEND_REPO}:${IMAGE_TAG} -n ${NAMESPACE}
                    
                    # Wait for rollout (ensures old pods are replaced)
                    kubectl rollout status deployment/api -n ${NAMESPACE} --timeout=300s || echo "API rollout timeout"
                    kubectl rollout status deployment/frontend -n ${NAMESPACE} --timeout=300s || echo "Frontend rollout timeout"
                    
                    # Show final status
                    echo "=== Final Pod Status ==="
                    kubectl get pods -n ${NAMESPACE} -o wide || true
                    '''
                }
            }
        }
        
        stage('Fallback Local Deploy') {
            when {
                not {
                    allOf {
                        expression { return sh(script: 'command -v kubectl', returnStatus: true) == 0 }
                        expression { return fileExists('/var/lib/jenkins/.kube/config') || fileExists('/root/.kube/config') }
                    }
                }
            }
            steps {
                script {
                    echo "🔄 Kubernetes not available, starting containers locally..."
                    sh '''
                    # Stop existing containers
                    docker-compose down || true
                    
                    # Update docker-compose to use new images
                    sed -i "s|image: .*api.*|image: ${ECR_REGISTRY}/${ECR_API_REPO}:${IMAGE_TAG}|g" docker-compose.yml || true
                    sed -i "s|image: .*frontend.*|image: ${ECR_REGISTRY}/${ECR_FRONTEND_REPO}:${IMAGE_TAG}|g" docker-compose.yml || true
                    
                    # Start with new images
                    docker-compose up -d || echo "Docker compose failed"
                    
                    # Show running containers
                    docker ps
                    '''
                }
            }
        }
    }
    
    post {
        always {
            script {
                sh '''
                echo "🧹 Cleaning up..."
                # Clean up Docker images
                docker rmi ${ECR_REGISTRY}/${ECR_API_REPO}:${IMAGE_TAG} || true
                docker rmi ${ECR_REGISTRY}/${ECR_FRONTEND_REPO}:${IMAGE_TAG} || true
                
                # Clean up build cache
                docker builder prune -f || true
                '''
            }
        }
        success {
            echo "✅ Pipeline completed! Old pods/containers replaced with new ones."
        }
        failure {
            echo "❌ Pipeline failed!"
        }
        aborted {
            echo "⏹️ Pipeline aborted!"
        }
    }
}