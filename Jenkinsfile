pipeline {
    agent any
    environment {
        DOCKER_REPOSITORY_URL = credentials('DOCKER_REPOSITORY_URL')
    }
    stages{
        stage("Flake8 formatting scan") {
            steps {
                sh '''
                  pip3 install --user tox==3.5.2
                  tox -e flake8
                '''
            }
        }
        stage("Run unit tests suite") {
            steps {
                sh '''
                  pip3 install --user tox==3.5.2
                  tox -e unit
                '''
            }
        }
        stage("Build pex files") {
            steps {
                sh '''
                  pip3 install --user tox==3.5.2
                  tox -e wrapper_package,owca_package
                '''
                stash(name: "wrappers", includes: "dist/**")
                archiveArtifacts(artifacts: "dist/**")
            }
            post {
                always {
                    sh '''
                    rm -fr dist
                    '''
                }
            }
        }
        stage("Building Docker images in parallel") {
            parallel {
                stage("Build and push Tensorflow training Docker image") {
                    steps {
                        withCredentials([file(credentialsId: 'kaggle.json', variable: 'KAGGLE_JSON')]) {
                            unstash("wrappers")
                            sh '''
                            IMAGE_NAME=${DOCKER_REPOSITORY_URL}/owca/tensorflow_train:${GIT_COMMIT}
                            IMAGE_DIR=${WORKSPACE}/workloads/tensorflow_train
                            cp -r dist ${IMAGE_DIR}
                            cp -f ${KAGGLE_JSON} ${IMAGE_DIR}/kaggle.json
                            docker build -t ${IMAGE_NAME} -f ${IMAGE_DIR}/Dockerfile ${IMAGE_DIR}
                            docker push ${IMAGE_NAME}
                            '''
                        }
                    }
                    post {
                        always {
                            sh '''
                            rm -rf ${WORKSPACE}/workloads/tensorflow_train/dist
                            '''
                        }
                    }
                }
                stage("Build and push Tensorflow inference Docker image") {
                    steps {
                        withCredentials([file(credentialsId: 'kaggle.json', variable: 'KAGGLE_JSON')]) {
                            unstash("wrappers")
                            sh '''
                            IMAGE_NAME=${DOCKER_REPOSITORY_URL}/owca/tensorflow_inference:${GIT_COMMIT}
                            IMAGE_DIR=${WORKSPACE}/workloads/tensorflow_inference
                            cp -r dist ${IMAGE_DIR}
                            cp -f ${KAGGLE_JSON} ${IMAGE_DIR}/kaggle.json
                            docker build -t ${IMAGE_NAME} -f ${IMAGE_DIR}/Dockerfile ${IMAGE_DIR}
                            docker push ${IMAGE_NAME}
                            '''
                        }
                    }
                    post {
                        always {
                            sh '''
                            rm -rf ${WORKSPACE}/workloads/tensorflow_inference/dist
                            '''
                        }
                    }
                }
                stage("Build and push Tensorflow Benchmark Docker image") {
                    steps {
                        unstash("wrappers")
                        sh '''
                        IMAGE_NAME=${DOCKER_REPOSITORY_URL}/owca/tensorflow_benchmark:${GIT_COMMIT}
                        IMAGE_DIR=${WORKSPACE}/workloads/tensorflow_benchmark
                        cp -r dist ${IMAGE_DIR}
                        docker build -t ${IMAGE_NAME} -f ${IMAGE_DIR}/Dockerfile ${IMAGE_DIR}
                        docker push ${IMAGE_NAME}
                        '''
                    }
                    post {
                        always {
                            sh '''
                            rm -rf ${WORKSPACE}/workloads/tensorflow_benchmark/dist
                            '''
                        }
                    }
                }
                stage("Build and push Redis Docker image") {
                    steps {
                        sh '''
                        IMAGE_NAME=${DOCKER_REPOSITORY_URL}/owca/redis:${GIT_COMMIT}
                        IMAGE_DIR=${WORKSPACE}/workloads/redis
                        cp -r dist ${IMAGE_DIR}
                        docker build -t ${IMAGE_NAME} -f ${IMAGE_DIR}/Dockerfile ${IMAGE_DIR}
                        docker push ${IMAGE_NAME}
                        '''
                    }
                    post {
                        always {
                            sh '''
                            rm -rf ${WORKSPACE}/workloads/redis/dist
                            '''
                        }
                    }
                }
                stage("Build and push stress-ng Docker image") {
                    steps {
                        unstash("wrappers")
                        sh '''
                        IMAGE_NAME=${DOCKER_REPOSITORY_URL}/owca/stress_ng:${GIT_COMMIT}
                        IMAGE_DIR=${WORKSPACE}/workloads/stress_ng
                        cp -r dist ${IMAGE_DIR}
                        docker build -t ${IMAGE_NAME} -f ${IMAGE_DIR}/Dockerfile ${IMAGE_DIR}
                        docker push ${IMAGE_NAME}
                        '''
                    }
                    post {
                        always {
                            sh '''
                            rm -rf ${WORKSPACE}/workloads/stress_ng/dist
                            '''
                        }
                    }
                }
                stage("Build and push rpc-perf Docker image") {
                    steps {
                        unstash("wrappers")
                        sh '''
                        IMAGE_NAME=${DOCKER_REPOSITORY_URL}/owca/rpc_perf:${GIT_COMMIT}
                        IMAGE_DIR=${WORKSPACE}/workloads/rpc_perf
                        cp -r dist ${IMAGE_DIR}
                        docker build -t ${IMAGE_NAME} -f ${IMAGE_DIR}/Dockerfile ${IMAGE_DIR}
                        docker push ${IMAGE_NAME}
                        '''
                    }
                    post {
                        always {
                            sh '''
                            rm -rf ${WORKSPACE}/workloads/rpc_perf/dist
                            '''
                        }
                    }
                }
                stage("Build and push Twemcache Docker image") {
                    steps {
                        sh '''
                        IMAGE_NAME=${DOCKER_REPOSITORY_URL}/owca/twemcache:${GIT_COMMIT}
                        IMAGE_DIR=${WORKSPACE}/workloads/twemcache
                        cp -r dist ${IMAGE_DIR}
                        docker build -t ${IMAGE_NAME} -f ${IMAGE_DIR}/Dockerfile ${IMAGE_DIR}
                        docker push ${IMAGE_NAME}
                        '''
                    }
                    post {
                        always {
                            sh '''
                            rm -rf ${WORKSPACE}/workloads/twemcache/dist
                            '''
                        }
                    }
                }
                stage("Build and push YCSB Docker image") {
                    steps {
                        unstash("wrappers")
                        sh '''
                        IMAGE_NAME=${DOCKER_REPOSITORY_URL}/owca/ycsb:${GIT_COMMIT}
                        IMAGE_DIR=${WORKSPACE}/workloads/ycsb
                        cp -r dist ${IMAGE_DIR}
                        docker build -t ${IMAGE_NAME} -f ${IMAGE_DIR}/Dockerfile ${IMAGE_DIR}
                        docker push ${IMAGE_NAME}
                        '''
                    }
                    post {
                        always {
                            sh '''
                            rm -rf ${WORKSPACE}/workloads/ycsb/dist
                            '''
                        }
                    }
                }
                stage("Build and push Cassandra Stress Docker image") {
                    steps {
                        unstash("wrappers")
                        sh '''
                        IMAGE_NAME=${DOCKER_REPOSITORY_URL}/owca/cassandra_stress:${GIT_COMMIT}
                        IMAGE_DIR=${WORKSPACE}/workloads/cassandra_stress
                        cp -r dist ${IMAGE_DIR}
                        docker build -t ${IMAGE_NAME} -f ${IMAGE_DIR}/Dockerfile ${IMAGE_DIR}
                        docker push ${IMAGE_NAME}
                        '''
                    }
                    post {
                        always {
                            sh '''
                            rm -rf ${WORKSPACE}/workloads/cassandra_stress/dist
                            '''
                        }
                    }
                }
                stage("Build and push mutilate Docker image") {
                    steps {
                        unstash("wrappers")
                        sh '''
                        IMAGE_NAME=${DOCKER_REPOSITORY_URL}/owca/mutilate:${GIT_COMMIT}
                        IMAGE_DIR=${WORKSPACE}/workloads/mutilate
                        cp -r dist ${IMAGE_DIR}
                        docker build -t ${IMAGE_NAME} -f ${IMAGE_DIR}/Dockerfile ${IMAGE_DIR}
                        docker push ${IMAGE_NAME}
                        '''
                    }
                    post {
                        always {
                            sh '''
                            rm -rf ${WORKSPACE}/workloads/mutilate/dist
                            '''
                        }
                    }
                }
                stage("Build and push SpecJBB Docker image") {
                    steps {
                        withCredentials([file(credentialsId: 'specjbb', variable: 'SPECJBB_TAR')]) {
                            unstash("wrappers")
                            sh '''
                            IMAGE_NAME=${DOCKER_REPOSITORY_URL}/owca/specjbb:${GIT_COMMIT}
                            IMAGE_DIR=${WORKSPACE}/workloads/specjbb
                            cp ${SPECJBB_TAR} ${IMAGE_DIR}
                            tar -xC ${IMAGE_DIR} -f ${IMAGE_DIR}/specjbb.tar.bz2
                            cp -r dist ${IMAGE_DIR}
                            docker build -t ${IMAGE_NAME} -f ${IMAGE_DIR}/Dockerfile ${IMAGE_DIR}
                            docker push ${IMAGE_NAME}
                            '''
                        }
                    }
                    post {
                        always {
                            sh '''
                            rm -rf ${WORKSPACE}/workloads/specjbb/specjbb.tar.bz2 ${WORKSPACE}/workloads/specjbb/specjbb ${WORKSPACE}/workloads/specjbb/dist
                            '''
                        }
                    }
                }
            }
            post {
                always {
                    sh '''
                    rm -f kaggle.json
                    '''
                }
            }
        }
    }
}
