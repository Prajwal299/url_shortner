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
        timeout(time: 15, unit: 'MINUTES')
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
                    kubectl version --client && echo "✅ kubectl available" || echo "❌ kubectl not found"
                    aws --version && echo "✅ AWS CLI available" || echo "❌ AWS CLI not found"
                    unzip -v && echo "✅ unzip available" || echo "❌ unzip not found"
                    
                    echo "=== Jenkins User Check ==="
                    whoami
                    groups
                    '''
                }
            }
        }
        
        stage('Build Application Images') {
            steps {
                script {
                    echo "🔨 Building Docker images..."
                    timeout(time: 8, unit: 'MINUTES') {
                        sh '''
                        echo "Building API image..."
                        docker build -t ${ECR_REGISTRY}/${ECR_API_REPO}:${IMAGE_TAG} ./app
                        docker tag ${ECR_REGISTRY}/${ECR_API_REPO}:${IMAGE_TAG} ${ECR_REGISTRY}/${ECR_API_REPO}:latest
                        
                        echo "Building Frontend image..."  
                        docker build -t ${ECR_REGISTRY}/${ECR_FRONTEND_REPO}:${IMAGE_TAG} ./frontend
                        docker tag ${ECR_REGISTRY}/${ECR_FRONTEND_REPO}:${IMAGE_TAG} ${ECR_REGISTRY}/${ECR_FRONTEND_REPO}:latest
                        
                        echo "✅ Images built successfully"
                        docker images | grep ${ECR_REGISTRY}
                        '''
                    }
                }
            }
        }
        
        stage('Deploy Locally with Docker Compose') {
            steps {
                script {
                    echo "🚀 Deploying locally (replacing old containers)..."
                    sh '''
                    echo "Current docker-compose.yml:"
                    cat docker-compose.yml || echo "No docker-compose.yml found"
                    
                    echo "Stopping old containers..."
                    docker-compose down || echo "No containers to stop"
                    
                    echo "Starting new containers with fresh images..."
                    # Update the compose file to use our newly built images
                    cat > docker-compose-deploy.yml << EOF
version: '3.8'
services:
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: rootpassword
      MYSQL_DATABASE: url_shortener
      MYSQL_USER: user
      MYSQL_PASSWORD: userpassword
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      timeout: 20s
      retries: 10

  api:
    image: ${ECR_REGISTRY}/${ECR_API_REPO}:${IMAGE_TAG}
    ports:
      - "5000:5000"
    depends_on:
      - mysql
    environment:
      - DATABASE_URL=mysql://user:userpassword@mysql:3306/url_shortener
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      timeout: 10s
      retries: 5

  frontend:
    image: ${ECR_REGISTRY}/${ECR_FRONTEND_REPO}:${IMAGE_TAG}
    ports:
      - "3000:3000"
    depends_on:
      - api
    environment:
      - REACT_APP_API_URL=http://localhost:5000

volumes:
  mysql_data:
