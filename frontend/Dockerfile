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

# 构建应用
RUN pnpm run build

# 运行阶段 - 使用 nginx 托管静态文件
FROM nginx:alpine AS runner

# 复制构建输出到 nginx
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制 nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 暴露端口
EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
