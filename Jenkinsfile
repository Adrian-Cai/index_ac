pipeline {
    agent { label 'caijinwei-portfolio-production' }

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    environment {
        PACKAGE_DIR = 'caijinwei-portfolio-self-host'
        DEPLOY_DIR = '/opt/caijinwei-portfolio/caijinwei-portfolio-self-host'
        COMPOSE_PROJECT_NAME = 'caijinwei-portfolio-self-host'
    }

    stages {
        stage('检查部署环境') {
            steps {
                sh '''
                    set -eu
                    test -f "$PACKAGE_DIR/compose.yaml"
                    test -f "$PACKAGE_DIR/Caddyfile"
                    test -f "$PACKAGE_DIR/dist/index.html"
                    test -f "$PACKAGE_DIR/dist/assets/xiaolu-mini-program-qr.png"
                    test -f "$PACKAGE_DIR/dist/assets/quality-engine-qr.png"
                    grep -Fqx 'index.wiac.xyz {' "$PACKAGE_DIR/Caddyfile"
                    ! grep -Fq 'your-domain.example' "$PACKAGE_DIR/Caddyfile"
                    command -v docker >/dev/null
                    command -v curl >/dev/null
                    docker compose version >/dev/null
                    docker info >/dev/null
                    mkdir -p "$DEPLOY_DIR"
                    test -w "$DEPLOY_DIR"
                    docker compose --project-name "$COMPOSE_PROJECT_NAME" \
                      --file "$PACKAGE_DIR/compose.yaml" config --quiet
                '''
            }
        }

        stage('同步站点文件') {
            steps {
                sh '''
                    set -eu
                    cp -a "$PACKAGE_DIR/." "$DEPLOY_DIR/"
                    docker compose --project-name "$COMPOSE_PROJECT_NAME" \
                      --file "$DEPLOY_DIR/compose.yaml" config --quiet
                '''
            }
        }

        stage('部署 Caddy') {
            steps {
                sh '''
                    set -eu
                    docker compose --project-name "$COMPOSE_PROJECT_NAME" \
                      --file "$DEPLOY_DIR/compose.yaml" up -d --force-recreate

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
