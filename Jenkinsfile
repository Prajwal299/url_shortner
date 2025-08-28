// pipeline {
//     agent any
//     environment {
//         MASTER_NODE_IP = "3.110.114.163"
//         WORKER_NODE_1 = "15.206.203.245"
//         WORKER_NODE_2 = "13.204.79.139"
//         API_IMAGE_NAME = "url-shortener-api"
//         FRONTEND_IMAGE_NAME = "url-shortener-frontend"
//         MYSQL_IMAGE_NAME = "mysql:8.0"
//         REPO_URL = "https://github.com/Prajwal299/url_shortner.git"
//         APP_DIR = "/home/ubuntu/url_shortner"
//         DOCKER_REGISTRY = "your-dockerhub-username" // Update this
//     }
//     stages {
//         stage('Checkout') {
//             steps {
//                 echo "Checking out code from repository"
//                 checkout scm
//             }
//         }
        
//         stage('Build and Push Images') {
//             steps {
//                 echo "Building and pushing Docker images"
//                 sshagent(credentials: ['ec2-ssh-key']) {
//                     sh """
//                         ssh -o StrictHostKeyChecking=no ubuntu@\${MASTER_NODE_IP} '
//                             set -e
//                             echo "--- Connected to Kubernetes master node ---"
                            
//                             if [ ! -d "\${APP_DIR}" ]; then
//                                 echo "Cloning repository..."
//                                 git clone \${REPO_URL} \${APP_DIR}
//                             else
//                                 echo "Repository exists. Pulling latest changes..."
//                                 cd \${APP_DIR}
//                                 git pull origin main
//                             fi

//                             cd \${APP_DIR}

//                             echo "--- Building API Docker image ---"
//                             docker build -t \${API_IMAGE_NAME}:\${BUILD_NUMBER} -t \${API_IMAGE_NAME}:latest ./app
                            
//                             echo "--- Building Frontend Docker image ---"
//                             docker build -t \${FRONTEND_IMAGE_NAME}:\${BUILD_NUMBER} -t \${FRONTEND_IMAGE_NAME}:latest ./frontend

//                             # Tag images for registry (optional - if using private registry)
//                             # docker tag \${API_IMAGE_NAME}:latest \${DOCKER_REGISTRY}/\${API_IMAGE_NAME}:latest
//                             # docker tag \${FRONTEND_IMAGE_NAME}:latest \${DOCKER_REGISTRY}/\${FRONTEND_IMAGE_NAME}:latest
                            
//                             # Push to registry (uncomment if using registry)
//                             # docker push \${DOCKER_REGISTRY}/\${API_IMAGE_NAME}:latest
//                             # docker push \${DOCKER_REGISTRY}/\${FRONTEND_IMAGE_NAME}:latest
//                         '
//                     """
//                 }
//             }
//         }
        
//         stage('Deploy to Kubernetes') {
//             steps {
//                 echo "Deploying to Kubernetes cluster"
//                 sshagent(credentials: ['ec2-ssh-key']) {
//                     sh """
//                         ssh -o StrictHostKeyChecking=no ubuntu@\${MASTER_NODE_IP} '
//                             set -e
//                             cd \${APP_DIR}
                            
//                             echo "--- Checking Kubernetes cluster status ---"
//                             kubectl get nodes
                            
//                             echo "--- Creating namespace if not exists ---"
//                             kubectl apply -f k8s/namespace.yaml
                            
//                             echo "--- Deploying MySQL ---"
//                             kubectl apply -f k8s/mysql-deployment.yaml
                            
//                             echo "--- Waiting for MySQL to be ready ---"
//                             kubectl wait --for=condition=ready pod -l app=mysql --timeout=300s -n url-shortener
                            
//                             echo "--- Deploying API ---"
//                             # Update image tag in deployment
//                             sed -i "s|image: url-shortener-api:latest|image: url-shortener-api:${BUILD_NUMBER}|g" k8s/api-deployment.yaml
//                             kubectl apply -f k8s/api-deployment.yaml
                            
//                             echo "--- Deploying Frontend ---"
//                             # Update image tag in deployment  
//                             sed -i "s|image: url-shortener-frontend:latest|image: url-shortener-frontend:${BUILD_NUMBER}|g" k8s/frontend-deployment.yaml
//                             kubectl apply -f k8s/frontend-deployment.yaml
                            
//                             echo "--- Applying HPA ---"
//                             kubectl apply -f k8s/hpa.yaml
                            
