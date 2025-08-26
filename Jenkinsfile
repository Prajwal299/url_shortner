pipeline {
    agent any

    environment {
        JAVA_HOME = "/usr/lib/jvm/java-17-openjdk-amd64"
        PATH = "$JAVA_HOME/bin:/usr/share/maven/bin:$PATH"
    }

    stages {
        stage('Checkout') {
            steps {
                git branch: 'main', url: 'https://github.com/Prajwal299/url_shortner.git'
            }
        }

        stage('Build') {
            steps {
                dir('app') {
                    sh 'mvn clean compile'
                }
            }
        }

        stage('Test') {
            steps {
                dir('app') {
                    sh 'mvn test'
                }
            }
            post {
                always {
                    junit 'app/target/surefire-reports/*.xml'
                }
            }
        }

        stage('Package') {
            steps {
                dir('app') {
                    sh 'mvn package -DskipTests'
                }
                archiveArtifacts artifacts: 'app/target/*.jar', fingerprint: true
            }
        }

        stage('Deploy to EC2') {
            when {
                branch 'main'
            }
            steps {
                withCredentials([sshUserPrivateKey(credentialsId: 'ec2-ssh-key', keyFileVariable: 'SSH_KEY')]) {
                    sh """
                        scp -o StrictHostKeyChecking=no -i $SSH_KEY app/target/*.jar ubuntu@YOUR_EC2_IP:/home/ubuntu/app.jar
                        ssh -o StrictHostKeyChecking=no -i $SSH_KEY ubuntu@YOUR_EC2_IP 'nohup java -jar /home/ubuntu/app.jar > app.log 2>&1 &'
                    """
                }
            }
        }
    }

    post {
        success {
            echo 'Pipeline executed successfully ✅'
        }
        failure {
            echo 'Pipeline failed ❌'
        }
    }
}
