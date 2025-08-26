pipeline {
    agent any
    environment {
        DEPLOY_SERVER_IP = "3.110.114.163"
        API_IMAGE_NAME = "url-shortener-api"
        FRONTEND_IMAGE_NAME = "url-shortener-frontend"
        MYSQL_IMAGE_NAME = "mysql:8.0"
        API_CONTAINER_NAME = "url_shortner_api_1"
        FRONTEND_CONTAINER_NAME = "url_shortner_frontend_1"
        MYSQL_CONTAINER_NAME = "url_shortner_mysql_1"
        REPO_URL = "https://github.com/Prajwal299/url_shortner.git"
        APP_DIR = "/home/ubuntu/url_shortner"
    }
    stages {
        stage('Deploy to EC2') {
            steps {
                echo "Deploying to EC2 instance: ${DEPLOY_SERVER_IP}"
                sshagent(credentials: ['ec2-ssh-key']) {
                    sh """
                        ssh -o StrictHostKeyChecking=no ubuntu@\${DEPLOY_SERVER_IP} '
                            echo "--- Connected to deployment server. Preparing workspace... ---"
                            if [ ! -d "\${APP_DIR}" ]; then
                                echo "Cloning repository..."
                                git clone \${REPO_URL} \${APP_DIR}
                            else
                                echo "Repository exists. Pulling latest changes..."
                                cd \${APP_DIR}
                                git pull
                            fi

                            cd \${APP_DIR}

                            echo "--- Building API Docker image... ---"
                            docker build -t \${API_IMAGE_NAME}:\${BUILD_NUMBER} -t \${API_IMAGE_NAME}:latest ./app

                            echo "--- Building Frontend Docker image... ---"
                            docker build -t \${FRONTEND_IMAGE_NAME}:\${BUILD_NUMBER} -t \${FRONTEND_IMAGE_NAME}:latest ./frontend

                            echo "--- Stopping and removing old containers... ---"
                            docker stop \${API_CONTAINER_NAME} || true
                            docker rm \${API_CONTAINER_NAME} || true
                            docker stop \${FRONTEND_CONTAINER_NAME} || true
                            docker rm \${FRONTEND_CONTAINER_NAME} || true
                            docker stop \${MYSQL_CONTAINER_NAME} || true
                            docker rm \${MYSQL_CONTAINER_NAME} || true

                            echo "--- Starting new containers... ---"
                            docker run -d --name \${API_CONTAINER_NAME} -p 5001:5000 --network url_shortner_default \${API_IMAGE_NAME}:latest
                            docker run -d --name \${FRONTEND_CONTAINER_NAME} -p 80:80 --network url_shortner_default \${FRONTEND_IMAGE_NAME}:latest
                            docker-compose up -d

                            echo "--- Cleaning up old images... ---"
                            docker image prune -f --filter "until=48h"

                            echo "--- Deployment successful! ---"
                            docker ps -a
                        '
                    """
                }
            }
        }
    }
    post {
        always {
            echo "Pipeline finished."
            sh '''
            echo "🧹 Cleaning up on Jenkins node..."
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
            • Built new API, frontend, and MySQL containers with tag: ${BUILD_NUMBER}
            • Replaced old containers on ${DEPLOY_SERVER_IP}
            • Application is running with latest code
            🔗 Access your application:
            • Frontend: http://${DEPLOY_SERVER_IP}
            • API: http://${DEPLOY_SERVER_IP}:5001
            • MySQL: ${DEPLOY_SERVER_IP}:3306
            """
        }
        failure {
            echo """
            ❌ Deployment failed! 
            🔍 Common issues to check:
            • SSH access to ${DEPLOY_SERVER_IP}
            • Docker build issues (check Dockerfile, disk space)
            • Port conflicts on ${DEPLOY_SERVER_IP} (ports 5001, 80, 3306)
            • Repository access or git pull issues
            • docker-compose.yml configuration
            Check the logs above for details.
            """
        }
    }
}