FROM caddy:2-alpine

COPY caijinwei-portfolio-self-host/Caddyfile /etc/caddy/Caddyfile
COPY caijinwei-portfolio-self-host/dist/ /srv/

RUN caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
