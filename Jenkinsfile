pipeline {
  agent {
    kubernetes {
      yaml """
apiVersion: v1
kind: Pod
spec:
  containers:
    - name: kaniko
      image: gcr.io/kaniko-project/executor:latest
      command: ["/bin/sh"]
      args: ["-c", "while true; do sleep 30; done"]
      tty: true
      volumeMounts:
        - name: kaniko-secret
          mountPath: /kaniko/.docker
        - name: workspace-volume
          mountPath: /workspace
  volumes:
    - name: kaniko-secret
      secret:
        secretName: regcred
    - name: workspace-volume
      emptyDir: {}
"""
    }
  }

  environment {
    IMAGE = "registry.sparkfly.cloud/athlefi/athlete-api"
    TAG = "latest"
  }

  stages {
    stage('Clone Repo') {
      steps {
        container('kaniko') {
          sh '''
            mkdir -p /workspace/app
            cp -r * /workspace/app/
          '''
        }
      }
    }

    stage('Build and Push') {
      steps {
        container('kaniko') {
          sh '''
            /kaniko/executor \
              --dockerfile=/workspace/app/Dockerfile \
              --context=/workspace/app \
              --destination=${IMAGE}:${TAG} \
              --skip-tls-verify \
              --insecure
          '''
        }
      }
    }
  }
}