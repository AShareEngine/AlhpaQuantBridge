import math
import os
import threading
import time
from datetime import datetime

try:
    from pyapp.pkg.xtquant import xtdata

    XTQUANT_DATA_AVAILABLE = True
    XTQUANT_IMPORT_ERROR = None
except Exception as exc:
    xtdata = None
    XTQUANT_DATA_AVAILABLE = False
    XTQUANT_IMPORT_ERROR = exc


KLINE_FIELDS = [
    "time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "amount",
    "settle",
    "openInterest",
    "preClose",
    "suspendFlag",
]

TICK_FIELDS = [
    "time",
    "lastPrice",
    "open",
    "high",
    "low",
    "lastClose",
    "amount",
    "volume",
    "pvolume",
    "openInt",
    "stockStatus",
    "lastSettlementPrice",
    "askPrice",
    "bidPrice",
    "askVol",
    "bidVol",
    "transactionNum",
]

CONNECT_JOIN_TIMEOUT_SECONDS = 5.0
CONNECT_RETRY_COOLDOWN_SECONDS = 5.0


class DataServiceException(Exception):
    def __init__(
        self,
        message,
        error_code="DATA_SERVICE_ERROR",
        status_code=400,
    ):
        super().__init__(message)
        self.error_code = error_code
        self.status_code = status_code


def _is_nan(value):
    try:
        return isinstance(value, float) and math.isnan(value)
    except Exception:
        return False


