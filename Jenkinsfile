pipeline {
    agent  any
    
    environment {
        DOCKER_REGISTRY = '934556830376.dkr.ecr.ap-south-1.amazonaws.com'
        API_IMAGE = "${DOCKER_REGISTRY}/url-shortener-api"
        FRONTEND_IMAGE = "${DOCKER_REGISTRY}/url-shortener-frontend"
        KUBECONFIG = '/var/lib/jenkins/.kube/config'
        ANSIBLE_HOST_KEY_CHECKING = 'False'
        PATH = "/usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin:/sbin"
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('Build API Image') {
            steps {
                script {
                    // Verify Docker is available
                    sh 'which docker || echo "Docker not found in PATH"'
                    sh 'docker --version || echo "Docker command failed"'
                    
                    dir('app') {
                        sh """
                            sudo docker build -t ${API_IMAGE}:${BUILD_NUMBER} .
                            sudo docker tag ${API_IMAGE}:${BUILD_NUMBER} ${API_IMAGE}:latest
                        """
                    }
                }
            }
        }
        
        stage('Build Frontend Image') {
            steps {
                script {
                    dir('frontend') {
                        sh """
                            sudo docker build -t ${FRONTEND_IMAGE}:${BUILD_NUMBER} .
                            sudo docker tag ${FRONTEND_IMAGE}:${BUILD_NUMBER} ${FRONTEND_IMAGE}:latest
                        """
                    }
                }
            }
        }
        
        stage('Push Images to ECR') {
            steps {
                script {
                    sh '''
                        aws ecr get-login-password --region ap-south-1 | sudo docker login --username AWS --password-stdin ${DOCKER_REGISTRY}
                        sudo docker push ${API_IMAGE}:${BUILD_NUMBER}
                        sudo docker push ${API_IMAGE}:latest
                        sudo docker push ${FRONTEND_IMAGE}:${BUILD_NUMBER}
                        sudo docker push ${FRONTEND_IMAGE}:latest
                    '''
                }
            }
        }
        
        stage('Update Kubernetes Manifests') {
            steps {
                script {
                    sh """
                        # Update API deployment with new image tag
                        sed -i 's|${API_IMAGE}:.*|${API_IMAGE}:${BUILD_NUMBER}|g' k8s/api-deployment.yaml
                        
                        # Update Frontend deployment with new image tag
                        sed -i 's|${FRONTEND_IMAGE}:.*|${FRONTEND_IMAGE}:${BUILD_NUMBER}|g' k8s/frontend-deployment.yaml
                    """
                }
            }
        }
        
        stage('Deploy to Kubernetes') {
            steps {
                script {
                    sh """
                        # Apply namespace first
                        kubectl apply -f k8s/namespace.yaml
                        
                        # Apply all other manifests
                        kubectl apply -f k8s/mysql-deployment.yaml
                        kubectl apply -f k8s/api-deployment.yaml
                        kubectl apply -f k8s/frontend-deployment.yaml
                        kubectl apply -f k8s/hpa.yaml
                        
                        # Wait for deployments to be ready
                        kubectl rollout status deployment/url-shortener-api -n url-shortener --timeout=300s
                        kubectl rollout status deployment/url-shortener-frontend -n url-shortener --timeout=300s
                        kubectl rollout status deployment/mysql -n url-shortener --timeout=300s
                    """
                }
            }
        }
        
        stage('Verify Deployment') {
            steps {
                script {
                    sh """
                        # Check pod status
                        kubectl get pods -n url-shortener
                        
                        # Check services
                        kubectl get services -n url-shortener
                        
                        # Get deployment status
                        kubectl get deployments -n url-shortener
                    """
                }
            }
        }
        
        stage('Cleanup Old Images') {
            steps {
                script {
                    sh '''
                        # Keep only last 5 builds worth of images
                        sudo docker images ${API_IMAGE} --format "table {{.Tag}}" | tail -n +2 | sort -nr | tail -n +6 | xargs -I {} sudo docker rmi ${API_IMAGE}:{} || true
                        sudo docker images ${FRONTEND_IMAGE} --format "table {{.Tag}}" | tail -n +2 | sort -nr | tail -n +6 | xargs -I {} sudo docker rmi ${FRONTEND_IMAGE}:{} || true
                        
                        # Clean up dangling images
                        sudo docker image prune -f
                    '''
                }
            }
        }
    }
    
    post {
        always {
            cleanWs()
        }
        success {
            echo 'Deployment successful!'
            // You can add notification here (Slack, email, etc.)
        }
        failure {
            echo 'Deployment failed!'
            // Add failure notification here
        }
    }
}