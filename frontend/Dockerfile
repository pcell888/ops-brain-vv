# 前端Dockerfile - 生产环境
# 构建阶段
FROM node:20-alpine AS builder

WORKDIR /app

# 启用 pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

# 复制依赖文件
COPY package.json pnpm-lock.yaml* ./

# 安装依赖
RUN pnpm install --frozen-lockfile

# 复制应用代码
COPY . .

# 构建时可覆盖（CDN 独立域名等场景）
ARG VITE_API_URL=
ARG VITE_WS_URL=
ARG VITE_BASE_PATH=
ENV VITE_API_URL=${VITE_API_URL}
ENV VITE_WS_URL=${VITE_WS_URL}
ENV VITE_BASE_PATH=${VITE_BASE_PATH}

RUN pnpm run build

# 运行阶段 - 使用 nginx 托管静态文件（官方镜像 entrypoint 会对 templates 做 envsubst）
FROM nginx:alpine AS runner

ENV API_UPSTREAM_HOST=ops-brain-api
ENV API_UPSTREAM_PORT=8000

COPY --from=builder /app/dist /usr/share/nginx/html
COPY default.conf.template /etc/nginx/templates/default.conf.template

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
