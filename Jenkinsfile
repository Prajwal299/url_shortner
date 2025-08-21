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
                        # Stop any running containers
                        docker ps -q | xargs -r docker stop || true
                        
                        # Remove old images to free space
                        docker system prune -f --volumes || true
                        docker image prune -a -f --filter "until=24h" || true
                        
                        echo "=== Building API image with retries ==="
                        echo "API Dockerfile content:"
                        cat ./app/Dockerfile
                        echo ""
                        echo "API requirements.txt content:"
                        cat ./app/requirements.txt
                        echo ""
                        
                        # Build with no cache and better network settings
                        DOCKER_BUILDKIT=1 docker build \
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
                                exit 1
                            }
                        
                        echo "✅ API image built successfully!"
                        
                        echo "=== Building Frontend image ==="
                        echo "Frontend Dockerfile content:"
                        cat ./frontend/Dockerfile
                        echo ""
                        
                        DOCKER_BUILDKIT=1 docker build \
                            --no-cache \
                            --progress=plain \
                            --network=host \
                            -t ${ECR_REGISTRY}/${ECR_FRONTEND_REPO}:${IMAGE_TAG} \
                            -t ${ECR_REGISTRY}/${ECR_FRONTEND_REPO}:latest \
                            ./frontend || {
                                echo "❌ Frontend build failed!"
                                exit 1
                            }
                        
                        echo "✅ Frontend image built successfully!"
                        
                        echo "=== Final Image List ==="
                        docker images | head -10
                        docker images | grep ${ECR_REGISTRY}
                        
                        echo "=== System Status After Build ==="
                        docker system df
                        '''
                    }
                }
            }
        }