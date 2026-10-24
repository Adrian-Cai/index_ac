# 蔡金伟个人主页：自托管部署

本包是纯静态站点：HTML、CSS、JavaScript 和 `dist/assets/` 图片；不需要数据库或后端。配置使用 Docker Compose 和 Caddy。Caddy 可直接提供静态文件，并在域名解析到服务器且 80/443 端口可从公网访问时自动申请和续期 HTTPS 证书。

> 对外开放前，请先检查简历页是否要继续公开手机号和邮箱。

## 1. 上传并解压

将 ZIP 上传到服务器后：

```bash
sudo mkdir -p /opt/caijinwei-portfolio
sudo unzip caijinwei-portfolio-self-host.zip -d /opt/caijinwei-portfolio
cd /opt/caijinwei-portfolio/caijinwei-portfolio-self-host
```

## 2. 配置域名

编辑 `Caddyfile`，把 `your-domain.example` 替换为自己的域名，例如 `portfolio.example.com`。然后在 DNS 中将域名解析到服务器的公网地址。

服务器防火墙、安全组和路由器（家庭服务器）需要允许 TCP 80、TCP 443；配置 IPv6 时还要确保 IPv6 入站规则允许这些端口。若 80 或 443 已由现有 Web 服务占用，把域名转发接入现有反向代理，不要让两个服务同时绑定同一端口。

## 3. 启动

服务器已安装 Docker Engine 和 Docker Compose 插件后执行：

```bash
docker compose up -d
docker compose ps
docker compose logs -f portfolio
```

配置正确并且公网 DNS/端口可达后，用 `https://你的域名` 访问。Docker Compose 的 `-d` 会让容器在后台持续运行。

## 4. 更新网站

把新版完整 `dist/` 目录覆盖服务器上的 `dist/`（保留 `assets/`），通常无需重建镜像；浏览器强制刷新即可看到更新。修改 `Caddyfile` 后执行：

```bash
docker compose restart portfolio
```

停止服务：

```bash
docker compose down
```

证书数据放在 Compose 命名卷中；不要删除 `caddy_data`，否则 Caddy 会重新申请证书。

## 家庭服务器说明

公网访客需要能够从互联网连到服务器的 80/443 端口。若宽带处于运营商 CGNAT，单做路由器端口映射仍无法从公网直连，需要向运营商申请可入站的公网地址，或使用带公网入口的隧道/中转服务器。
