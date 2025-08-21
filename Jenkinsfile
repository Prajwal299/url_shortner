pipeline {
    agent any
    environment {
        IMAGE_TAG = "${BUILD_NUMBER}"
        NAMESPACE = 'url-shortener'
        REGISTRY = 'http://3.110.114.163:5000'
        API_IMAGE = "${REGISTRY}/url-shortener-api"
        FRONTEND_IMAGE = "${REGISTRY}/url-shortener-frontend"
        KUBECONFIG = '/var/lib/jenkins/.kube/config'
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
                    kubectl --kubeconfig=$KUBECONFIG version --client && echo "✅ kubectl available" || echo "❌ kubectl not found"
                    echo "=== Registry Check ==="
                    curl -s http://3.110.114.163:5000/v2/ && echo "✅ Registry available" || echo "❌ Registry not accessible"
                    echo "=== Jenkins User Check ==="
                    whoami
                    groups
                    echo "=== Disk Space ==="
                    df -h
                    echo "=== Kubernetes Config ==="
                    ls -l $KUBECONFIG || echo "❌ kubeconfig not found"
                    '''
                }
            }
        }
        stage('Build Application Images') {
            steps {
                script {
                    echo "🔨 Building Docker images..."
                    timeout(time: 15, unit: 'MINUTES') {
                        sh '''
                        set -e
                        echo "=== Cleaning up old images ==="
                        docker image prune -f --filter "until=48h" || true
                        echo "=== Building API image ==="
                        docker build -t ${API_IMAGE##http://}:$IMAGE_TAG -t ${API_IMAGE##http://}:latest ./app || {
                            echo "❌ API build failed!"
                            df -h
                            docker system df
                            exit 1
                        }
                        echo "=== Building Frontend image ==="
                        docker build -t ${FRONTEND_IMAGE##http://}:$IMAGE_TAG -t ${FRONTEND_IMAGE##http://}:latest ./frontend || {
                            echo "❌ Frontend build failed!"
                            df -h
                            docker system df
                            exit 1
                        }
                        echo "✅ Images built successfully"
                        docker images | grep ${REGISTRY##http://}
                        '''
                    }
                }
            }
        }
        stage('Push to Local Registry') {
            steps {
                script {
                    echo "📤 Pushing images to local registry..."
                    sh '''
                    set -e
                    docker push ${API_IMAGE##http://}:$IMAGE_TAG || {
                        echo "❌ Failed to push API image!"
                        curl -s http://3.110.114.163:5000/v2/ || echo "❌ Registry not accessible"
                        exit 1
                    }
                    docker push ${API_IMAGE##http://}:latest
                    docker push ${FRONTEND_IMAGE##http://}:$IMAGE_TAG || {
                        echo "❌ Failed to push frontend image!"
                        curl -s http://3.110.114.163:5000/v2/ || echo "❌ Registry not accessible"
                        exit 1
                    }
                    docker push ${FRONTEND_IMAGE##http://}:latest
                    echo "✅ Images pushed to local registry"
                    '''
                }
            }
        }
        stage('Deploy to Kubernetes') {
            steps {
                script {
                    echo "☸️ Deploying to Kubernetes..."
                    sh '''
                    set -e
                    if [ ! -f "$KUBECONFIG" ]; then
                        echo "❌ kubeconfig not found at $KUBECONFIG"
                        exit 1
                    fi
                    echo "=== Cleaning up old pods ==="
                    kubectl --kubeconfig=$KUBECONFIG delete pod -n $NAMESPACE -l app=api --force --grace-period=0 || true
                    kubectl --kubeconfig=$KUBECONFIG delete pod -n $NAMESPACE -l app=frontend --force --grace-period=0 || true
                    echo "=== Applying manifests ==="
                    kubectl --kubeconfig=$KUBECONFIG apply -f k8s/namespace.yaml
                    kubectl --kubeconfig=$KUBECONFIG apply -f k8s/mysql-deployment.yaml
                    kubectl --kubeconfig=$KUBECONFIG set image deployment/api api=${API_IMAGE##http://}:$IMAGE_TAG -n $NAMESPACE --record
                    kubectl --kubeconfig=$KUBECONFIG set image deployment/frontend frontend=${FRONTEND_IMAGE##http://}:$IMAGE_TAG -n $NAMESPACE --record
                    kubectl --kubeconfig=$KUBECONFIG apply -f k8s/api-deployment.yaml
                    kubectl --kubeconfig=$KUBECONFIG apply -f k8s/frontend-deployment.yaml
                    echo "=== Waiting for rollouts ==="
                    kubectl --kubeconfig=$KUBECONFIG rollout status deployment/api -n $NAMESPACE --timeout=300s
                    kubectl --kubeconfig=$KUBECONFIG rollout status deployment/frontend -n $NAMESPACE --timeout=300s
                    echo "✅ Deployment completed"
                    kubectl --kubeconfig=$KUBECONFIG get pods -n $NAMESPACE
                    '''
                }
            }
        }
        stage('Verify Deployment') {
            steps {
                script {
                    echo "🏥 Verifying deployment..."
                    sh '''
                    if [ ! -f "$KUBECONFIG" ]; then
                        echo "❌ kubeconfig not found at $KUBECONFIG"
                        exit 1
                    fi
                    echo "=== Deployment Status ==="
                    kubectl --kubeconfig=$KUBECONFIG get deployments -n $NAMESPACE
                    echo "=== Pod Status ==="
                    kubectl --kubeconfig=$KUBECONFIG get pods -n $NAMESPACE
                    echo "=== Service Status ==="
                    kubectl --kubeconfig=$KUBECONFIG get services -n $NAMESPACE
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
            • Built new images with tag: $IMAGE_TAG
            • Replaced old pods with new ones
            • Application is running with latest code
            🔗 Access your application:
            • Frontend: http://3.110.114.163:30300
            • API: http://3.110.114.163:30500
            """
        }
        failure {
            echo """
            ❌ Deployment failed! 
            🔍 Common issues to check:
            • Docker build issues (check Dockerfile, network)
            • Local registry connectivity (http://3.110.114.163:5000)
            • Kubernetes connectivity or manifest errors
            • Missing kubeconfig at $KUBECONFIG
            Check the logs above for details.
            """
        }
    }
}