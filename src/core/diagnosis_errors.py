"""诊断失败时面向终端用户的短文案；完整异常仅在日志中记录。"""

from __future__ import annotations

import re

_DEFAULT = "诊断未能正常完成，请稍后重试。"


def _extract_mcp_tool_error(raw: str) -> str | None:
    """从 MCP 工具错误消息中提取业务端原始错误。

    典型格式: Error executing tool <tool>: [code] <path>: <business_error>
    """
    m = re.search(r"Error executing tool \w+:\s*\[\d+\]\s*\S+:\s*(.+)", raw, re.IGNORECASE)
    if m:
        detail = m.group(1).strip()
        if detail:
            return detail
    return None


def public_diagnosis_error_message(exc: BaseException) -> str:
    """
    根据异常内容归纳为用户可读的一句说明，不包含路径、堆栈与响应体原文。
    """
    raw = str(exc).strip()
    low = raw.lower()

    if not raw:
        return _DEFAULT

    if "已取消" in raw:
        return "诊断已取消。"

    if "timeout" in low or "timed out" in low or "超时" in raw:
        return "连接或请求超时，请稍后重试。"
    if "econnrefused" in low or "connection refused" in low or "连接被拒绝" in raw:
        return "无法连接到服务，请检查网络后重试。"
    if "enotfound" in low or "getaddrinfo" in low:
        return "网络或域名解析异常，请检查网络设置。"

    if "401" in raw or "unauthorized" in low:
        return "没有访问所需数据的权限，请联系管理员。"
    if "403" in raw or "forbidden" in low:
        return "访问被拒绝，请联系管理员。"
    if "404" in raw or "not found" in low:
        return "所需数据或服务暂不可用，请稍后重试。"
    if "429" in raw or "too many requests" in low:
        return "请求过于频繁，请稍后再试。"
    if "502" in raw or "bad gateway" in low:
        return "上游服务暂时不可用，请稍后重试。"
    if "503" in raw or "service unavailable" in low:
        return "服务暂时繁忙，请稍后重试。"
    if "504" in raw or "gateway timeout" in low:
        return "服务响应超时，请稍后重试。"
    if "500" in raw or "internal server error" in low:
        return "服务暂时异常，请稍后重试。"

    if "error executing tool" in low or "executing tool" in low:
        detail = _extract_mcp_tool_error(raw)
        if detail:
            return f"执行任务创建失败: {detail}"
        return "分析过程中获取数据失败，请稍后重试。"
    if "数据缺失" in raw or "数据采集" in raw:
        return "数据采集失败，无法完成诊断，请检查业务系统连通性后重试。"

    return _DEFAULT