def normalize_scalar(value):
    if value is None:
        return None
    if _is_nan(value):
        return None
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except Exception:
            return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "to_pydatetime"):
        try:
            return value.to_pydatetime().isoformat()
        except Exception:
            pass
    if hasattr(value, "item"):
        try:
            return normalize_scalar(value.item())
        except Exception:
            pass
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def normalize_jsonable(value):
    value = normalize_scalar(value)
    if isinstance(value, dict):
        return {str(key): normalize_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [normalize_jsonable(item) for item in value]
    if hasattr(value, "tolist") and not isinstance(value, (str, bytes, dict)):
        try:
            return normalize_jsonable(value.tolist())
        except Exception:
            pass
    return value


def to_epoch_ms(value):
    value = normalize_scalar(value)
    if value in (None, ""):
        return int(time.time() * 1000)
    if isinstance(value, datetime):
        return int(value.timestamp() * 1000)
    if isinstance(value, (int, float)):
        if value > 1_000_000_000_000:
            return int(value)
        if value > 1_000_000_000:
            return int(float(value) * 1000)
    value_str = str(value)
    normalized_str = value_str.replace("T", " ").split(".")[0]
    for fmt, length in (
        ("%Y%m%d%H%M%S", 14),
        ("%Y%m%d", 8),
        ("%Y-%m-%d %H:%M:%S", 19),
        ("%Y-%m-%d", 10),
    ):
        try:
            return int(datetime.strptime(normalized_str[:length], fmt).timestamp() * 1000)
        except ValueError:
            continue
    return int(time.time() * 1000)


def normalize_sequence(value):
    value = normalize_scalar(value)
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if hasattr(value, "tolist") and not isinstance(value, (str, bytes, dict)):
        try:
            normalized = value.tolist()
            if normalized is None:
                return []
            if isinstance(normalized, list):
                return normalized
            if isinstance(normalized, tuple):
                return list(normalized)
            return [normalized]
        except Exception:
            pass
    return [value]


def normalize_mapping(value):
    value = normalize_scalar(value)
    if value is None:
        return {}
    if isinstance(value, dict):
        return {str(key): normalize_jsonable(item) for key, item in value.items()}
    if hasattr(value, "to_dict"):
        try:
            return normalize_mapping(value.to_dict())
        except Exception:
            pass
    try:
        return {str(key): normalize_jsonable(item) for key, item in dict(value).items()}
    except Exception:
        return {"value": normalize_jsonable(value)}


def normalize_records(value):
    value = normalize_scalar(value)
    if value is None:
        return []
    if hasattr(value, "reset_index") and hasattr(value, "to_dict"):
        try:
            return [
                {str(key): normalize_jsonable(item) for key, item in record.items()}
                for record in value.reset_index().to_dict("records")
            ]
        except Exception:
            pass
    if hasattr(value, "to_dict"):
        try:
            records = value.to_dict("records")
            return [
                {str(key): normalize_jsonable(item) for key, item in record.items()}
                for record in records
            ]
        except Exception:
            pass
    return [normalize_mapping(item) for item in normalize_sequence(value)]


class XtDataGateway:
    def __init__(self):
        self._initialized = False
        self._connect_lock = threading.RLock()
        self._connect_thread = None
        self._last_connect_error = None
        self._last_connect_failure_at = 0.0

    def _resolve_data_dir(self, path):
        if not path:
            return ""
        normalized = os.path.abspath(os.path.expanduser(path))
        if os.path.basename(normalized).lower() == "datadir":
            return normalized
        if os.path.basename(normalized).lower() == "userdata_mini":
            return os.path.join(normalized, "datadir")
        userdata_path = os.path.join(normalized, "userdata_mini", "datadir")
        if os.path.exists(userdata_path):
            return userdata_path
        return os.path.join(normalized, "datadir")

    def _configure_xtdata(self):
        if not XTQUANT_DATA_AVAILABLE:
            return
        xtdata.enable_hello = False

        data_path = os.getenv("XTDATA_DATA_DIR") or os.getenv("QMT_USERDATA_PATH")
        if not data_path:
            try:
                from api.global_params import G

                data_path = (G.orm.get_setting_config() or {}).get("mini_qmt_path")
            except Exception:
                data_path = ""

        if data_path:
            xtdata.data_dir = self._resolve_data_dir(data_path)

    def _connect_worker(self):
        try:
            client = xtdata.connect()
        except Exception as exc:
            self._initialized = False
            self._last_connect_error = str(exc)
            self._last_connect_failure_at = time.monotonic()
            return

        connected = bool(client and hasattr(client, "is_connected") and client.is_connected())
        self._initialized = connected
        if connected:
            self._last_connect_error = None
            return

        self._last_connect_error = "xtdata.connect() did not yield a connected client"
        self._last_connect_failure_at = time.monotonic()

    def _start_connect_thread_locked(self):
        if self._connect_thread and self._connect_thread.is_alive():
            return self._connect_thread

        if self._last_connect_failure_at:
            retry_after = self._last_connect_failure_at + CONNECT_RETRY_COOLDOWN_SECONDS
            if time.monotonic() < retry_after:
                return None

        self._configure_xtdata()
        thread = threading.Thread(target=self._connect_worker, daemon=True, name="xtdata-connect")
        self._connect_thread = thread
        thread.start()
        return thread

    def ensure_ready(self):
        if not XTQUANT_DATA_AVAILABLE:
            message = "xtquant.xtdata is unavailable"
            if XTQUANT_IMPORT_ERROR:
                message = f"{message}: {XTQUANT_IMPORT_ERROR}"
            raise DataServiceException(message, "XTDATA_UNAVAILABLE", 503)

        if self._initialized:
            return

        with self._connect_lock:
            if self._initialized:
                return
            thread = self._start_connect_thread_locked()

        if thread is not None:
            thread.join(timeout=CONNECT_JOIN_TIMEOUT_SECONDS)
            if thread.is_alive():
                self._last_connect_error = "xtdata.connect() timed out"

        if not self._initialized:
            reason = f": {self._last_connect_error}" if self._last_connect_error else ""
            raise DataServiceException(
                "xtdata is unavailable; verify xtquant installation, QMT login state, and MiniQMT path"
                + reason,
                "XTDATA_UNAVAILABLE",
                503,
            )

    def _require_feature(self, name):
        self.ensure_ready()
        func = getattr(xtdata, name, None)
        if func is None:
            raise DataServiceException(
                f"{name} is not supported by the current QMT client",
                "FEATURE_NOT_SUPPORTED",
                501,
            )
        return func

    def _call_feature(self, name, *args, **kwargs):
        func = self._require_feature(name)
        try:
            return func(*args, **kwargs)
        except RuntimeError as exc:
            if self._is_feature_not_supported_error(exc):
                raise DataServiceException(
                    f"{name} is not supported by the current QMT client",
                    "FEATURE_NOT_SUPPORTED",
                    501,
                )
            raise

    def get_kline_history(
        self,
        symbols,
        period="1d",
        start_time="",
        end_time="",
        fields=None,
        adjust_type="none",
        fill_data=True,
    ):
        fields = fields or []
        raw = self._call_feature(
            "get_market_data",
            field_list=fields,
            stock_list=symbols,
            period=period,
            start_time=start_time,
            end_time=end_time,
            count=-1,
            dividend_type=adjust_type,
            fill_data=fill_data,
        )
        return self._format_kline_history(raw, symbols, fields)

    def get_tick_history(
        self,
        symbols,
        start_time="",
        end_time="",
        fields=None,
        adjust_type="none",
    ):
        fields = fields or []
        raw = self._call_feature(
            "get_market_data",
            field_list=fields,
            stock_list=symbols,
            period="tick",
            start_time=start_time,
            end_time=end_time,
            count=-1,
            dividend_type=adjust_type,
            fill_data=False,
        )
        return self._format_tick_history(raw, symbols, fields)

    def get_full_tick_snapshot(self, symbols):
        raw = self._call_feature("get_full_tick", symbols)
        return [
            {"symbol": symbol, "tick": self._normalize_tick_payload(payload)}
            for symbol, payload in (raw or {}).items()
        ]

    def get_market_data_ex(
        self,
        symbols,
        period="1d",
        start_time="",
        end_time="",
        count=-1,
        fields=None,
        adjust_type="none",
        fill_data=True,
    ):
        fields = fields or []
        raw = self._call_feature(
            "get_market_data_ex",
            field_list=fields,
            stock_list=symbols,
            period=period,
            start_time=start_time,
            end_time=end_time,
            count=count,
            dividend_type=adjust_type,
            fill_data=fill_data,
        )
        return self._format_frame_map(raw, symbols, fields)

    def get_local_data(
        self,
        symbols,
        period="1d",
        start_time="",
        end_time="",
        count=-1,
        fields=None,
        adjust_type="none",
        fill_data=True,
    ):
        fields = fields or []
        raw = self._call_feature(
            "get_local_data",
            field_list=fields,
            stock_list=symbols,
            period=period,
            start_time=start_time,
            end_time=end_time,
            count=count,
            dividend_type=adjust_type,
            fill_data=fill_data,
        )
        return self._format_frame_map(raw, symbols, fields)

    def get_full_kline(
        self,
        symbols,
        period="1m",
        start_time="",
        end_time="",
        count=1,
        fields=None,
        adjust_type="none",
        fill_data=True,
    ):
        fields = fields or []
        raw = self._call_feature(
            "get_full_kline",
            field_list=fields,
            stock_list=symbols,
            period=period,
            start_time=start_time,
            end_time=end_time,
            count=count,
            dividend_type=adjust_type,
            fill_data=fill_data,
        )
        return self._format_kline_history(raw, symbols, fields)

    def get_financial_data(self, symbols, table_names, start_time="", end_time=""):
        raw = self._call_feature(
            "get_financial_data",
            symbols,
            table_list=table_names,
            start_time=start_time,
            end_time=end_time,
        )
        items = []
        for symbol, table_map in (raw or {}).items():
            for table_name, frame in (table_map or {}).items():
                rows = normalize_records(frame)
                columns = [str(column) for column in getattr(frame, "columns", [])]
                items.append(
                    {
                        "symbol": symbol,
                        "table_name": table_name,
                        "columns": columns,
                        "rows": rows,
                    }
                )
        return items

    def get_instrument_detail(self, symbol, complete=False):
        detail = self._call_feature("get_instrument_detail", symbol, iscomplete=complete) or {}
        return {"symbol": symbol, "fields": normalize_mapping(detail)}

    def get_instrument_type(self, symbol):
        return {
            "symbol": symbol,
            "type": normalize_mapping(self._call_feature("get_instrument_type", symbol)),
        }

    def get_trade_times(self, symbol):
        return {
            "symbol": symbol,
            "trade_times": normalize_jsonable(self._call_feature("get_trading_time", symbol)),
        }

    def get_main_contract(self, code_market, start_time="", end_time=""):
        raw = self._call_feature("get_main_contract", code_market, start_time=start_time, end_time=end_time)
        return {"code_market": code_market, "main_contract": normalize_jsonable(raw)}

    def get_trading_calendar(self, market, start_time="", end_time=""):
        dates = self._call_feature("get_trading_calendar", market, start_time, end_time)
        return {"market": market, "dates": [str(item) for item in (dates or [])]}

    def get_trading_dates(self, market, start_time="", end_time="", count=-1):
        dates = self._call_feature("get_trading_dates", market, start_time, end_time, count)
        return {"market": market, "dates": [str(item) for item in (dates or [])]}

    def get_holidays(self):
        return [str(item) for item in (self._call_feature("get_holidays") or [])]

    def get_index_weight(self, index_code):
        data = self._call_feature("get_index_weight", index_code) or {}
        components = [
            {"symbol": str(symbol), "weight": normalize_scalar(weight)}
            for symbol, weight in data.items()
        ]
        return {"index_code": index_code, "components": components}

    def get_period_list(self):
        return [str(item) for item in (self._call_feature("get_period_list") or [])]

    def get_data_dir(self):
        return {"data_dir": str(self._call_feature("get_data_dir") or "")}

    def get_sector_list(self, sector_name=None):
        normalized_sector_name = sector_name.strip() if isinstance(sector_name, str) else None
        if normalized_sector_name:
            symbols = self._call_feature("get_stock_list_in_sector", normalized_sector_name) or []
            return [{"sector_name": normalized_sector_name, "symbols": [str(item) for item in symbols]}]

        sectors = self._call_feature("get_sector_list") or []
        result = []
        for name in sectors:
            try:
                symbols = xtdata.get_stock_list_in_sector(name) or []
            except Exception:
                symbols = []
            result.append({"sector_name": str(name), "symbols": [str(item) for item in symbols]})
        return result

    def get_divid_factors(self, stock_code, start_time="", end_time=""):
        raw = self._call_feature(
            "get_divid_factors",
            stock_code,
            start_time=start_time,
            end_time=end_time,
        )
        return {"stock_code": stock_code, "items": normalize_records(raw)}

    def get_cb_info(self, symbol):
        raw = self._call_feature("get_cb_info", symbol)
        return {"symbol": symbol, "fields": normalize_mapping(raw)}

    def get_ipo_info(self, start_time="", end_time=""):
        raw = self._call_feature("get_ipo_info", start_time=start_time, end_time=end_time)
        return normalize_records(raw)

    def get_etf_info(self, symbol=None):
        raw = self._call_feature("get_etf_info") or {}
        if symbol:
            return {"symbol": symbol, "fields": normalize_mapping(raw.get(symbol, {}))}
        return normalize_mapping(raw)

    def get_l2_quote(self, symbols, start_time="", end_time="", count=-1, fields=None):
        fields = fields or []
        items = []
        for symbol in symbols:
            payload = self._call_feature(
                "get_l2_quote",
                field_list=fields,
                stock_code=symbol,
                start_time=start_time,
                end_time=end_time,
                count=count,
            )
            for record in normalize_sequence(payload):
                items.append({"symbol": symbol, "quote": self._normalize_tick_payload(record)})
        return items

    def get_l2_order(self, symbols, start_time="", end_time="", count=-1, fields=None):
        fields = fields or []
        items = []
        for symbol in symbols:
            payload = self._call_feature(
                "get_l2_order",
                field_list=fields,
                stock_code=symbol,
                start_time=start_time,
                end_time=end_time,
                count=count,
            )
            records = [self._normalize_l2_order(item) for item in normalize_sequence(payload)]
            items.append({"symbol": symbol, "orders": records})
        return items

    def get_l2_transaction(self, symbols, start_time="", end_time="", count=-1, fields=None):
        fields = fields or []
        items = []
        for symbol in symbols:
            payload = self._call_feature(
                "get_l2_transaction",
                field_list=fields,
                stock_code=symbol,
                start_time=start_time,
                end_time=end_time,
                count=count,
            )
            records = [self._normalize_l2_transaction(item) for item in normalize_sequence(payload)]
            items.append({"symbol": symbol, "transactions": records})
        return items

    def download_history_data(
        self,
        stock_code,
        period="1d",
        start_time="",
        end_time="",
        incrementally=False,
    ):
        result = self._call_feature(
            "download_history_data",
            stock_code,
            period=period,
            start_time=start_time,
            end_time=end_time,
            incrementally=incrementally,
        )
        return self._download_result("download_history_data", result)

    def download_history_data_batch(
        self,
        symbols,
        period="1d",
        start_time="",
        end_time="",
        incrementally=False,
    ):
        if getattr(xtdata, "download_history_data2", None):
            result = self._call_feature(
                "download_history_data2",
                symbols,
                period=period,
                start_time=start_time,
                end_time=end_time,
                incrementally=incrementally,
            )
            return self._download_result("download_history_data2", result)

        result = [
            self._call_feature(
                "download_history_data",
                symbol,
                period=period,
                start_time=start_time,
                end_time=end_time,
                incrementally=incrementally,
            )
            for symbol in symbols
        ]
        return self._download_result("download_history_data", result)

    def download_financial_data(self, symbols, table_names=None, start_time="", end_time=""):
        table_names = table_names or []
        if getattr(xtdata, "download_financial_data2", None):
            result = self._call_feature(
                "download_financial_data2",
                symbols,
                table_list=table_names,
                start_time=start_time,
                end_time=end_time,
            )
            return self._download_result("download_financial_data2", result)

        result = self._call_feature(
            "download_financial_data",
            symbols,
            table_list=table_names,
            start_time=start_time,
            end_time=end_time,
        )
        return self._download_result("download_financial_data", result)

    def download_index_weight(self, index_code=None):
        try:
            result = self._call_feature("download_index_weight", index_code)
        except TypeError:
            result = self._call_feature("download_index_weight")
        return self._download_result("download_index_weight", result)

    def download_history_contracts(self, market=None):
        try:
            result = self._call_feature("download_history_contracts", market)
        except TypeError:
            result = self._call_feature("download_history_contracts")
        return self._download_result("download_history_contracts", result)

    def download_sector_data(self, sector_name=None):
        try:
            result = self._call_feature("download_sector_data", sector_name)
        except TypeError:
            result = self._call_feature("download_sector_data")
        return self._download_result("download_sector_data", result)

    def download_holiday_data(self):
        result = self._call_feature("download_holiday_data")
        return self._download_result("download_holiday_data", result)

    def download_cb_data(self):
        result = self._call_feature("download_cb_data")
        return self._download_result("download_cb_data", result)

    def download_etf_info(self):
        result = self._call_feature("download_etf_info")
        return self._download_result("download_etf_info", result)

    def _format_frame_map(self, data, symbols, requested_fields):
        if not isinstance(data, dict) or not data:
            return []
        result = []
        for symbol in symbols:
            value = data.get(symbol)
            if value is None:
                continue
            result.append(
                {
                    "symbol": symbol,
                    "fields": requested_fields,
                    "rows": normalize_records(value),
                }
            )
        return result

    def _format_kline_history(self, data, symbols, requested_fields):
        if not isinstance(data, dict) or not data:
            return []

        frame_map = {}
        for field in KLINE_FIELDS:
            if field in data:
                frame_map[field] = data[field]
        if not frame_map:
            return self._format_frame_map(data, symbols, requested_fields)

        first_frame = next(iter(frame_map.values()))
        columns = list(getattr(first_frame, "columns", []))
        result = []
        for symbol in symbols:
            if hasattr(first_frame, "index") and symbol not in first_frame.index:
                continue
            bars = []
            for column in columns:
                bar = {"time_ms": to_epoch_ms(column)}
                for field, frame in frame_map.items():
                    if field == "time":
                        continue
                    try:
                        value = frame.loc[symbol, column]
                    except Exception:
                        continue
                    key = self._snake_case_field(field)
                    normalized = normalize_scalar(value)
                    if key in {"volume", "open_interest", "suspend_flag"}:
                        bar[key] = int(normalized or 0)
                    elif normalized is None:
                        bar[key] = None
                    else:
                        bar[key] = float(normalized)
                bars.append(bar)
            result.append({"symbol": symbol, "fields": requested_fields or KLINE_FIELDS, "bars": bars})
        return result

    def _format_tick_history(self, data, symbols, requested_fields):
        if not isinstance(data, dict) or not data:
            return []
        result = []
        for symbol in symbols:
            rows = data.get(symbol)
            if rows is None:
                continue
            ticks = []
            if hasattr(rows, "dtype") and getattr(rows.dtype, "names", None):
                available_fields = list(rows.dtype.names)
                selected_fields = requested_fields or available_fields
                for row in rows:
                    item = {
                        field: normalize_scalar(row[field])
                        for field in selected_fields
                        if field in available_fields
                    }
                    ticks.append(self._normalize_tick_payload(item))
            elif hasattr(rows, "to_dict"):
                for record in rows.to_dict("records"):
                    ticks.append(self._normalize_tick_payload(record))
            else:
                for row in normalize_sequence(rows):
                    ticks.append(self._normalize_tick_payload(row))
            result.append({"symbol": symbol, "fields": requested_fields or TICK_FIELDS, "ticks": ticks})
        return result

    def _normalize_tick_payload(self, payload):
        payload = normalize_mapping(payload)
        return {
            "time_ms": to_epoch_ms(payload.get("time")),
            "last_price": self._float(payload.get("lastPrice", payload.get("last_price", 0.0))),
            "open": self._float(payload.get("open", 0.0)),
            "high": self._float(payload.get("high", 0.0)),
            "low": self._float(payload.get("low", 0.0)),
            "last_close": self._float(payload.get("lastClose", payload.get("last_close", 0.0))),
            "amount": self._float(payload.get("amount", 0.0)),
            "volume": self._int(payload.get("volume", 0)),
            "pvolume": self._int(payload.get("pvolume", 0)),
            "open_int": self._int(payload.get("openInt", payload.get("open_int", 0))),
            "stock_status": self._int(payload.get("stockStatus", payload.get("stock_status", 0))),
            "last_settlement_price": self._float(
                payload.get("lastSettlementPrice", payload.get("last_settlement_price", 0.0))
            ),
            "ask_price": self._levels(payload, "askPrice", "ask_price"),
            "bid_price": self._levels(payload, "bidPrice", "bid_price"),
            "ask_vol": [self._int(item) for item in self._levels(payload, "askVol", "ask_vol", as_float=False)],
            "bid_vol": [self._int(item) for item in self._levels(payload, "bidVol", "bid_vol", as_float=False)],
            "transaction_num": self._int(
                payload.get("transactionNum", payload.get("transaction_num", 0))
            ),
        }

    def _normalize_l2_order(self, payload):
        payload = normalize_mapping(payload)
        return {
            "time_ms": to_epoch_ms(payload.get("time")),
            "price": self._float(payload.get("price", 0.0)),
            "volume": self._int(payload.get("volume", 0)),
            "entrust_no": self._int(payload.get("entrustNo", payload.get("entrust_no", 0))),
            "entrust_type": self._int(payload.get("entrustType", payload.get("entrust_type", 0))),
            "entrust_direction": self._int(
                payload.get("entrustDirection", payload.get("entrust_direction", 0))
            ),
        }

    def _normalize_l2_transaction(self, payload):
        payload = normalize_mapping(payload)
        return {
            "time_ms": to_epoch_ms(payload.get("time")),
            "price": self._float(payload.get("price", 0.0)),
            "volume": self._int(payload.get("volume", 0)),
            "amount": self._float(payload.get("amount", 0.0)),
            "trade_index": self._int(payload.get("tradeIndex", payload.get("trade_index", 0))),
            "buy_no": self._int(payload.get("buyNo", payload.get("buy_no", 0))),
            "sell_no": self._int(payload.get("sellNo", payload.get("sell_no", 0))),
            "trade_type": self._int(payload.get("tradeType", payload.get("trade_type", 0))),
            "trade_flag": self._int(payload.get("tradeFlag", payload.get("trade_flag", 0))),
        }

    def _download_result(self, name, result=None):
        return {"function": name, "success": True, "result": normalize_jsonable(result)}

    def _levels(self, payload, camel_key, snake_key, as_float=True):
        value = payload.get(camel_key, payload.get(snake_key))
        if value is not None:
            items = normalize_sequence(value)
        else:
            items = []
            for index in range(1, 11):
                item = payload.get(f"{camel_key}{index}", payload.get(f"{snake_key}{index}"))
                if item is not None:
                    items.append(item)
        if as_float:
            return [self._float(item) for item in items]
        return [self._int(item) for item in items]

    def _float(self, value):
        value = normalize_scalar(value)
        try:
            if value is None:
                return 0.0
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _int(self, value):
        value = normalize_scalar(value)
        try:
            if value is None:
                return 0
            return int(float(value))
        except (TypeError, ValueError):
            return 0

    def _snake_case_field(self, field):
        mapping = {
            "openInterest": "open_interest",
            "preClose": "pre_close",
            "suspendFlag": "suspend_flag",
        }
        return mapping.get(field, field)

    def _is_feature_not_supported_error(self, exc):
        message = str(exc).lower()
        return (
            "function not realize" in message
            or "未找到处理函数" in message
            or "当前客户端未支持此功能" in message
        )
