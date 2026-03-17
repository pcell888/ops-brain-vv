# 企业运营AI智能诊断系统 (ops-brain)

基于 **LangGraph + MCP + Python** 的多租户 SaaS 智能诊断系统，面向电商行业。

## 功能

- **一键诊断**: CRM、营销、客户留存、运营效率 4 维度 20 项指标健康度评分
- **根因分析**: LLM 驱动的异常指标根因分析
- **方案生成**: AI 生成个性化优化方案，支持自动化营销动作
- **执行推送**: 方案分解为任务推送至业务系统，支持 human-in-the-loop 审批
- **效果追踪**: 执行前后指标对比，自动生成复盘报告
- **WebSocket 实时推送**: 诊断全过程进度实时推送

## 架构

```
FastAPI(HTTP+WebSocket) → LangGraph(状态图) → MCP Servers(5个) → 企业业务系统API
```

| MCP Server | 端口 | 职责 |
|-----------|------|------|
| metrics-server | 8100 | 运营指标采集与计算 |
| crm-server | 8101 | CRM客户数据、企业画像 |
| benchmark-server | 8102 | 行业基准数据 |
| task-server | 8103 | 任务推送 |
| notify-server | 8104 | 消息通知 |

## 快速开始

### 1. 环境配置

```bash
cp .env.example .env
# 编辑 .env 填入 LLM API Key、数据库配置等
```

### 2. Docker Compose 启动

```bash
docker compose up -d
```

### 3. 初始化数据库

连接 PostgreSQL 执行 `tenant_registry` 建表语句（见开发文档第 2.2 节）。

### 4. 注册租户

```sql
INSERT INTO tenant_registry (tenant_id, tenant_name, api_base_url, auth_type, auth_credential, industry_code)
VALUES ('ent_001', '企业A', 'https://ent-a.wlwq.com/api', 'token', 'encrypted_token', 'ecommerce');
```

### 5. 发起诊断

```bash
curl -X POST http://localhost:8000/api/v1/diagnosis/start \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": "ent_001", "store_id": "S100", "trigger_type": "manual"}'
```

返回 `thread_id` 和 `ws_url`，通过 WebSocket 连接接收实时进度。

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/diagnosis/start` | 启动诊断 |
| POST | `/api/v1/diagnosis/{thread_id}/adopt` | 采纳方案 |
| GET | `/api/v1/diagnosis/{thread_id}/state` | 查询状态 |
| WS | `/api/v1/ws/diagnosis/{thread_id}` | 实时进度推送 |
| GET | `/health` | 健康检查 |

## 开发

```bash
pip install -e ".[dev]"
pytest
```

## 技术栈

- Python 3.11+, LangGraph, MCP SDK, FastAPI, httpx
- PostgreSQL (LangGraph Checkpointer), Redis (缓存)
- 通义千问 / GPT-4o (LLM)
