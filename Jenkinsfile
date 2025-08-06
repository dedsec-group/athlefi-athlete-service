pipeline {
    agent {
        kubernetes {
            label 'kaniko-agent'
            defaultContainer 'kaniko'
            yaml """
apiVersion: v1
kind: Pod
metadata:
  labels:
    jenkins: kaniko
spec:
  containers:
    - name: kaniko
      image: gcr.io/kaniko-project/executor:debug
      command:
        - /busybox/sh
      args:
        - -c
        - sleep 999999
      tty: true
      volumeMounts:
        - name: kaniko-secret
          mountPath: /kaniko/.docker
          readOnly: true
        - name: workspace-volume
          mountPath: /workspace
  volumes:
    - name: kaniko-secret
      secret:
        secretName: regcred
        items:
          - key: .dockerconfigjson
            path: config.json
    - name: workspace-volume
      emptyDir: {}
"""
        }
    }
    environment {
        IMAGE = "registry.sparkfly.cloud/athlefi/athlete-api"
        TAG = "v${env.BUILD_NUMBER}"
    }
    stages {
        stage('Prepare Workspace') {
            steps {
                container('kaniko') {
                    sh '''
                    mkdir -p /workspace/app
                    cp -r * /workspace/app/
                    '''
                }
            }
        }
        stage('Build Docker Image with Kaniko') {
            steps {
                container('kaniko') {
                    sh '''
                    /kaniko/executor \
                      --dockerfile=/workspace/app/Dockerfile \
                      --context=/workspace/app \
                      --destination=${IMAGE}:${TAG} \
                      --destination=${IMAGE}:latest \
                      --verbosity=debug
                    '''
                }
            }
        }
    }
}