//                             echo "--- Deploying Prometheus ---"
//                             if [ -d "k8s/prometheus" ]; then
//                                 kubectl apply -f k8s/prometheus/
//                             fi
                            
//                             echo "--- Deploying Grafana ---"
//                             if [ -d "k8s/grafana" ]; then
//                                 kubectl apply -f k8s/grafana/
//                             fi
                            
//                             echo "--- Checking deployment status ---"
//                             kubectl get pods -n url-shortener
//                             kubectl get services -n url-shortener
//                             kubectl get hpa -n url-shortener
                            
//                             echo "--- Getting service URLs ---"
//                             kubectl get service frontend-service -n url-shortener -o wide
//                         '
//                     """
//                 }
//             }
//         }
        
//         stage('Verify Deployment') {
//             steps {
//                 echo "Verifying deployment health"
//                 sshagent(credentials: ['ec2-ssh-key']) {
//                     sh """
//                         ssh -o StrictHostKeyChecking=no ubuntu@\${MASTER_NODE_IP} '
//                             echo "--- Final deployment verification ---"
//                             kubectl get all -n url-shortener
                            
//                             echo "--- Checking pod logs (last 10 lines) ---"
//                             kubectl logs --tail=10 -l app=api -n url-shortener || true
//                             kubectl logs --tail=10 -l app=frontend -n url-shortener || true
//                         '
//                     """
//                 }
//             }
//         }
//     }
    
//     post {
//         always {
//             echo "Pipeline finished."
//             sh '''
//             echo "🧹 Cleaning up on Jenkins node..."
//             docker image prune -f --filter "until=48h" || true
//             docker container prune -f || true
//             '''
//         }
//         success {
//             echo """
//             ✅ 🎉 KUBERNETES DEPLOYMENT SUCCESSFUL! 🎉 ✅
//             📋 What was deployed:
//             • API service with build number: ${BUILD_NUMBER}
//             • Frontend service with build number: ${BUILD_NUMBER}
//             • MySQL database
//             • Horizontal Pod Autoscaler (HPA)
//             • Prometheus monitoring
//             • Grafana dashboards
            
//             🔗 Access your application:
//             • Frontend: Check NodePort service on any worker node
//             • API: Internal cluster communication
//             • Grafana: Check service endpoint
//             • Prometheus: Check service endpoint
            
//             📊 Check status:
//             kubectl get all -n url-shortener
//             """
//         }
//         failure {
//             echo """
//             ❌ Deployment failed! 
//             🔍 Common issues to check:
//             • SSH access to Kubernetes nodes
//             • Kubernetes cluster status: kubectl get nodes
//             • Docker build issues in /home/ubuntu/url_shortner
//             • Kubernetes deployment files in k8s/ directory
//             • Image pull policies and availability
//             • Namespace and resource conflicts
            
//             🔧 Debug commands:
//             kubectl get pods -n url-shortener
//             kubectl describe pod <pod-name> -n url-shortener
//             kubectl logs <pod-name> -n url-shortener
//             """
//         }
//     }
// }


pipeline {
    agent any

    environment {
        DEPLOY_SERVER_IP = "3.110.114.163"
        REPO_URL = "https://github.com/Prajwal299/url_shortner.git"
        APP_DIR = "/home/ubuntu/url_shortner"
    }

    stages {
        stage('Checkout') {
            steps {
                echo "Checking out code from repository"
                checkout scm
            }
        }

        stage('Deploy to EC2') {
            steps {
                echo "Deploying to EC2 instance: ${DEPLOY_SERVER_IP}"
                sshagent(credentials: ['ec2-ssh-key']) {
                    sh """
                        ssh -o StrictHostKeyChecking=no ubuntu@${DEPLOY_SERVER_IP} << 'EOF'
                            set -e
                            echo "--- Connected to deployment server ---"
                            if [ ! -d "${APP_DIR}" ]; then
                                echo "Cloning repository..."
                                git clone ${REPO_URL} ${APP_DIR}
                            else
                                echo "Repository exists. Pulling latest changes..."
                                cd ${APP_DIR}
                                git fetch origin
                                git reset --hard origin/main
                            fi
                            cd ${APP_DIR}
                            echo "--- Checking disk space ---"
                            df -h
                            echo "--- Stopping and removing existing containers ---"
                            docker-compose down || true
                            echo "--- Building and starting containers ---"
                            docker-compose build --no-cache
                            docker-compose up -d
                            echo "--- Cleaning up old images ---"
                            docker image prune -f --filter "until=48h"
                            echo "--- Deployment successful ---"
                            docker ps -a
                        EOF
                    """
                }
            }
        }
    }
}