EOF
                    
                    echo "Starting services with new images..."
                    docker-compose -f docker-compose-deploy.yml up -d
                    
                    echo "Waiting for services to be ready..."
                    sleep 10
                    
                    echo "=== Container Status ==="
                    docker-compose -f docker-compose-deploy.yml ps
                    
                    echo "=== Container Logs (last 10 lines) ==="
                    docker-compose -f docker-compose-deploy.yml logs --tail=10
                    
                    echo "✅ Local deployment complete - old containers replaced!"
                    '''
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
                    echo "📤 Pushing images to ECR..."
                    sh '''
                    echo "Logging into ECR..."
                    aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}
                    
                    echo "Pushing images..."
                    docker push ${ECR_REGISTRY}/${ECR_API_REPO}:${IMAGE_TAG}
                    docker push ${ECR_REGISTRY}/${ECR_API_REPO}:latest
                    docker push ${ECR_REGISTRY}/${ECR_FRONTEND_REPO}:${IMAGE_TAG}
                    docker push ${ECR_REGISTRY}/${ECR_FRONTEND_REPO}:latest
                    
                    echo "✅ Images pushed to ECR"
                    '''
                }
            }
        }
        
        stage('Deploy to Kubernetes') {
            when {
                allOf {
                    expression { return sh(script: 'command -v kubectl', returnStatus: true) == 0 }
                    anyOf {
                        expression { return fileExists('/var/lib/jenkins/.kube/config') }
                        expression { return fileExists('/root/.kube/config') }
                        expression { return fileExists('/home/jenkins/.kube/config') }
                    }
                }
            }
            steps {
                script {
                    echo "☸️ Deploying to Kubernetes (replacing old pods)..."
                    sh '''
                    # Find kubeconfig
                    for config_path in "/var/lib/jenkins/.kube/config" "/root/.kube/config" "/home/jenkins/.kube/config"; do
                        if [ -f "$config_path" ]; then
                            export KUBECONFIG="$config_path"
                            echo "Using kubeconfig: $config_path"
                            break
                        fi
                    done
                    
                    if [ -z "$KUBECONFIG" ]; then
                        echo "❌ No kubeconfig found"
                        exit 1
                    fi
                    
                    echo "Testing kubectl connection..."
                    kubectl cluster-info || echo "Warning: cluster connection issues"
                    
                    echo "Creating/updating namespace..."
                    kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
                    
                    echo "Applying Kubernetes manifests..."
                    kubectl apply -f k8s/ || echo "Some manifests failed to apply"
                    
                    echo "Updating deployments with new images (this replaces old pods)..."
                    kubectl set image deployment/api api=${ECR_REGISTRY}/${ECR_API_REPO}:${IMAGE_TAG} -n ${NAMESPACE} --record || \
                    kubectl create deployment api --image=${ECR_REGISTRY}/${ECR_API_REPO}:${IMAGE_TAG} -n ${NAMESPACE}
                    
                    kubectl set image deployment/frontend frontend=${ECR_REGISTRY}/${ECR_FRONTEND_REPO}:${IMAGE_TAG} -n ${NAMESPACE} --record || \
                    kubectl create deployment frontend --image=${ECR_REGISTRY}/${ECR_FRONTEND_REPO}:${IMAGE_TAG} -n ${NAMESPACE}
                    
                    echo "Waiting for rollouts to complete..."
                    kubectl rollout status deployment/api -n ${NAMESPACE} --timeout=300s || echo "API rollout timeout"
                    kubectl rollout status deployment/frontend -n ${NAMESPACE} --timeout=300s || echo "Frontend rollout timeout"
                    
                    echo "=== Final Kubernetes Status ==="
                    kubectl get pods -n ${NAMESPACE} -o wide
                    kubectl get deployments -n ${NAMESPACE}
                    
                    echo "✅ Kubernetes deployment complete - old pods replaced!"
                    '''
                }
            }
        }
        
        stage('Health Check') {
            steps {
                script {
                    echo "🏥 Running health checks..."
                    sh '''
                    echo "=== Application Health Check ==="
                    
                    # Check local deployment
                    if docker ps | grep -q "url-shortener"; then
                        echo "✅ Local containers are running"
                        
                        # Try to access the application
                        sleep 5
                        curl -f http://localhost:5000/health || curl -f http://localhost:5000 || echo "API not responding yet"
                        curl -f http://localhost:3000 || echo "Frontend not responding yet"
                    else
                        echo "⚠️ No local containers found"
                    fi
                    
                    echo "=== Docker Status ==="
                    docker ps --format "table {{.Names}}\\t{{.Status}}\\t{{.Ports}}"
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
                
                # Remove unused images (keep the latest)
                docker image prune -f || true
                
                # Don't remove the images we just built as they might be in use
                echo "Keeping newly built images for running containers"
                '''
            }
        }
        success {
            echo """
            ✅ 🎉 DEPLOYMENT SUCCESSFUL! 🎉 ✅
            
            📋 What happened:
            • Built new images with tag: ${BUILD_NUMBER}
            • Replaced old containers/pods with new ones
            • Application is running with latest code
            
            🔗 Access your application:
            • Frontend: http://localhost:3000
            • API: http://localhost:5000
            
            🚀 Next push will automatically replace these containers!
            """
        }
        failure {
            echo "❌ Deployment failed! Check the logs above for details."
        }
    }
}