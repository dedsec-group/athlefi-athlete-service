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

  options {
      timestamps()
      ansiColor('xterm')
      disableConcurrentBuilds()
      buildDiscarder(logRotator(numToKeepStr: '20'))
  }

  environment {
    IMAGE      = "registry.sparkfly.cloud/athlefi/athlete-api"
    // Derive TAG cleanly from env on branches or tags:
    RAW_REF    = "${env.GIT_TAG_NAME ?: env.GIT_BRANCH ?: ''}"
    // Normalize possible values like 'refs/tags/v1.2.3' or 'refs/heads/main' or 'origin/main'
    GIT_REF    = "${RAW_REF.replaceAll('refs/tags/','').replaceAll('refs/heads/','').replaceAll('origin/','')}"
    IS_TAG     = "${GIT_REF.startsWith('v')}"          // true if semantic tag
    BRANCH     = "${env.CHANGE_TARGET ?: (GIT_REF.startsWith('v') ? '' : GIT_REF)}"
    SHORT_SHA  = "${env.GIT_COMMIT ? env.GIT_COMMIT.take(7) : ''}"
    // Kaniko cache repo (same registry; create once)
    CACHE_REPO = "registry.sparkfly.cloud/athlefi/kaniko-cache"
  }

  stages {
    stage('Show Build Context') {
      steps {
        echo "GIT_BRANCH: ${env.GIT_BRANCH}"
        echo "GIT_TAG_NAME: ${env.GIT_TAG_NAME}"
        echo "Derived GIT_REF: ${env.GIT_REF}"
        echo "Is Tag?: ${env.IS_TAG}"
      }
    }

    stage('Validate Tag') {
      when { expression { return env.IS_TAG?.toBoolean() } }
      steps {
        echo "Building image for tag ${env.GIT_REF}"
      }
    }

    stage('Build & Push (Tag)') {
      when { expression { return env.IS_TAG?.toBoolean() } }
      steps {
        container('kaniko') {
          retry(2) {
            sh '''
              /kaniko/executor \
                --context="${WORKSPACE}" \
                --dockerfile=Dockerfile \
                --destination=${IMAGE}:${GIT_REF} \
                --destination=${IMAGE}:latest \
                --cache=true \
                --cache-repo=${CACHE_REPO} \
                --verbosity=info \
                --single-snapshot \
                --compressed
            '''
          }
        }
      }
    }

    stage('Build & Push (Main edge)') {
      when { allOf { expression { return !env.IS_TAG?.toBoolean() }; branch 'main' } }
      steps {
        container('kaniko') {
          retry(2) {
            sh '''
              /kaniko/executor \
                --context="${WORKSPACE}" \
                --dockerfile=Dockerfile \
                --destination=${IMAGE}:edge \
                --cache=true \
                --cache-repo=${CACHE_REPO} \
                --verbosity=info \
                --single-snapshot \
                --compressed
            '''
          }
        }
      }
    }

    stage('Build & Push (Feature)') {
      when { allOf { expression { return !env.IS_TAG?.toBoolean() }; not { branch 'main' } } }
      steps {
        container('kaniko') {
          script {
            def safeBranch = env.BRANCH.replaceAll('[^a-zA-Z0-9_.-]', '-')
            def tag = "${safeBranch}-${env.SHORT_SHA}"
            echo "Building feature image tag: ${tag}"
          }
          retry(2) {
            sh '''
              SAFE_BRANCH="$(echo "${BRANCH}" | sed -E 's/[^a-zA-Z0-9_.-]+/-/g')"
              TAG="${SAFE_BRANCH}-${SHORT_SHA}"
              /kaniko/executor \
                --context="${WORKSPACE}" \
                --dockerfile=Dockerfile \
                --destination=${IMAGE}:${TAG} \
                --cache=true \
                --cache-repo=${CACHE_REPO} \
                --verbosity=info \
                --single-snapshot \
                --compressed
            '''
          }
        }
      }
    }
  }

  post {
    always {
      echo "Done: ${currentBuild.currentResult}"
    }
  }
}