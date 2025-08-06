pipeline {
    agent any

    environment {
        REGISTRY = "registry.sparkfly.cloud"
        IMAGE_NAME = "athlefi/athlete-api"
        TAG = "latest"
        DOCKER_CREDENTIALS_ID = "regcred"  // ID del secreto de Jenkins para el login
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build Docker Image') {
            steps {
                script {
                    sh "docker build -t ${REGISTRY}/${IMAGE_NAME}:${TAG} ."
                }
            }
        }

        stage('Push to Registry') {
            steps {
                script {
                    docker.withRegistry("https://${REGISTRY}", "${DOCKER_CREDENTIALS_ID}") {
                        sh "docker push ${REGISTRY}/${IMAGE_NAME}:${TAG}"
                    }
                }
            }
        }

        stage('Post') {
            steps {
                echo "Build and push complete!"
            }
        }
    }

    post {
        failure {
            echo "❌ Build failed!"
        }
        success {
            echo "✅ Build succeeded!"
        }
    }
}