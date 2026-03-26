from __future__ import annotations


def test_client_record_list_accepts_page_no(client) -> None:
    resp = client.get("/client-record/list", params={"pageNo": 2, "pageSize": 10})
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("code") == 0


def test_sales_contract_list_accepts_page_no(client) -> None:
    resp = client.get("/sales-contract/list", params={"pageNo": 2, "pageSize": 10})
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("code") == 0
