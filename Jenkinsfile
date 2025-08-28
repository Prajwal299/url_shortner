
// pipeline {
//     agent any

//     environment {
//         DEPLOY_SERVER_IP = "3.110.114.163"
//         REPO_URL = "https://github.com/Prajwal299/url_shortner.git"
//         APP_DIR = "/home/ubuntu/url_shortner"
//     }

//     stages {
//         stage('Checkout') {
//             steps {
//                 echo "Checking out code from repository"
//                 checkout scm
//             }
//         }

//         stage('Deploy to EC2') {
//             steps {
//                 echo "Deploying to EC2 instance: ${DEPLOY_SERVER_IP}"
//                 sshagent(credentials: ['ec2-ssh-key']) {
//                     sh """
//                         ssh -o StrictHostKeyChecking=no ubuntu@${DEPLOY_SERVER_IP} << 'EOF'
//                             set -e
//                             echo "--- Connected to deployment server ---"
//                             if [ ! -d "${APP_DIR}" ]; then
//                                 echo "Cloning repository..."
//                                 git clone ${REPO_URL} ${APP_DIR}
//                             else
//                                 echo "Repository exists. Pulling latest changes..."
//                                 cd ${APP_DIR}
//                                 git fetch origin
//                                 git reset --hard origin/main
//                             fi
//                             cd ${APP_DIR}
//                             echo "--- Checking disk space ---"
//                             df -h
//                             echo "--- Stopping and removing existing containers ---"
//                             docker-compose down || true
//                             echo "--- Building and starting containers ---"
//                             docker-compose build --no-cache
//                             docker-compose up -d
//                             echo "--- Cleaning up old images ---"
//                             docker image prune -f --filter "until=48h"
//                             echo "--- Deployment successful ---"
//                             docker ps -a
//                         EOF
//                     """
//                 }
//             }
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
                            echo "--- Connected to deployment server ---"

                            if [ ! -d "${APP_DIR}" ]; then
                                echo "Cloning repository..."
                                git clone ${REPO_URL} ${APP_DIR} || true
                            else
                                echo "Repository exists. Pulling latest changes..."
                                cd ${APP_DIR}
                                git fetch origin || true
                                git reset --hard origin/main || true
                            fi

                            cd ${APP_DIR}

                            echo "--- Checking disk space ---"
                            df -h || true

                            echo "--- Stopping and removing existing containers ---"
                            docker-compose down || true

                            echo "--- Building and starting containers ---"
                            docker-compose build --no-cache || true
                            docker-compose up -d || true

                            echo "--- Cleaning up old images ---"
                            docker image prune -f --filter "until=48h" || true

                            echo "--- Deployment successful ---"
                            docker ps -a || true
                        EOF
                    """
                }
            }
        }
    }

    post {
        success {
            echo '✅ Build and Deployment Successful!'
        }
        failure {
            echo '❌ Build Failed – check logs above.'
        }
    }
}
