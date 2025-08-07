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
      command: []
      volumeMounts:
        - name: kaniko-secret
          mountPath: /kaniko/.docker
          readOnly: true
  volumes:
    - name: kaniko-secret
      secret:
        secretName: regcred
        items:
          - key: .dockerconfigjson
            path: config.json
"""
        }
    }
    environment {
        IMAGE = "registry.sparkfly.cloud/athlefi/athlete-api"
        GIT_TAG = "${env.GIT_TAG_NAME ?: env.GIT_BRANCH?.replaceAll('origin/', '')}"
    }
    stages {
        stage('Validate Tag') {
            when {
                expression {
                    return GIT_TAG.startsWith('v')
                }
            }
            steps {
                echo "Building image for tag ${GIT_TAG}"
            }
        }

        stage('Build and Push Image') {
            when {
                expression {
                    return GIT_TAG.startsWith('v')
                }
            }
            steps {
                container('kaniko') {
                    sh '''
                    /kaniko/executor \
                      --context=`pwd` \
                      --dockerfile=Dockerfile \
                      --destination=${IMAGE}:${GIT_TAG} \
                      --destination=${IMAGE}:latest \
                      --verbosity=info
                    '''
                }
            }
        }
    }
}