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
        - while true; do sleep 30; done
      volumeMounts:
        - name: kaniko-secret
          mountPath: /kaniko/.docker
  volumes:
    - name: kaniko-secret
      secret:
        secretName: regcred
"""
        }
    }
    environment {
        IMAGE = "harbor.sparkfly.dev/athlefi/athlete-api"
        TAG = "v${env.BUILD_NUMBER}"
    }
    stages {
        stage('Build Docker Image with Kaniko') {
            steps {
                container('kaniko') {
                    sh '''
                    /kaniko/executor \
                      --context `pwd` \
                      --dockerfile Dockerfile \
                      --destination=${IMAGE}:${TAG} \
                      --destination=${IMAGE}:latest \
                      --verbosity=debug
                    '''
                }
            }
        }
    }
}