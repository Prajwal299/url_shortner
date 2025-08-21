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
                    docker buildx version && echo "✅ Docker Buildx available" || echo "❌ Docker Buildx not found"
                    kubectl version --client && echo "✅ kubectl available" || echo "❌ kubectl not found"
                    aws --version && echo "✅ AWS CLI available" || echo "❌ AWS CLI not found"
                    unzip -v && echo "✅ unzip available" || echo "❌ unzip not found"
                    echo "=== Jenkins User Check ==="
                    whoami
                    groups
                    echo "=== Disk Space ==="
                    df -h
                    '''
                }
            }
        }
        stage('Build Application Images') {
            steps {
                script {
                    echo "🔨 Building Docker images..."
                    timeout(time: 12, unit: 'MINUTES') {
                        sh '''
                        set -e
                        echo "=== Building API image ==="
                        docker build -t $ECR_REGISTRY/$ECR_API_REPO:$IMAGE_TAG -t $ECR_REGISTRY/$ECR_API_REPO:latest ./app
                        echo "=== Building Frontend image ==="
                        docker build -t $ECR_REGISTRY/$ECR_FRONTEND_REPO:$IMAGE_TAG -t $ECR_REGISTRY/$ECR_FRONTEND_REPO:latest ./frontend
                        echo "✅ Images built successfully"
                        docker images | grep $ECR_REGISTRY
                        '''
                    }
                }
            }
        }
        stage('Push to ECR') {
            steps {
                withCredentials([aws(credentialsId: 'aws-creds', accessKeyVariable: 'AWS_ACCESS_KEY_ID', secretKeyVariable: 'AWS_SECRET_ACCESS_KEY')]) {
                    script {
                        echo "📤 Pushing images to ECR..."
                        sh '''
                        aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY
                        docker push $ECR_REGISTRY/$ECR_API_REPO:$IMAGE_TAG
                        docker push $ECR_REGISTRY/$ECR_API_REPO:latest
                        docker push $ECR_REGISTRY/$ECR_FRONTEND_REPO:$IMAGE_TAG
                        docker push $ECR_REGISTRY/$ECR_FRONTEND_REPO:latest
                        echo "✅ Images pushed to ECR"
                        '''
                    }
                }
            }
        }
        stage('Deploy to Kubernetes') {
            steps {
                withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')]) {
                    script {
                        echo "☸️ Deploying to Kubernetes..."
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
kubectl --kubeconfig="$KUBECONFIG_FILE" apply -f k8s/namespace.yaml
kubectl --kubeconfig="$KUBECONFIG_FILE" apply -f k8s/mysql-deployment.yaml
kubectl --kubeconfig="$KUBECONFIG_FILE" set image deployment/api api="$ECR_REGISTRY/$ECR_API_REPO:$IMAGE_TAG" -n "$NAMESPACE" --record
kubectl --kubeconfig="$KUBECONFIG_FILE" set image deployment/frontend frontend="$ECR_REGISTRY/$ECR_FRONTEND_REPO:$IMAGE_TAG" -n "$NAMESPACE" --record
kubectl --kubeconfig="$KUBECONFIG_FILE" apply -f k8s/api-deployment.yaml
kubectl --kubeconfig="$KUBECONFIG_FILE" apply -f k8s/frontend-deployment.yaml
echo "Waiting for rollouts..."
kubectl --kubeconfig="$KUBECONFIG_FILE" rollout status deployment/api -n "$NAMESPACE" --timeout=300s
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
            echo "🧹 Cleaning up..."
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
            • Built new images with tag: $BUILD_NUMBER
            • Replaced old pods with new ones
            • Application is running with latest code
            🔗 Access your application:
            • Frontend: http://3.110.114.163:3000
            • API: http://3.110.114.163:5000
            """
        }
        failure {
            echo """
            ❌ Deployment failed! 
            🔍 Common issues to check:
            • Docker build issues (check Dockerfile, network)
            • AWS ECR authentication
            • Kubernetes connectivity or manifest errors
            • Insufficient resources on Jenkins EC2
            Check the logs above for details.
            """
        }
    }
}