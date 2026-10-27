# 蔡金伟个人主页：CNB + Jenkins 部署

本项目是纯静态站点推送到 main 后，CNB 将 dist/ 和 Caddy 配置打成 Docker 镜像并推送到 CNB Docker 制品库；CNB 随后调用 Jenkins 的 SCM PipelineJenkins 在标记为 caijinwei-portfolio-production 的 Agent 上拉取指定提交的镜像，通过 Docker Compose 部署并检查本机 HTTP 状态

对外开放前，请检查简历页是否要继续公开手机号和邮箱

## 首次配置

### CNB 密钥仓库

在 CNB 创建私有密钥仓库 ImAcaiy/caijinwei-portfolio-secrets，添加 jenkins.yml文件包含：

    JENKINS_JOB_URL: "https://jenkins.example.com/job/folder/job/portfolio"
    JENKINS_USER: "jenkins-deploy"
    JENKINS_API_TOKEN: "由 Jenkins 生成的 API token"
    allow_slugs:
      - ImAcaiy/caijinwei-portfolio
    allow_events:
      - push
    allow_branches:
      - main

将 URL、用户名和 token 替换成 Jenkins SCM Pipeline 的实际值Jenkins 用户只需有读取和构建该 job 的权限不要把真实 token 提交到普通 Git 仓库

### Jenkins

1. Jenkins Pipeline job 从本仓库 SCM 加载根目录的 Jenkinsfile，并配置 IMAGE_TAG 字符串参数
2. 在 Jenkins 凭据中创建用户名/密码项，ID 为 cnb-registry-readonly；用户名填 `cnb`，密码使用有该 Docker 制品库只读权限的 CNB 访问令牌
3. caijinwei-portfolio-production Agent 需要 Docker Engine、Docker Compose 插件和 curlCNB Runner 需要能通过 HTTPS 访问 Jenkins

### 服务器

域名 index.wiac.xyz 的 DNS 和防火墙需允许公网访问 TCP 80、443；启用 IPv6 时也需允许对应入站流量Caddy 的证书和配置保存在 Compose 命名卷中

## 发布与运维

每次推送 main 时，CNB 检查部署文件，构建 docker.cnb.cool/imacaiy/caijinwei-portfolio:<提交短 SHA> 镜像并推送，然后触发 Jenkins 部署同一标签CNB 等待 Jenkins 完成；部署失败或等待超时会使 CNB 流水线失败

在 Jenkins 查看容器和日志：

    docker compose --project-name caijinwei-portfolio-self-host \
      --file /opt/caijinwei-portfolio/caijinwei-portfolio-self-host/compose.yaml ps
    docker compose --project-name caijinwei-portfolio-self-host \
      --file /opt/caijinwei-portfolio/caijinwei-portfolio-self-host/compose.yaml logs -f portfolio

手动部署镜像时，在 Compose 命令前设置完整镜像名，例如：

    PORTFOLIO_IMAGE=docker.cnb.cool/imacaiy/caijinwei-portfolio:0123abcd \
      docker compose --project-name caijinwei-portfolio-self-host \
      --file /opt/caijinwei-portfolio/caijinwei-portfolio-self-host/compose.yaml \
      up -d --force-recreate

证书数据保存在 caddy_data 命名卷中停止服务时不要传 --volumes，否则会删除证书数据

若宽带处于运营商 CGNAT，单做路由器端口映射无法让公网访客直连；需要可入站的公网地址，或使用带公网入口的隧道/中转服务器
