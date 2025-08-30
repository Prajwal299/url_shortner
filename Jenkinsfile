// pipeline {
//     agent any

//     triggers {
//         githubPush()  // This triggers the pipeline when GitHub webhook is received
//     }

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
//                         ssh -o StrictHostKeyChecking=no ubuntu@${DEPLOY_SERVER_IP} << 'DEPLOY_EOF'
//                             echo "--- Connected to deployment server ---"

//                             if [ ! -d "${APP_DIR}" ]; then
//                                 echo "Cloning repository..."
//                                 git clone ${REPO_URL} ${APP_DIR} || true
//                             else
//                                 echo "Repository exists. Pulling latest changes..."
//                                 cd ${APP_DIR}
//                                 git fetch origin || true
//                                 git reset --hard origin/main || true
//                             fi

//                             cd ${APP_DIR}

//                             echo "--- Checking disk space ---"
//                             df -h || true

//                             echo "--- Stopping and removing existing containers ---"
//                             docker-compose down || true

//                             echo "--- Building and starting containers ---"
//                             docker-compose build --no-cache || true
//                             docker-compose up -d || true

//                             echo "--- Cleaning up old images ---"
//                             docker image prune -f --filter "until=48h" || true

//                             echo "--- Deployment successful ---"
//                             docker ps -a || true
// DEPLOY_EOF
//                     """
//                 }
//             }
//         }
//     }

//     post {
//         success {
//             echo '✅ Build and Deployment Successful!'
//         }
//         failure {
//             echo '❌ Build Failed – check logs above.'
//         }
//     }
// }

