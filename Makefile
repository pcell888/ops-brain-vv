# 配置
VENV := venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

# 端口
PORT_API := 8000
PORT_WLWQ := 8200
PORT_FRONTEND := 3000
PORTS := $(PORT_API) $(PORT_WLWQ) $(PORT_FRONTEND)

# 假目标
.PHONY: dev setup-dev infra up down kill-port clean

# 1. 创建虚拟环境
venv:
	python3 -m venv $(VENV)

# 2. 安装依赖
setup-dev: venv
	$(PIP) install -e .

# 3. 启动数据库（postgres + redis）
infra:
	docker compose up -d postgres redis

# 4. 启动本地开发服务
dev: kill-port
	@( \
		$(VENV)/bin/uvicorn src.api.main:app --host 0.0.0.0 --port $(PORT_API) --reload & \
		$(VENV)/bin/uvicorn src.wlwq.app:app --host 0.0.0.0 --port $(PORT_WLWQ) --reload & \
		cd frontend && pnpm run dev -- --port $(PORT_FRONTEND) & \
		wait \
	)

# 5. 杀死已占用端口
kill-port:
	@for p in $(PORTS); do \
		pids=$$(lsof -t -iTCP:$$p -sTCP:LISTEN 2>/dev/null); \
		if [ -n "$$pids" ]; then \
			kill $$pids 2>/dev/null || true; \
			sleep 0.2; \
			still=$$(lsof -t -iTCP:$$p -sTCP:LISTEN 2>/dev/null); \
			[ -n "$$still" ] && kill -9 $$still 2>/dev/null || true; \
		fi; \
	done

# 6. Docker 一键启动全部
up:
	docker compose up -d --build

# 7. Docker 停止
down:
	docker compose down

# 8. 清理缓存
clean:
	rm -rf $(VENV) __pycache__ *.pyc .pytest_cache


# ─── rsync部署 ────────────────────────────────────
HOST=47.118.25.132
USER=root
REMOTE_DIR=/opt/wzq/opt-brain

# 要上传的内容
SRC=src frontend config docker-compose.yml Makefile Dockerfile pyproject.toml

# 要排除的内容
EXCLUDES= \
  --exclude="**/__pycache__/**" \
  --exclude="**/*.pyc" \
  --exclude="**/*.pyo" \
  --exclude="frontend/.pnpm-store/**" \
  --exclude="frontend/node_modules/**" \
  --exclude="frontend/dist/**"

# 一键部署
deploy:
	rsync -avz $(EXCLUDES) $(SRC) $(USER)@$(HOST):$(REMOTE_DIR)