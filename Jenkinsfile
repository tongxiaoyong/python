pipeline {
  agent any
  stages {
    stage('git') {
      steps {
        git(url: 'https://github.com/tongxiaoyong/python.git', branch: 'master', poll: true)
      }
    }
  }
}