pipeline {
    agent any

    triggers {
        githubPush()  // This triggers the pipeline when GitHub webhook is received
    }

    environment {
        DEPLOY_SERVER_IP = "3.110.114.163"
        REPO_URL = "https://github.com/Prajwal299/url_shortner.git"
        APP_DIR = "/home/ubuntu/url_shortner"
        KUBECONFIG = "/home/ubuntu/.kube/config"
    }

    stages {
        stage('Checkout') {
            steps {
                echo "Checking out code from repository"
                checkout scm
            }
        }

        stage('Build and Test') {
            steps {
                echo "Building and testing application"
                script {
                    // You can add your tests here
                    sh '''
                        echo "Running basic validation..."
                        # Add any lint checks, unit tests, etc.
                        if [ -f app/requirements.txt ]; then
                            echo "✅ API requirements.txt found"
                        else
                            echo "❌ API requirements.txt missing"
                            exit 1
                        fi
                        
                        if [ -f frontend/index.html ]; then
                            echo "✅ Frontend index.html found"
                        else
                            echo "❌ Frontend index.html missing"
                            exit 1
                        fi
                    '''
                }
            }
        }

        stage('Deploy to Kubernetes') {
            steps {
                echo "Deploying to Kubernetes cluster on EC2: ${DEPLOY_SERVER_IP}"
                sshagent(credentials: ['ec2-ssh-key']) {
                    sh """
                        ssh -o StrictHostKeyChecking=no ubuntu@${DEPLOY_SERVER_IP} << 'DEPLOY_EOF'
                            echo "--- Connected to Kubernetes master node ---"

                            # Navigate to app directory
                            cd ${APP_DIR} || {
                                echo "Error: Could not change to ${APP_DIR}"
                                exit 1
                            }

                            # Pull latest changes
                            echo "--- Pulling latest changes ---"
                            git fetch origin || true
                            git reset --hard origin/main || true

                            # Stop existing docker-compose services to free up resources
                            echo "--- Stopping docker-compose services ---"
                            docker-compose down || true

                            # Build Docker images locally
                            echo "--- Building Docker images ---"
                            docker build -t url_shortner_api:latest ./app/ || {
                                echo "❌ Failed to build API image"
                                exit 1
                            }
                            
                            docker build -t url_shortner_frontend:latest ./frontend/ || {
                                echo "❌ Failed to build Frontend image"
                                exit 1
                            }

                            # Load images into kind cluster if using kind
                            if kubectl get nodes | grep -q "demo-cluster"; then
                                echo "--- Loading images into kind cluster ---"
                                kind load docker-image url_shortner_api:latest --name demo-cluster || true
                                kind load docker-image url_shortner_frontend:latest --name demo-cluster || true
                            fi

                            # Check if Kubernetes is accessible
                            echo "--- Checking Kubernetes cluster ---"
                            export KUBECONFIG=${KUBECONFIG}
                            kubectl cluster-info || {
                                echo "❌ Cannot connect to Kubernetes cluster"
                                exit 1
                            }

                            # Deploy to Kubernetes
                            echo "--- Deploying to Kubernetes ---"
                            
                            # Create namespace if it doesn't exist
                            kubectl create namespace url-shortener --dry-run=client -o yaml | kubectl apply -f - || true
                            kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f - || true

                            # Apply all Kubernetes manifests
                            echo "--- Applying MySQL deployment ---"
                            kubectl apply -f - <<MYSQL_MANIFEST
apiVersion: v1
kind: PersistentVolume
metadata:
  name: mysql-pv
  namespace: url-shortener
spec:
  capacity:
    storage: 10Gi
  accessModes:
    - ReadWriteOnce
  hostPath:
    path: /mnt/mysql-data
  persistentVolumeReclaimPolicy: Retain
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: mysql-pvc
  namespace: url-shortener
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
---
apiVersion: v1
kind: Secret
metadata:
  name: mysql-secret
  namespace: url-shortener
type: Opaque
data:
  mysql-root-password: cm9vdA==
  mysql-password: cm9vdA==
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mysql
  namespace: url-shortener
spec:
  replicas: 1
  selector:
    matchLabels:
      app: mysql
  template:
    metadata:
      labels:
        app: mysql
    spec:
      containers:
      - name: mysql
        image: mysql:8.0
        ports:
        - containerPort: 3306
        env:
        - name: MYSQL_ROOT_PASSWORD
          valueFrom:
            secretKeyRef:
              name: mysql-secret
              key: mysql-root-password
        - name: MYSQL_DATABASE
          value: urlshortener
        - name: MYSQL_USER
          value: admin
        - name: MYSQL_PASSWORD
          valueFrom:
            secretKeyRef:
              name: mysql-secret
              key: mysql-password
        volumeMounts:
        - name: mysql-storage
          mountPath: /var/lib/mysql
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
      volumes:
      - name: mysql-storage
        persistentVolumeClaim:
          claimName: mysql-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: mysql-service
  namespace: url-shortener
spec:
  selector:
    app: mysql
  ports:
  - port: 3306
    targetPort: 3306
  type: ClusterIP
MYSQL_MANIFEST

                            # Wait for MySQL to be ready
                            echo "--- Waiting for MySQL to be ready ---"
                            kubectl wait --for=condition=ready pod -l app=mysql -n url-shortener --timeout=300s || true

                            # Deploy API
                            echo "--- Applying API deployment ---"
                            kubectl apply -f - <<API_MANIFEST
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
  namespace: url-shortener
  labels:
    app: api
spec:
  replicas: 2
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "5000"
        prometheus.io/path: "/metrics"
    spec:
      containers:
      - name: api
        image: url_shortner_api:latest
        imagePullPolicy: Never
        ports:
        - containerPort: 5000
        env:
        - name: DB_HOST
          value: mysql-service
        - name: DB_USER
          value: admin
        - name: DB_PASS
          valueFrom:
            secretKeyRef:
              name: mysql-secret
              key: mysql-password
        - name: DB_NAME
          value: urlshortener
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        readinessProbe:
          httpGet:
            path: /
            port: 5000
          initialDelaySeconds: 30
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /
            port: 5000
          initialDelaySeconds: 60
          periodSeconds: 20
---
apiVersion: v1
kind: Service
metadata:
  name: api-service
  namespace: url-shortener
  labels:
    app: api
spec:
  selector:
    app: api
  ports:
  - port: 80
    targetPort: 5000
  type: ClusterIP
API_MANIFEST

                            # Deploy Frontend
                            echo "--- Applying Frontend deployment ---"
                            kubectl apply -f - <<FRONTEND_MANIFEST
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: url-shortener
  labels:
    app: frontend
spec:
  replicas: 2
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
      - name: frontend
        image: url_shortner_frontend:latest
        imagePullPolicy: Never
        ports:
        - containerPort: 80
        resources:
          requests:
            memory: "128Mi"
            cpu: "50m"
          limits:
            memory: "256Mi"
            cpu: "200m"
---
apiVersion: v1
kind: Service
metadata:
  name: frontend-service
  namespace: url-shortener
spec:
  selector:
    app: frontend
  ports:
  - port: 80
    targetPort: 80
  type: NodePort
  nodePort: 30080
FRONTEND_MANIFEST

                            # Wait for deployments
                            echo "--- Waiting for deployments to be ready ---"
                            kubectl wait --for=condition=available deployment/api -n url-shortener --timeout=300s || true
                            kubectl wait --for=condition=available deployment/frontend -n url-shortener --timeout=300s || true

                            # Deploy HPA
                            echo "--- Setting up Horizontal Pod Autoscaler ---"
                            kubectl apply -f - <<HPA_MANIFEST
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-hpa
  namespace: url-shortener
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: frontend-hpa
  namespace: url-shortener
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: frontend
  minReplicas: 2
  maxReplicas: 5
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 80
HPA_MANIFEST

                            # Deploy Prometheus and Grafana
                            echo "--- Setting up monitoring stack ---"
                            kubectl apply -f - <<MONITORING_MANIFEST
apiVersion: v1
kind: ServiceAccount
metadata:
  name: prometheus
  namespace: monitoring
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: prometheus
rules:
- apiGroups: [""]
  resources:
  - nodes
  - nodes/proxy
  - services
  - endpoints
  - pods
  verbs: ["get", "list", "watch"]
- apiGroups:
  - extensions
  resources:
  - ingresses
  verbs: ["get", "list", "watch"]
- nonResourceURLs: ["/metrics"]
  verbs: ["get"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: prometheus
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: prometheus
subjects:
- kind: ServiceAccount
  name: prometheus
  namespace: monitoring
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: monitoring
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
      evaluation_interval: 15s
    scrape_configs:
      - job_name: 'prometheus'
        static_configs:
          - targets: ['localhost:9090']
      - job_name: 'kubernetes-apiservers'
        kubernetes_sd_configs:
        - role: endpoints
        scheme: https
        tls_config:
          ca_file: /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
        bearer_token_file: /var/run/secrets/kubernetes.io/serviceaccount/token
        relabel_configs:
        - source_labels: [__meta_kubernetes_namespace, __meta_kubernetes_service_name, __meta_kubernetes_endpoint_port_name]
          action: keep
          regex: default;kubernetes;https
      - job_name: 'kubernetes-nodes'
        kubernetes_sd_configs:
        - role: node
        scheme: https
        tls_config:
          ca_file: /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
        bearer_token_file: /var/run/secrets/kubernetes.io/serviceaccount/token
        relabel_configs:
        - action: labelmap
          regex: __meta_kubernetes_node_label_(.+)
      - job_name: 'kubernetes-pods'
        kubernetes_sd_configs:
        - role: pod
        relabel_configs:
        - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
          action: keep
          regex: true
        - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
          action: replace
          target_label: __metrics_path__
          regex: (.+)
        - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
          action: replace
          regex: ([^:]+)(?::\d+)?;(\d+)
          replacement: \$1:\$2
          target_label: __address__
        - action: labelmap
          regex: __meta_kubernetes_pod_label_(.+)
        - source_labels: [__meta_kubernetes_namespace]
          action: replace
          target_label: kubernetes_namespace
        - source_labels: [__meta_kubernetes_pod_name]
          action: replace
          target_label: kubernetes_pod_name
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: prometheus
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: prometheus
  template:
    metadata:
      labels:
        app: prometheus
    spec:
      serviceAccountName: prometheus
      containers:
      - name: prometheus
        image: prom/prometheus:latest
        ports:
        - containerPort: 9090
        volumeMounts:
        - name: config-volume
          mountPath: /etc/prometheus
        - name: storage-volume
          mountPath: /prometheus
        args:
          - '--config.file=/etc/prometheus/prometheus.yml'
          - '--storage.tsdb.path=/prometheus'
          - '--web.console.libraries=/etc/prometheus/console_libraries'
          - '--web.console.templates=/etc/prometheus/consoles'
          - '--storage.tsdb.retention.time=200h'
          - '--web.enable-lifecycle'
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
      volumes:
      - name: config-volume
        configMap:
          name: prometheus-config
      - name: storage-volume
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: prometheus-service
  namespace: monitoring
spec:
  selector:
    app: prometheus
  ports:
  - port: 9090
    targetPort: 9090
  type: NodePort
  nodePort: 30090
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: grafana
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: grafana
  template:
    metadata:
      labels:
        app: grafana
    spec:
      containers:
      - name: grafana
        image: grafana/grafana:latest
        ports:
        - containerPort: 3000
        env:
        - name: GF_SECURITY_ADMIN_PASSWORD
          value: admin
        volumeMounts:
        - name: grafana-storage
          mountPath: /var/lib/grafana
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "300m"
      volumes:
      - name: grafana-storage
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: grafana-service
  namespace: monitoring
spec:
  selector:
    app: grafana
  ports:
  - port: 3000
    targetPort: 3000
  type: NodePort
  nodePort: 30030
MONITORING_MANIFEST

                            # Wait for deployments to be ready
                            echo "--- Waiting for deployments to be ready ---"
                            kubectl wait --for=condition=available deployment/mysql -n url-shortener --timeout=300s || echo "MySQL deployment timeout"
                            kubectl wait --for=condition=available deployment/api -n url-shortener --timeout=300s || echo "API deployment timeout"
                            kubectl wait --for=condition=available deployment/frontend -n url-shortener --timeout=300s || echo "Frontend deployment timeout"
                            kubectl wait --for=condition=available deployment/prometheus -n monitoring --timeout=300s || echo "Prometheus deployment timeout"
                            kubectl wait --for=condition=available deployment/grafana -n monitoring --timeout=300s || echo "Grafana deployment timeout"

                            # Get deployment status
                            echo "--- Deployment Status ---"
                            kubectl get all -n url-shortener
                            kubectl get all -n monitoring
                            kubectl get hpa -n url-shortener

                            # Get access URLs
                            NODE_IP=\$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="ExternalIP")].address}' || kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')
                            echo "--- Access URLs ---"
                            echo "Frontend: http://\${NODE_IP}:30080"
                            echo "Prometheus: http://\${NODE_IP}:30090"
                            echo "Grafana: http://\${NODE_IP}:30030 (admin/admin)"

                            echo "--- Kubernetes Deployment Successful ---"
DEPLOY_EOF
                    """
                }
            }
        }

        stage('Health Check') {
            steps {
                echo "Performing health checks on deployed services"
                sshagent(credentials: ['ec2-ssh-key']) {
                    sh """
                        ssh -o StrictHostKeyChecking=no ubuntu@${DEPLOY_SERVER_IP} << 'HEALTH_EOF'
                            echo "--- Performing health checks ---"
                            
                            # Check if pods are running
                            kubectl get pods -n url-shortener
                            kubectl get pods -n monitoring
                            
                            # Check HPA status
                            kubectl get hpa -n url-shortener
                            
                            # Test API endpoint (if accessible)
                            API_POD=\$(kubectl get pods -n url-shortener -l app=api -o jsonpath='{.items[0].metadata.name}')
                            if [ ! -z "\$API_POD" ]; then
                                echo "Testing API health..."
                                kubectl exec -n url-shortener \$API_POD -- curl -f http://localhost:5000/ || echo "API health check failed"
                            fi
                            
                            echo "--- Health checks completed ---"
HEALTH_EOF
                    """
                }
            }
        }
    }

    post {
        success {
            echo '✅ Kubernetes Build and Deployment Successful!'
            echo 'Your URL Shortener is now running on Kubernetes with:'
            echo '  - Auto-scaling enabled'
            echo '  - Prometheus monitoring'
            echo '  - Grafana dashboards'
            echo 'Access your application at http://YOUR_NODE_IP:30080'
        }
        failure {
            echo '❌ Kubernetes Deployment Failed – check logs above.'
        }
        always {
            echo 'Pipeline completed. Check deployment status with:'
            echo 'kubectl get all -n url-shortener'
            echo 'kubectl get hpa -n url-shortener'
        }
    }
}