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
    stages {
        stage('Checkout') {
            steps {
                git branch: 'main', credentialsId: 'git', url: 'git@github.com:Prajwal299/url_shortner.git'
            }
        }
        stage('Build Images') {
            steps {
                script {
                    sh "docker build -t ${ECR_REGISTRY}/${ECR_API_REPO}:${IMAGE_TAG} ./app"
                    sh "docker tag ${ECR_REGISTRY}/${ECR_API_REPO}:${IMAGE_TAG} ${ECR_REGISTRY}/${ECR_API_REPO}:latest"
                    sh "docker build -t ${ECR_REGISTRY}/${ECR_FRONTEND_REPO}:${IMAGE_TAG} ./frontend"
                    sh "docker tag ${ECR_REGISTRY}/${ECR_FRONTEND_REPO}:${IMAGE_TAG} ${ECR_REGISTRY}/${ECR_FRONTEND_REPO}:latest"
                }
            }
        }
        stage('Push to ECR') {
            steps {
                withCredentials([aws(credentialsId: 'aws-creds', accessKeyVariable: 'AWS_ACCESS_KEY_ID', secretKeyVariable: 'AWS_SECRET_ACCESS_KEY')]) {
                    script {
                        sh """
                        aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}
                        docker push ${ECR_REGISTRY}/${ECR_API_REPO}:${IMAGE_TAG}
                        docker push ${ECR_REGISTRY}/${ECR_API_REPO}:latest
                        docker push ${ECR_REGISTRY}/${ECR_FRONTEND_REPO}:${IMAGE_TAG}
                        docker push ${ECR_REGISTRY}/${ECR_FRONTEND_REPO}:latest
                        """
                    }
                }
            }
        }
        stage('Deploy to Kubernetes') {
            steps {
                withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')]) {
                    script {
                        sh '''
                        cat > deploy.sh << 'EOF'
#!/bin/bash
set -e

KUBECONFIG_FILE="$1"
NAMESPACE="$2"
IMAGE_TAG="$3"
ECR_REGISTRY="$4"
ECR_API_REPO="$5"
ECR_FRONTEND_REPO="$6"

echo "Starting deployment with image tag: $IMAGE_TAG"

# Apply namespace
kubectl --kubeconfig="$KUBECONFIG_FILE" apply -f k8s/namespace.yaml

# Apply MySQL deployment
kubectl --kubeconfig="$KUBECONFIG_FILE" apply -f k8s/mysql-deployment.yaml

# Update images
kubectl --kubeconfig="$KUBECONFIG_FILE" set image deployment/api api="$ECR_REGISTRY/$ECR_API_REPO:$IMAGE_TAG" -n "$NAMESPACE" --record
kubectl --kubeconfig="$KUBECONFIG_FILE" set image deployment/frontend frontend="$ECR_REGISTRY/$ECR_FRONTEND_REPO:$IMAGE_TAG" -n "$NAMESPACE" --record

# Apply remaining manifests
kubectl --kubeconfig="$KUBECONFIG_FILE" apply -f k8s/api-deployment.yaml
kubectl --kubeconfig="$KUBECONFIG_FILE" apply -f k8s/frontend-deployment.yaml

# Wait for rollout
echo "Waiting for API deployment rollout..."
kubectl --kubeconfig="$KUBECONFIG_FILE" rollout status deployment/api -n "$NAMESPACE" --timeout=300s
echo "Waiting for Frontend deployment rollout..."
kubectl --kubeconfig="$KUBECONFIG_FILE" rollout status deployment/frontend -n "$NAMESPACE" --timeout=300s

echo "Deployment completed successfully!"
kubectl --kubeconfig="$KUBECONFIG_FILE" get pods -n "$NAMESPACE"
EOF

                        chmod +x deploy.sh
                        ./deploy.sh "$KUBECONFIG" "$NAMESPACE" "$IMAGE_TAG" "$ECR_REGISTRY" "$ECR_API_REPO" "$ECR_FRONTEND_REPO"
                        '''
                    }
                }
            }
        }
        stage('Verify Deployment') {
            steps {
                withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')]) {
                    sh '''
                    echo "=== Deployment Status ==="
                    kubectl --kubeconfig="$KUBECONFIG" get deployments -n url-shortener
                    echo "=== Pod Status ==="
                    kubectl --kubeconfig="$KUBECONFIG" get pods -n url-shortener
                    echo "=== Service Status ==="
                    kubectl --kubeconfig="$KUBECONFIG" get services -n url-shortener
                    '''
                }
            }
        }
    }
    post {
        always {
            sh '''
            docker rmi ${ECR_REGISTRY}/${ECR_API_REPO}:${IMAGE_TAG} || true
            docker rmi ${ECR_REGISTRY}/${ECR_API_REPO}:latest || true
            docker rmi ${ECR_REGISTRY}/${ECR_FRONTEND_REPO}:${IMAGE_TAG} || true
            docker rmi ${ECR_REGISTRY}/${ECR_FRONTEND_REPO}:latest || true
            '''
        }
        success {
            echo "Deployment completed successfully!"
        }
        failure {
            echo "Deployment failed!"
        }
    }
}