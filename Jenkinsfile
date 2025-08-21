pipeline {
    agent any
    environment {
        AWS_REGION = 'ap-south-1'
        ECR_REGISTRY = '934556830376.dkr.ecr.ap-south-1.amazonaws.com'
        ECR_API_REPO = 'url-shortener-api'
        ECR_FRONTEND_REPO = 'url-shortener-frontend'
        IMAGE_TAG = "${BUILD_NUMBER}"
        NAMESPACE = 'url-shortener'
        DOCKER_BUILDKIT = '1'
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
                    kubectl version --client && echo "✅ kubectl available" || echo "❌ kubectl not found"
                    aws --version && echo "✅ AWS CLI available" || echo "❌ AWS CLI not found"
                    unzip -v && echo "✅ unzip available" || echo "❌ unzip not found"
                    
                    echo "=== Jenkins User Check ==="
                    whoami
                    groups
                    
                    echo "=== Docker System Info ==="
                    docker system df
                    '''
                }
            }
        }
        
        stage('Build Application Images') {
            steps {
                script {
                    echo "🔨 Building Docker images with optimizations..."
                    timeout(time: 12, unit: 'MINUTES') {
                        sh '''
                        set -e  # Exit on any error
                        
                        echo "=== Docker Build Environment ==="
                        docker --version
                        docker system df
                        
                        echo "=== Cleaning up old containers and images ==="
                        # Stop any running containers that might conflict
                        docker ps -q --filter "expose=5000" | xargs -r docker stop || true
                        docker ps -q --filter "expose=3000" | xargs -r docker stop || true
                        
                        # Remove old images to free space (keep last 2 days)
                        docker image prune -a -f --filter "until=48h" || true
                        docker container prune -f || true
                        
                        echo "=== Building API image ==="
                        echo "API Dockerfile content:"
                        cat ./app/Dockerfile
                        echo ""
                        echo "API requirements.txt content:"
                        cat ./app/requirements.txt
                        echo ""
                        
                        # Build API image with optimizations
                        docker build \
                            --no-cache \
                            --progress=plain \
                            --network=host \
                            --build-arg BUILDKIT_INLINE_CACHE=1 \
                            -t ${ECR_REGISTRY}/${ECR_API_REPO}:${IMAGE_TAG} \
                            -t ${ECR_REGISTRY}/${ECR_API_REPO}:latest \
                            ./app || {
                                echo "❌ API build failed! Checking system resources..."
                                df -h
                                docker system df
                                echo "=== Last 50 lines of docker logs ==="
                                docker logs $(docker ps -lq) --tail=50 || true
                                exit 1
                            }
                        
                        echo "✅ API image built successfully!"
                        
                        echo "=== Building Frontend image ==="
                        echo "Frontend Dockerfile content:"
                        cat ./frontend/Dockerfile || echo "No Dockerfile found in frontend"
                        
                        docker build \
                            --no-cache \
                            --progress=plain \
                            --network=host \
                            -t ${ECR_REGISTRY}/${ECR_FRONTEND_REPO}:${IMAGE_TAG} \
                            -t ${ECR_REGISTRY}/${ECR_FRONTEND_REPO}:latest \
                            ./frontend || {
                                echo "❌ Frontend build failed!"
                                docker system df
                                exit 1
                            }
                        
                        echo "✅ Frontend image built successfully!"
                        
                        echo "=== Final Image List ==="
                        docker images | head -10
                        docker images | grep ${ECR_REGISTRY} || echo "No ECR images found"
                        
                        echo "=== System Status After Build ==="
                        docker system df
                        '''
                    }
                }
            }
        }
        
        stage('Test Images') {
            steps {
                script {
                    echo "🧪 Testing built images..."
                    sh '''
                    echo "Testing API image startup..."
                    
                    # Test API image
                    docker run -d --name test-api -p 5001:5000 ${ECR_REGISTRY}/${ECR_API_REPO}:${IMAGE_TAG} || {
                        echo "Failed to start API container"
                        exit 1
                    }
                    
                    # Wait for container to start
                    echo "Waiting for API container to start..."
                    sleep 15
                    
                    # Check if container is running
                    if docker ps | grep test-api; then
                        echo "✅ API container started successfully"
                        docker logs test-api --tail=20
                    else
                        echo "❌ API container failed to start"
                        docker logs test-api || true
                        docker ps -a | grep test-api
                        exit 1
                    fi
                    
                    # Cleanup test container
                    docker stop test-api || true
                    docker rm test-api || true
                    
                    echo "✅ Image tests passed"
                    '''
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
                    docker-compose down --remove-orphans || echo "No containers to stop"
                    docker-compose -f docker-compose-deploy.yml down --remove-orphans || echo "No deploy containers to stop"
                    
                    echo "Creating deployment compose file..."
                    cat > docker-compose-deploy.yml << 'EOF'
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
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "--silent"]
      timeout: 20s
      retries: 10
      interval: 10s
      start_period: 30s
    restart: unless-stopped

  api:
    image: ${ECR_REGISTRY}/${ECR_API_REPO}:${IMAGE_TAG}
    ports:
      - "5000:5000"
    depends_on:
      - mysql
    environment:
      - DATABASE_URL=mysql://user:userpassword@mysql:3306/url_shortener
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health", "||", "curl", "-f", "http://localhost:5000"]
      timeout: 10s
      retries: 5
      interval: 30s
      start_period: 40s
    restart: unless-stopped

  frontend:
    image: ${ECR_REGISTRY}/${ECR_FRONTEND_REPO}:${IMAGE_TAG}
    ports:
      - "3000:3000"
    depends_on:
      - api
    environment:
      - REACT_APP_API_URL=http://localhost:5000
    restart: unless-stopped

volumes:
  mysql_data:
EOF
                    
                    echo "Starting services with new images..."
                    docker-compose -f docker-compose-deploy.yml up -d
                    
                    echo "Waiting for services to be ready..."
                    sleep 30
                    
                    echo "=== Container Status ==="
                    docker-compose -f docker-compose-deploy.yml ps
                    
                    echo "=== Container Health ==="
                    docker-compose -f docker-compose-deploy.yml ps -a
                    
                    echo "=== Container Logs (last 20 lines each) ==="
                    docker-compose -f docker-compose-deploy.yml logs --tail=20
                    
                    echo "✅ Local deployment complete!"
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
                    echo "☸️ Deploying to Kubernetes..."
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
                    
                    echo "Updating deployments with new images..."
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
                    
                    echo "✅ Kubernetes deployment complete!"
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
                    if docker ps | grep -q "deploy.*api\|deploy.*frontend\|deploy.*mysql"; then
                        echo "✅ Local containers are running"
                        
                        # Test API endpoints with retries
                        echo "Testing API endpoints..."
                        for i in {1..5}; do
                            if curl -f -s http://localhost:5000/health; then
                                echo "✅ API health check passed"
                                break
                            elif curl -f -s http://localhost:5000; then
                                echo "✅ API is responding"
                                break
                            else
                                echo "Attempt $i failed, retrying in 10s..."
                                sleep 10
                            fi
                            
                            if [ $i -eq 5 ]; then
                                echo "⚠️ API health check failed after 5 attempts"
                            fi
                        done
                        
                        echo "Testing Frontend..."
                        if curl -f -s http://localhost:3000 > /dev/null; then
                            echo "✅ Frontend is responding"
                        else
                            echo "⚠️ Frontend not responding (this can be normal initially)"
                        fi
                    else
                        echo "⚠️ No local containers found"
                    fi
                    
                    echo "=== Docker Status ==="
                    docker ps --format "table {{.Names}}\\t{{.Status}}\\t{{.Ports}}"
                    
                    echo "=== Resource Usage ==="
                    docker system df
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
                
                # Clean up old/dangling images but keep recent ones
                docker image prune -f --filter "until=48h" || true
                
                # Remove stopped containers
                docker container prune -f || true
                
                echo "Keeping newly built images for running containers"
                
                echo "=== Final System Status ==="
                docker system df
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
            • Health Check: http://localhost:5000/health
            
            🚀 Next push will automatically replace these containers!
            """
        }
        failure {
            echo """
            ❌ Deployment failed! 
            
            🔍 Common issues to check:
            • Docker build timeout (check Dockerfile optimization)
            • Network connectivity issues
            • Dependency conflicts in requirements.txt
            • Insufficient disk space
            • Jenkinsfile syntax errors
            
            Check the logs above for details.
            """
        }
        unstable {
            echo "⚠️ Build completed with warnings. Check logs for details."
        }
    }
}