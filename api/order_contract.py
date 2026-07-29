"""Stable request and response shapes for the local automated-order API."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


def api_order_fingerprint(*, task_id, stock_code, volume, price, is_buy, order_type) -> str:
    """Return the canonical digest guarded by one idempotency key."""
    payload = {
        "task_id": int(task_id),
        "stock_code": str(stock_code),
        "volume": int(volume),
        "price": format(float(price), ".8f"),
        "is_buy": int(is_buy),
        "order_type": str(order_type),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def api_order_status_payload(
    order: Mapping[str, Any] | None,
    *,
    idempotent_replay: bool = False,
) -> dict[str, Any]:
    """Normalize persisted bridge data without claiming an order is filled."""
    row = dict(order or {})
    return {
        "order_id": int(row.get("id") or 0),
        "client_order_id": str(row.get("client_order_id") or ""),
        "task_id": row.get("task_id"),
        "strategy_code": row.get("strategy_code"),
        "stock_code": row.get("security_code"),
        "volume": int(row.get("volume") or 0),
        "price": float(row.get("price") or 0),
        "is_buy": int(row.get("is_buy") or 0),
        "submission_state": str(row.get("submission_state") or "received"),
        "broker_order_id": str(row.get("broker_order_id") or row.get("fix_result_order_id") or ""),
        "broker_status": str(row.get("broker_status") or ""),
        "broker_status_message": str(row.get("status_msg") or ""),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
        "idempotent_replay": bool(idempotent_replay),
    }
