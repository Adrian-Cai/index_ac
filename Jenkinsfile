pipeline {
    agent { label 'caijinwei-portfolio-production' }

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    parameters {
        string(name: 'IMAGE_TAG', defaultValue: '', description: 'CNB 提交镜像标签（8 位 commit SHA）')
    }

    environment {
        PACKAGE_DIR = 'caijinwei-portfolio-self-host'
        DEPLOY_DIR = '/opt/caijinwei-portfolio/caijinwei-portfolio-self-host'
        COMPOSE_PROJECT_NAME = 'caijinwei-portfolio-self-host'
        IMAGE_REPO = 'docker.cnb.cool/imacaiy/caijinwei-portfolio'
    }

    stages {
        stage('检查部署环境') {
            steps {
                sh '''
                    set -eu
                    printf '%s' "$IMAGE_TAG" | grep -Eq '^[0-9a-f]{8}$'
                    test -f "$PACKAGE_DIR/compose.yaml"
                    test -f "$PACKAGE_DIR/Caddyfile"
                    test -f "$PACKAGE_DIR/dist/index.html"
                    grep -Fqx 'index.wiac.xyz {' "$PACKAGE_DIR/Caddyfile"
                    ! grep -Fq 'your-domain.example' "$PACKAGE_DIR/Caddyfile"
                    command -v docker >/dev/null
                    command -v curl >/dev/null
                    docker compose version >/dev/null
                    docker info >/dev/null
                    mkdir -p "$DEPLOY_DIR"
                    test -w "$DEPLOY_DIR"
                    export PORTFOLIO_IMAGE="$IMAGE_REPO:$IMAGE_TAG"
                    docker compose --project-name "$COMPOSE_PROJECT_NAME" \
                      --file "$PACKAGE_DIR/compose.yaml" config --quiet
                '''
            }
        }

        stage('同步 Compose 配置') {
            steps {
                sh '''
                    set -eu
                    cp "$PACKAGE_DIR/compose.yaml" "$DEPLOY_DIR/compose.yaml"
                    export PORTFOLIO_IMAGE="$IMAGE_REPO:$IMAGE_TAG"
                    docker compose --project-name "$COMPOSE_PROJECT_NAME" \
                      --file "$DEPLOY_DIR/compose.yaml" config --quiet
                '''
            }
        }

        stage('部署 Caddy') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'cnb-registry-readonly',
                    usernameVariable: 'CNB_REGISTRY_USER',
                    passwordVariable: 'CNB_REGISTRY_TOKEN'
                )]) {
                    sh '''
                        set -eu
                        set +x
                        printf '%s' "$CNB_REGISTRY_TOKEN" | docker login docker.cnb.cool \
                          --username "$CNB_REGISTRY_USER" --password-stdin
                        trap 'docker logout docker.cnb.cool >/dev/null 2>&1 || true' EXIT

                        export PORTFOLIO_IMAGE="$IMAGE_REPO:$IMAGE_TAG"
                        docker compose --project-name "$COMPOSE_PROJECT_NAME" \
                          --file "$DEPLOY_DIR/compose.yaml" pull portfolio
                        docker compose --project-name "$COMPOSE_PROJECT_NAME" \
                          --file "$DEPLOY_DIR/compose.yaml" up -d --force-recreate portfolio

                        container_id=$(docker compose --project-name "$COMPOSE_PROJECT_NAME" \
                          --file "$DEPLOY_DIR/compose.yaml" ps -q portfolio)
                        test -n "$container_id"
                        test "$(docker inspect --format '{{.State.Running}}' "$container_id")" = true

                        status=$(curl --silent --show-error --output /dev/null \
                          --write-out '%{http_code}' --max-time 10 \
                          --header 'Host: index.wiac.xyz' http://127.0.0.1/)
                        case "$status" in
                          200|308) ;;
                          *) echo "Caddy 本机 HTTP 检查失败，状态码：$status" >&2; exit 1 ;;
                        esac
                    '''
                }
            }
        }
    }
}
