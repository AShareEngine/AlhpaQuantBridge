from api.order_contract import api_order_fingerprint, api_order_status_payload


def test_same_order_instruction_has_a_stable_idempotency_fingerprint():
    original = api_order_fingerprint(
        task_id=7,
        stock_code="000001.SZ",
        volume=100,
        price=12.3,
        is_buy=1,
        order_type=1,
    )
    retry = api_order_fingerprint(
        task_id=7,
        stock_code="000001.SZ",
        volume=100,
        price=12.3000000,
        is_buy=True,
        order_type="1",
    )
    changed_quantity = api_order_fingerprint(
        task_id=7,
        stock_code="000001.SZ",
        volume=200,
        price=12.3,
        is_buy=1,
        order_type=1,
    )

    assert retry == original
    assert changed_quantity != original


def test_order_status_payload_separates_submission_from_fill_status():
    result = api_order_status_payload(
        {
            "id": 42,
            "client_order_id": "live:run:0",
            "task_id": 7,
            "strategy_code": "alphablocks_live",
            "security_code": "000001.SZ",
            "volume": 100,
            "price": 12.3,
            "is_buy": 1,
            "submission_state": "submitted",
            "broker_order_id": "9988",
            "broker_status": "submitted",
            "status_msg": "",
        },
        idempotent_replay=True,
    )

    assert result["order_id"] == 42
    assert result["broker_order_id"] == "9988"
    assert result["submission_state"] == "submitted"
    assert result["idempotent_replay"] is True
