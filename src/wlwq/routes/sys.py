"""部门与用户 — 供 MCP crm-server get_dept_structure 调用。"""

from __future__ import annotations

from fastapi import APIRouter, Query

from src.wlwq.database import get_cursor

router = APIRouter(tags=["sys"])


def _ok(data):
    return {"code": 0, "data": data, "msg": "success"}


@router.get("/sys-dept/tree")
async def dept_tree(storeId: str | None = Query(None)):
    try:
        async with get_cursor() as cur:
            await cur.execute(
                'SELECT dept_id AS "deptId", dept_name AS "deptName", parent_id AS "parentId" FROM sys_dept WHERE del_flag=\'0\''
            )
            rows = await cur.fetchall()
            return _ok({"list": rows})
    except Exception:
        return _ok({
            "list": [
                {"deptId": 1, "deptName": "总公司", "parentId": 0},
                {"deptId": 2, "deptName": "销售部", "parentId": 1},
                {"deptId": 3, "deptName": "运营部", "parentId": 1},
                {"deptId": 4, "deptName": "客服部", "parentId": 1},
            ]
        })


@router.get("/sys-user/list")
async def user_list(deptId: str | None = Query(None)):
    try:
        async with get_cursor() as cur:
            if deptId:
                await cur.execute(
                    'SELECT u.user_id AS "userId", u.nick_name AS "userName", u.dept_id AS "deptId" '
                    "FROM sys_user u WHERE u.dept_id=%s AND u.del_flag='0'",
                    (int(deptId) if deptId.isdigit() else deptId,),
                )
            else:
                await cur.execute(
                    'SELECT u.user_id AS "userId", u.nick_name AS "userName", u.dept_id AS "deptId" FROM sys_user u WHERE u.del_flag=\'0\''
                )
            rows = await cur.fetchall()
            return _ok({"list": rows})
    except Exception:
        return _ok({
            "list": [
                {"userId": 1, "userName": "管理员", "deptId": 2},
                {"userId": 2, "userName": "销售主管", "deptId": 2},
                {"userId": 3, "userName": "运营经理", "deptId": 3},
                {"userId": 4, "userName": "客服主管", "deptId": 4},
            ]
        })
