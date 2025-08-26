pipeline {
    agent any

    environment {
        AWS_DEFAULT_REGION = "ap-south-1"   // change if required
        APP_NAME = "url-shortener"
    }

    stages {
        stage('Checkout') {
            steps {
                git branch: 'main',
                    url: 'https://github.com/Prajwal299/url_shortner.git'
            }
        }

        stage('Install Dependencies') {
            steps {
                dir('app') {
                    sh 'pip3 install -r requirements.txt'
                }
            }
        }

        stage('Build Docker Images') {
            steps {
                script {
                    sh 'docker build -t ${APP_NAME}-api ./app'
                    sh 'docker build -t ${APP_NAME}-frontend ./frontend'
                }
            }
        }

        stage('Run Docker Compose') {
            steps {
                sh 'docker-compose up -d --build'
            }
        }

        stage('Deploy to Kubernetes') {
            steps {
                withAWS(region: "${AWS_DEFAULT_REGION}", credentials: 'aws-creds') {
                    sh '''
                        aws eks update-kubeconfig --name my-cluster
                        kubectl apply -f k8s/namespace.yaml
                        kubectl apply -f k8s/mysql-deployment.yaml
                        kubectl apply -f k8s/api-deployment.yaml
                        kubectl apply -f k8s/frontend-deployment.yaml
                        kubectl apply -f k8s/hpa.yaml
                    '''
                }
            }
        }
    }

    post {
        always {
            sh 'docker-compose down || true'
        }
        success {
            echo '✅ Deployment Successful!'
        }
        failure {
            echo '❌ Deployment Failed. Please check logs.'
        }
    }
}
