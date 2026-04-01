# 本地开发（不用 Docker 跑应用）：venv + 本机启动所有服务
VENV_DIR := venv
PYTHON := $(VENV_DIR)/bin/python
PIP := $(VENV_DIR)/bin/pip

# 本地服务占用端口，dev 启动前会先释放
LOCAL_PORTS := 8000 8200 3000

.PHONY: dev setup-dev dev-infra run-local kill-local-ports deps venv create-pg-db init-db

# 创建 venv（不存在时）
venv:
	@test -d $(VENV_DIR) || (python3 -m venv $(VENV_DIR) && echo "已创建 $(VENV_DIR)")

# 安装 Python 依赖（venv 已存在则跳过）
DEPS_MARKER := $(VENV_DIR)/.deps-installed
deps: venv
	@test -f $(DEPS_MARKER) || ($(PIP) install -e . && touch $(DEPS_MARKER))

# 本地开发：仅准备 venv 与依赖（不启动 Docker）
# 请先确保 postgres:5432、redis:6379 已就绪（本机或 make dev-infra）
setup-dev: deps
	@echo "--- 本地环境就绪 (venv: $(VENV_DIR))"
	@echo "  启动所有应用: make dev"
	@echo "  若需 Docker 起 postgres/redis: make dev-infra"

# 仅用 Docker 启动 postgres + redis（供本机应用连接）
dev-infra:
	docker compose up -d postgres redis
	@echo "--- postgres:5432 redis:6379 已启动"

# 根据 .env 的 POSTGRES_URI 创建数据库（不存在时）
create-pg-db:
	$(PYTHON) scripts/create_pg_db.py

# 初始化 PostgreSQL 表：建库 + tenant_registry 表及种子数据（无 Alembic，按需执行）
init-db: create-pg-db
	$(PYTHON) scripts/init_tenant_registry.py
	@echo "--- 诊断用表已就绪；LangGraph checkpoint 表在首次请求时自动创建"

# 释放本地服务端口（避免 address already in use）
kill-local-ports:
	@for p in $(LOCAL_PORTS); do \
		(fuser -k $$p/tcp 2>/dev/null) || \
		(pids=$$(lsof -t -i :$$p 2>/dev/null); [ -n "$$pids" ] && kill -9 $$pids); \
		true; \
	done
	@echo "--- 已释放端口: $(LOCAL_PORTS)"

# 本机启动全部应用（API + wlwq + frontend），MCP server 通过 stdio 按需启动
dev: deps kill-local-ports
	@echo "--- 启动本地服务 (API 8000, wlwq 8200, frontend 3000)..."
	@echo "--- MCP servers 使用 stdio 传输，由 API 进程按需拉起"
	@( \
		$(VENV_DIR)/bin/uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload & \
		$(VENV_DIR)/bin/uvicorn src.wlwq.app:app --host 0.0.0.0 --port 8200 --reload & \
		cd frontend && pnpm run dev & \
		wait \
	)

# 兼容旧命令
run-local: dev

# Docker 启动全部服务（含 API、MCP、wlwq、frontend 开发服务器）
# 默认 --build：代码变更后否则会一直跑镜像里旧的 COPY，刷新页面也看不到效果
up:
	docker compose up -d --build

down:
	docker compose down
