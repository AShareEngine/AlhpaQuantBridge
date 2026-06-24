from flask import Flask, jsonify, request
import threading
from datetime import datetime
from api.global_params import G
from api.httpserver.xtdata_gateway import DataServiceException, XtDataGateway


class APIService:
    TASK_FILTER_FIELDS = {
        "id": "int",
        "account_id": "int",
        "user_id": "str",
        "strategy_code": "str",
        "task_type": "int",
        "platform": "int",
        "is_open": "int",
        "order_count_type": "int",
    }
    TASK_MUTABLE_FIELDS = {
        "name": "str",
        "account_id": "int",
        "strategy_code": "str",
        "order_count_type": "int",
        "dynamic_calculation_type": "int",
        "strategy_amount": "float",
        "position_amount": "float",
        "allocation_amount": "float",
        "can_use_amount": "float",
        "accruing_amounts": "float",
        "enable": "int",
        "days_number": "int",
        "service_charge": "float",
        "lower_limit_of_fees": "float",
        "backtest_id": "int",
        "mock_service_charge": "float",
        "mock_lower_limit_of_fees": "float",
        "mock_allocation_amount": "float",
        "user_id": "str",
        "is_simulation": "int",
        "position_ratio": "float",
        "platform": "int",
        "open_mandatory_limit_order": "int",
        "task_type": "int",
        "host_user_email": "str",
        "share_secret": "str",
        "strategy_keys_id": "int",
        "is_open": "int",
    }
    POSITION_MUTABLE_FIELDS = {
        "security_code": "str",
        "volume": "int",
        "amount": "float",
        "task_id": "int",
        "average_price": "float",
        "backtest_id": "int",
        "is_mock": "int",
    }

    def __init__(self, trade_controller, api_handler=None):
        self.app = Flask(__name__)
        self.server = None
        self.thread = None
        self.trade_controller = trade_controller
        self.api_handler = api_handler
        self.data_gateway = XtDataGateway()
        self._register_routes()
        self._register_data_routes()
        self._is_running = False

        import logging

        class FlaskLogHandler(logging.Handler):
            def emit(self, record):
                log_message = self.format(record)
                log_message = (
                    log_message.split("] ")[1] if "] " in log_message else log_message
                )
                G.logger.info("api调用： " + log_message, extra={"showMessage": True})

        werkzeug_logger = logging.getLogger("werkzeug")
        handler = FlaskLogHandler()
        handler.setLevel(logging.INFO)
        werkzeug_logger.addHandler(handler)

    def _success(self, data=None, message="success", status_code=200):
        return (
            jsonify(
                {
                    "code": status_code,
                    "success": 200 <= status_code < 300,
                    "message": message,
                    "timestamp": datetime.now().isoformat(),
                    "data": data,
                }
            ),
            status_code,
        )

    def _error(self, message, status_code=400, data=None):
        return (
            jsonify(
                {
                    "code": status_code,
                    "success": False,
                    "message": message,
                    "timestamp": datetime.now().isoformat(),
                    "error": message,
                    "data": data,
                }
            ),
            status_code,
        )

    def _coerce_value(self, key, value, value_type):
        if value == "":
            value = None

        if value_type == "str":
            return value.strip() if isinstance(value, str) else value

        if value is None:
            return None

        if value_type == "int":
            if isinstance(value, str) and value.lower() in ("true", "false"):
                return 1 if value.lower() == "true" else 0
            return int(value)

        if value_type == "float":
            return float(value)

        raise ValueError(f"unsupported value type for {key}")

    def _normalize_payload(self, source, field_map):
        payload = {}
        for key, value_type in field_map.items():
            if key not in source:
                continue
            try:
                payload[key] = self._coerce_value(key, source.get(key), value_type)
            except (TypeError, ValueError):
                return None, f"{key} format is invalid"
        return payload, None

    def _apply_api_task_defaults(self, payload):
        payload.setdefault("platform", 10)
        payload.setdefault("task_type", 1)
        payload.setdefault("user_id", G.unique_id)
        payload.setdefault("order_count_type", 2)
        payload.setdefault("dynamic_calculation_type", 1)
        payload.setdefault("position_ratio", 1)
        payload.setdefault("open_mandatory_limit_order", 1)
        payload.setdefault("service_charge", 0.00025)
        payload.setdefault("lower_limit_of_fees", 5)
        allocation_amount = payload.get("allocation_amount", 100000)
        payload.setdefault("allocation_amount", allocation_amount)
        payload.setdefault("can_use_amount", allocation_amount)
        payload.setdefault("accruing_amounts", allocation_amount)
        payload.setdefault("mock_allocation_amount", allocation_amount)
        payload.setdefault("mock_service_charge", payload.get("service_charge", 0.00025))
        payload.setdefault("mock_lower_limit_of_fees", payload.get("lower_limit_of_fees", 5))
        return payload

    def _parse_request_filters(self, args, field_map):
        filters = {}
        for key, value_type in field_map.items():
            if key not in args:
                continue
            raw_value = args.get(key)
            if raw_value in (None, ""):
                continue
            try:
                filters[key] = self._coerce_value(key, raw_value, value_type)
            except (TypeError, ValueError):
                return None, f"{key} format is invalid"
        return filters, None

    def _get_task_by_identifier(self, task_id=None, strategy_code=None):
        if task_id not in (None, ""):
            try:
                task_id = int(task_id)
            except (TypeError, ValueError):
                return None, "task_id must be an integer", 400

            task = G.orm.get_task_detail({"id": task_id})
            if not task or task.get("delete_time"):
                return None, "task not found", 404
            return task, None, None

        if isinstance(strategy_code, str):
            strategy_code = strategy_code.strip()

        if not strategy_code:
            return None, "task_id or strategy_code is required", 400

        task_list = G.orm.get_task_list({"strategy_code": strategy_code})
        if not task_list:
            return None, "task not found", 404
        return task_list[0], None, None

    def _get_account_by_identifier(self, account_id=None, task_id=None, strategy_code=None):
        if account_id not in (None, ""):
            try:
                account_id = int(account_id)
            except (TypeError, ValueError):
                return None, "account_id must be an integer", 400
        elif task_id not in (None, "") or strategy_code not in (None, ""):
            task, error_message, status_code = self._get_task_by_identifier(
                task_id=task_id, strategy_code=strategy_code
            )
            if error_message:
                return None, error_message, status_code
            account_id = task.get("account_id")
        else:
            return None, "account_id or task_id or strategy_code is required", 400

        if account_id in (None, ""):
            return None, "task is not bound to an account", 400

        account = G.orm.get_account_by_id(account_id)
        if not account:
            return None, "account not found", 404
        return account, None, None

    def _ensure_api_handler(self):
        return self.api_handler is not None

    def _get_task_positions(self, task_id):
        if self._ensure_api_handler():
            return self.api_handler.get_position_by_task_id(task_id)
        return G.orm.query_position_by_task_id(task_id)

    def _update_task_fields(self, task_id, raw_data):
        payload, error_message = self._normalize_payload(raw_data, self.TASK_MUTABLE_FIELDS)
        if error_message:
            return None, error_message, 400
        if not payload:
            return None, "no valid task fields were provided", 400

        task = G.orm.get_task_detail({"id": task_id})
        if not task or task.get("delete_time"):
            return None, "task not found", 404

        if "position_ratio" in payload and task.get("order_count_type") != 1:
            return (
                None,
                "only order_count_type=1 tasks support position_ratio adjustment",
                400,
            )

        ok = G.orm.update_task(task_id, **payload)
        if not ok:
            return None, "update task failed", 500

        updated_task = G.orm.get_task_detail({"id": task_id})
        return updated_task, None, None

    def _build_account_overview(self):
        accounts = G.orm.get_account_list()
        account_items = []
        summary = {
            "cash": 0.0,
            "frozen_cash": 0.0,
            "market_value": 0.0,
            "total_asset": 0.0,
        }

        for account in accounts:
            if self._ensure_api_handler():
                fund = self.api_handler.get_account_info(account["id"])
            else:
                fund = {
                    "cash": 0,
                    "frozen_cash": 0,
                    "market_value": 0,
                    "total_asset": 0,
                }
            account_item = dict(account)
            account_item["fund"] = fund
            account_items.append(account_item)

            for key in summary:
                summary[key] += float((fund or {}).get(key) or 0)

        return {
            "summary": summary,
            "accounts": account_items,
        }

    def _as_list(self, value):
        if value in (None, ""):
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, tuple):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return [str(value).strip()]

    def _as_bool(self, value, default=False):
        if value in (None, ""):
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in ("1", "true", "yes", "y", "on"):
                return True
            if normalized in ("0", "false", "no", "n", "off"):
                return False
        return default

    def _as_int(self, value, default=0):
        if value in (None, ""):
            return default
        return int(value)

    def _as_str(self, value, default=""):
        if value in (None, ""):
            return default
        return str(value).strip()

    def _json_body(self):
        data = request.get_json(silent=True)
        return data if isinstance(data, dict) else {}

    def _symbols_from_payload(self, payload, required=True):
        for key in ("symbols", "stock_list", "code_list"):
            symbols = self._as_list(payload.get(key))
            if symbols:
                return symbols, None

        for key in ("symbol", "stock_code", "code", "security_code"):
            symbol = self._as_str(payload.get(key))
            if symbol:
                return [symbol], None

        if required:
            return None, "symbols is required"
        return [], None

    def _market_data_params(self, payload):
        symbols, error_message = self._symbols_from_payload(payload)
        if error_message:
            return None, error_message
        try:
            return {
                "symbols": symbols,
                "period": self._as_str(payload.get("period"), "1d"),
                "start_time": self._as_str(payload.get("start_time")),
                "end_time": self._as_str(payload.get("end_time")),
                "count": self._as_int(payload.get("count"), -1),
                "fields": self._as_list(payload.get("fields")),
                "adjust_type": self._as_str(
                    payload.get("adjust_type", payload.get("dividend_type")),
                    "none",
                ),
                "fill_data": self._as_bool(payload.get("fill_data"), True),
            }, None
        except (TypeError, ValueError):
            return None, "count format is invalid"

    def _handle_data_result(self, callback, message):
        try:
            return self._success(callback(), message=message)
        except DataServiceException as exc:
            return self._error(
                str(exc),
                exc.status_code,
                {"error_code": exc.error_code},
            )
        except Exception as exc:
            G.logger.exception("data api failed")
            return self._error(
                f"data api failed: {str(exc)}",
                500,
                {"error_code": "DATA_SERVICE_ERROR"},
            )

    def _register_data_routes(self):
        @self.app.route("/api/v1/data/kline-history", methods=["POST"])
        def data_kline_history():
            payload = self._json_body()
            params, error_message = self._market_data_params(payload)
            if error_message:
                return self._error(error_message)

            return self._handle_data_result(
                lambda: {
                    "items": self.data_gateway.get_kline_history(
                        symbols=params["symbols"],
                        period=params["period"],
                        start_time=params["start_time"],
                        end_time=params["end_time"],
                        fields=params["fields"],
                        adjust_type=params["adjust_type"],
                        fill_data=params["fill_data"],
                    )
                },
                "获取 K 线历史成功",
            )

        @self.app.route("/api/v1/data/tick-history", methods=["POST"])
        def data_tick_history():
            payload = self._json_body()
            symbols, error_message = self._symbols_from_payload(payload)
            if error_message:
                return self._error(error_message)

            return self._handle_data_result(
                lambda: {
                    "items": self.data_gateway.get_tick_history(
                        symbols=symbols,
                        start_time=self._as_str(payload.get("start_time")),
                        end_time=self._as_str(payload.get("end_time")),
                        fields=self._as_list(payload.get("fields")),
                        adjust_type=self._as_str(
                            payload.get("adjust_type", payload.get("dividend_type")),
                            "none",
                        ),
                    )
                },
                "获取 Tick 历史成功",
            )

        @self.app.route("/api/v1/data/full-tick", methods=["POST"])
        def data_full_tick():
            payload = self._json_body()
            symbols, error_message = self._symbols_from_payload(payload)
            if error_message:
                return self._error(error_message)

            return self._handle_data_result(
                lambda: {"items": self.data_gateway.get_full_tick_snapshot(symbols)},
                "获取全量 Tick 快照成功",
            )

        @self.app.route("/api/v1/data/market-data-ex", methods=["POST"])
        def data_market_data_ex():
            payload = self._json_body()
            params, error_message = self._market_data_params(payload)
            if error_message:
                return self._error(error_message)

            return self._handle_data_result(
                lambda: {"items": self.data_gateway.get_market_data_ex(**params)},
                "获取扩展行情数据成功",
            )

        @self.app.route("/api/v1/data/local-data", methods=["POST"])
        def data_local_data():
            payload = self._json_body()
            params, error_message = self._market_data_params(payload)
            if error_message:
                return self._error(error_message)

            return self._handle_data_result(
                lambda: {"items": self.data_gateway.get_local_data(**params)},
                "获取本地行情数据成功",
            )

        @self.app.route("/api/v1/data/full-kline", methods=["POST"])
        def data_full_kline():
            payload = self._json_body()
            params, error_message = self._market_data_params(payload)
            if error_message:
                return self._error(error_message)
            if payload.get("count") in (None, ""):
                params["count"] = 1

            return self._handle_data_result(
                lambda: {"items": self.data_gateway.get_full_kline(**params)},
                "获取最新交易日 K 线成功",
            )

        @self.app.route("/api/v1/data/financial", methods=["POST"])
        def data_financial():
            payload = self._json_body()
            symbols, error_message = self._symbols_from_payload(payload)
            if error_message:
                return self._error(error_message)
            table_names = self._as_list(payload.get("table_names", payload.get("table_list")))
            if not table_names:
                return self._error("table_names is required")

            return self._handle_data_result(
                lambda: {
                    "items": self.data_gateway.get_financial_data(
                        symbols,
                        table_names,
                        start_time=self._as_str(payload.get("start_time")),
                        end_time=self._as_str(payload.get("end_time")),
                    )
                },
                "获取财务数据成功",
            )

        @self.app.route("/api/v1/data/instrument/<symbol>", methods=["GET"])
        def data_instrument(symbol):
            complete = self._as_bool(request.args.get("complete"), False)
            return self._handle_data_result(
                lambda: self.data_gateway.get_instrument_detail(symbol, complete=complete),
                "获取合约信息成功",
            )

        @self.app.route("/api/v1/data/instrument-type/<symbol>", methods=["GET"])
        def data_instrument_type(symbol):
            return self._handle_data_result(
                lambda: self.data_gateway.get_instrument_type(symbol),
                "获取合约类型成功",
            )

        @self.app.route("/api/v1/data/trade-times/<symbol>", methods=["GET"])
        def data_trade_times(symbol):
            return self._handle_data_result(
                lambda: self.data_gateway.get_trade_times(symbol),
                "获取交易时间段成功",
            )

        @self.app.route("/api/v1/data/main-contract/<code_market>", methods=["GET"])
        def data_main_contract(code_market):
            return self._handle_data_result(
                lambda: self.data_gateway.get_main_contract(
                    code_market,
                    start_time=self._as_str(request.args.get("start_time")),
                    end_time=self._as_str(request.args.get("end_time")),
                ),
                "获取主力合约成功",
            )

        @self.app.route("/api/v1/data/trading-calendar", methods=["POST"])
        def data_trading_calendar():
            payload = self._json_body()
            market = self._as_str(payload.get("market"))
            if not market:
                return self._error("market is required")

            return self._handle_data_result(
                lambda: self.data_gateway.get_trading_calendar(
                    market,
                    start_time=self._as_str(payload.get("start_time")),
                    end_time=self._as_str(payload.get("end_time")),
                ),
                "获取交易日历成功",
            )

        @self.app.route("/api/v1/data/trading-dates", methods=["POST"])
        def data_trading_dates():
            payload = self._json_body()
            market = self._as_str(payload.get("market"))
            if not market:
                return self._error("market is required")
            try:
                count = self._as_int(payload.get("count"), -1)
            except (TypeError, ValueError):
                return self._error("count format is invalid")

            return self._handle_data_result(
                lambda: self.data_gateway.get_trading_dates(
                    market,
                    start_time=self._as_str(payload.get("start_time")),
                    end_time=self._as_str(payload.get("end_time")),
                    count=count,
                ),
                "获取交易日列表成功",
            )

        @self.app.route("/api/v1/data/holidays", methods=["GET"])
        def data_holidays():
            return self._handle_data_result(
                lambda: {"items": self.data_gateway.get_holidays()},
                "获取节假日列表成功",
            )

        @self.app.route("/api/v1/data/index-weight", methods=["POST"])
        def data_index_weight():
            payload = self._json_body()
            index_code = self._as_str(payload.get("index_code"))
            if not index_code:
                return self._error("index_code is required")

            return self._handle_data_result(
                lambda: self.data_gateway.get_index_weight(index_code),
                "获取指数权重成功",
            )

        @self.app.route("/api/v1/data/periods", methods=["GET"])
        def data_periods():
            return self._handle_data_result(
                lambda: {"items": self.data_gateway.get_period_list()},
                "获取可用周期列表成功",
            )

        @self.app.route("/api/v1/data/data-dir", methods=["GET"])
        def data_data_dir():
            return self._handle_data_result(
                lambda: self.data_gateway.get_data_dir(),
                "获取数据目录成功",
            )

        @self.app.route("/api/v1/data/sectors", methods=["GET"])
        def data_sectors():
            return self._handle_data_result(
                lambda: {
                    "items": self.data_gateway.get_sector_list(
                        sector_name=request.args.get("sector_name")
                    )
                },
                "获取板块列表成功",
            )

        @self.app.route("/api/v1/data/divid-factors", methods=["POST"])
        def data_divid_factors():
            payload = self._json_body()
            stock_code = self._as_str(payload.get("stock_code", payload.get("symbol")))
            if not stock_code:
                return self._error("stock_code is required")

            return self._handle_data_result(
                lambda: self.data_gateway.get_divid_factors(
                    stock_code,
                    start_time=self._as_str(payload.get("start_time")),
                    end_time=self._as_str(payload.get("end_time")),
                ),
                "获取除权除息数据成功",
            )

        @self.app.route("/api/v1/data/cb-info/<symbol>", methods=["GET"])
        def data_cb_info(symbol):
            return self._handle_data_result(
                lambda: self.data_gateway.get_cb_info(symbol),
                "获取可转债信息成功",
            )

        @self.app.route("/api/v1/data/ipo-info", methods=["GET"])
        def data_ipo_info():
            return self._handle_data_result(
                lambda: {
                    "items": self.data_gateway.get_ipo_info(
                        start_time=self._as_str(request.args.get("start_time")),
                        end_time=self._as_str(request.args.get("end_time")),
                    )
                },
                "获取新股申购信息成功",
            )

        @self.app.route("/api/v1/data/etf-info", methods=["GET"])
        def data_etf_info_all():
            return self._handle_data_result(
                lambda: self.data_gateway.get_etf_info(),
                "获取 ETF 信息成功",
            )

        @self.app.route("/api/v1/data/etf-info/<symbol>", methods=["GET"])
        def data_etf_info(symbol):
            return self._handle_data_result(
                lambda: self.data_gateway.get_etf_info(symbol),
                "获取 ETF 信息成功",
            )

        @self.app.route("/api/v1/data/l2/quote", methods=["POST"])
        def data_l2_quote():
            payload = self._json_body()
            symbols, error_message = self._symbols_from_payload(payload)
            if error_message:
                return self._error(error_message)
            try:
                count = self._as_int(payload.get("count"), -1)
            except (TypeError, ValueError):
                return self._error("count format is invalid")

            return self._handle_data_result(
                lambda: {
                    "items": self.data_gateway.get_l2_quote(
                        symbols,
                        start_time=self._as_str(payload.get("start_time")),
                        end_time=self._as_str(payload.get("end_time")),
                        count=count,
                        fields=self._as_list(payload.get("fields")),
                    )
                },
                "获取 L2 快照成功",
            )

        @self.app.route("/api/v1/data/l2/order", methods=["POST"])
        def data_l2_order():
            payload = self._json_body()
            symbols, error_message = self._symbols_from_payload(payload)
            if error_message:
                return self._error(error_message)
            try:
                count = self._as_int(payload.get("count"), -1)
            except (TypeError, ValueError):
                return self._error("count format is invalid")

            return self._handle_data_result(
                lambda: {
                    "items": self.data_gateway.get_l2_order(
                        symbols,
                        start_time=self._as_str(payload.get("start_time")),
                        end_time=self._as_str(payload.get("end_time")),
                        count=count,
                        fields=self._as_list(payload.get("fields")),
                    )
                },
                "获取 L2 逐笔委托成功",
            )

        @self.app.route("/api/v1/data/l2/transaction", methods=["POST"])
        def data_l2_transaction():
            payload = self._json_body()
            symbols, error_message = self._symbols_from_payload(payload)
            if error_message:
                return self._error(error_message)
            try:
                count = self._as_int(payload.get("count"), -1)
            except (TypeError, ValueError):
                return self._error("count format is invalid")

            return self._handle_data_result(
                lambda: {
                    "items": self.data_gateway.get_l2_transaction(
                        symbols,
                        start_time=self._as_str(payload.get("start_time")),
                        end_time=self._as_str(payload.get("end_time")),
                        count=count,
                        fields=self._as_list(payload.get("fields")),
                    )
                },
                "获取 L2 逐笔成交成功",
            )

        @self.app.route("/api/v1/data/download/history", methods=["POST"])
        def data_download_history():
            payload = self._json_body()
            stock_code = self._as_str(payload.get("stock_code", payload.get("symbol")))
            if not stock_code:
                return self._error("stock_code is required")

            return self._handle_data_result(
                lambda: self.data_gateway.download_history_data(
                    stock_code,
                    period=self._as_str(payload.get("period"), "1d"),
                    start_time=self._as_str(payload.get("start_time")),
                    end_time=self._as_str(payload.get("end_time")),
                    incrementally=self._as_bool(payload.get("incrementally"), False),
                ),
                "下载历史行情数据成功",
            )

        @self.app.route("/api/v1/data/download/history/batch", methods=["POST"])
        def data_download_history_batch():
            payload = self._json_body()
            symbols, error_message = self._symbols_from_payload(payload)
            if error_message:
                return self._error(error_message)

            return self._handle_data_result(
                lambda: self.data_gateway.download_history_data_batch(
                    symbols,
                    period=self._as_str(payload.get("period"), "1d"),
                    start_time=self._as_str(payload.get("start_time")),
                    end_time=self._as_str(payload.get("end_time")),
                    incrementally=self._as_bool(payload.get("incrementally"), False),
                ),
                "批量下载历史行情数据成功",
            )

        @self.app.route("/api/v1/data/download/financial", methods=["POST"])
        def data_download_financial():
            payload = self._json_body()
            symbols, error_message = self._symbols_from_payload(payload)
            if error_message:
                return self._error(error_message)

            return self._handle_data_result(
                lambda: self.data_gateway.download_financial_data(
                    symbols,
                    table_names=self._as_list(payload.get("table_names", payload.get("table_list"))),
                    start_time=self._as_str(payload.get("start_time")),
                    end_time=self._as_str(payload.get("end_time")),
                ),
                "下载财务数据成功",
            )

        @self.app.route("/api/v1/data/download/index-weight", methods=["POST"])
        def data_download_index_weight():
            payload = self._json_body()
            return self._handle_data_result(
                lambda: self.data_gateway.download_index_weight(
                    index_code=self._as_str(payload.get("index_code")) or None
                ),
                "下载指数权重数据成功",
            )

        @self.app.route("/api/v1/data/download/history-contracts", methods=["POST"])
        def data_download_history_contracts():
            payload = self._json_body()
            return self._handle_data_result(
                lambda: self.data_gateway.download_history_contracts(
                    market=self._as_str(payload.get("market")) or None
                ),
                "下载历史合约数据成功",
            )

        @self.app.route("/api/v1/data/download/sector", methods=["POST"])
        def data_download_sector():
            payload = self._json_body()
            return self._handle_data_result(
                lambda: self.data_gateway.download_sector_data(
                    sector_name=self._as_str(payload.get("sector_name")) or None
                ),
                "下载板块数据成功",
            )

        @self.app.route("/api/v1/data/download/holiday", methods=["POST"])
        def data_download_holiday():
            return self._handle_data_result(
                lambda: self.data_gateway.download_holiday_data(),
                "下载节假日数据成功",
            )

        @self.app.route("/api/v1/data/download/cb", methods=["POST"])
        def data_download_cb():
            return self._handle_data_result(
                lambda: self.data_gateway.download_cb_data(),
                "下载可转债数据成功",
            )

        @self.app.route("/api/v1/data/download/etf", methods=["POST"])
        def data_download_etf():
            return self._handle_data_result(
                lambda: self.data_gateway.download_etf_info(),
                "下载 ETF 数据成功",
            )

    def _register_routes(self):
        @self.app.route("/api/shippings", methods=["GET"])
        @self.app.route("/api/tasks", methods=["GET"])
        def get_tasks():
            filters, error_message = self._parse_request_filters(
                request.args, self.TASK_FILTER_FIELDS
            )
            if error_message:
                return self._error(error_message)
            data = G.orm.get_task_list(filters or {})
            return self._success(data)

        @self.app.route("/api/tasks", methods=["POST"])
        def create_task():
            raw_data = request.get_json(silent=True) or {}
            payload, error_message = self._normalize_payload(
                raw_data, self.TASK_MUTABLE_FIELDS
            )
            if error_message:
                return self._error(error_message)
            if not payload:
                return self._error("request body is required")

            payload = self._apply_api_task_defaults(payload)
            ok = G.orm.create_task(payload)
            if not ok:
                return self._error("create task failed", 500)
            return self._success(True, message="task created")

        @self.app.route("/api/tasks/<int:task_id>", methods=["GET"])
        def get_task_detail(task_id):
            task = G.orm.get_task_detail({"id": task_id})
            if not task or task.get("delete_time"):
                return self._error("task not found", 404)
            return self._success(task)

        @self.app.route("/api/tasks/<int:task_id>", methods=["PUT"])
        def update_task(task_id):
            raw_data = request.get_json(silent=True) or {}
            task, error_message, status_code = self._update_task_fields(task_id, raw_data)
            if error_message:
                return self._error(error_message, status_code)
            return self._success(task, message="task updated")

        @self.app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
        def delete_task(task_id):
            task = G.orm.get_task_detail({"id": task_id})
            if not task or task.get("delete_time"):
                return self._error("task not found", 404)

            ok = G.orm.delete_task({"id": task_id})
            if not ok:
                return self._error("delete task failed", 500)
            return self._success(True, message="task deleted")

        @self.app.route("/api/tasks/<int:task_id>/run", methods=["POST"])
        def run_task(task_id):
            raw_data = request.get_json(silent=True) or {}
            is_open = raw_data.get("is_open")
            if is_open in (None, ""):
                return self._error("is_open is required")

            task = G.orm.get_task_detail({"id": task_id})
            if not task or task.get("delete_time"):
                return self._error("task not found", 404)

            try:
                is_open = self._coerce_value("is_open", is_open, "int")
            except (TypeError, ValueError):
                return self._error("is_open format is invalid")

            ok = G.orm.run_task(
                {"id": task_id, "is_open": is_open, "name": task.get("name", "")}
            )
            if not ok:
                return self._error("update task running state failed", 500)
            return self._success(True, message="task running state updated")

        @self.app.route("/api/positions", methods=["GET"])
        def get_positions():
            task_id = request.args.get("task_id")
            strategy_code = request.args.get("strategy_code")
            task, error_message, status_code = self._get_task_by_identifier(
                task_id=task_id, strategy_code=strategy_code
            )
            if error_message:
                return self._error(error_message, status_code)
            return self._success(self._get_task_positions(task["id"]))

        @self.app.route("/api/tasks/<int:task_id>/positions", methods=["GET"])
        def get_task_positions(task_id):
            task = G.orm.get_task_detail({"id": task_id})
            if not task or task.get("delete_time"):
                return self._error("task not found", 404)
            return self._success(self._get_task_positions(task_id))

        @self.app.route("/api/tasks/<int:task_id>/positions", methods=["POST"])
        def add_position(task_id):
            task = G.orm.get_task_detail({"id": task_id})
            if not task or task.get("delete_time"):
                return self._error("task not found", 404)

            raw_data = request.get_json(silent=True) or {}
            payload, error_message = self._normalize_payload(
                raw_data, self.POSITION_MUTABLE_FIELDS
            )
            if error_message:
                return self._error(error_message)
            if not payload:
                return self._error("request body is required")

            payload["task_id"] = task_id
            if self._ensure_api_handler():
                ok = self.api_handler.add_position(payload)
            else:
                ok = G.orm.add_position(payload)
            if not ok:
                return self._error("add position failed", 500)
            return self._success(True, message="position created")

        @self.app.route("/api/tasks/<int:task_id>/positions/batch", methods=["POST"])
        def batch_add_positions(task_id):
            task = G.orm.get_task_detail({"id": task_id})
            if not task or task.get("delete_time"):
                return self._error("task not found", 404)

            raw_data = request.get_json(silent=True) or []
            if not isinstance(raw_data, list) or len(raw_data) == 0:
                return self._error("request body must be a non-empty array")

            payload_list = []
            for index, item in enumerate(raw_data):
                if not isinstance(item, dict):
                    return self._error(f"body[{index}] must be an object")
                payload, error_message = self._normalize_payload(
                    item, self.POSITION_MUTABLE_FIELDS
                )
                if error_message:
                    return self._error(f"body[{index}] {error_message}")
                payload["task_id"] = task_id
                payload_list.append(payload)

            if self._ensure_api_handler():
                ok = self.api_handler.batch_add_positions(payload_list)
            else:
                ok = G.orm.batch_add_positions(payload_list)
            if not ok:
                return self._error("batch add positions failed", 500)
            return self._success(True, message="positions created")

        @self.app.route("/api/tasks/<int:task_id>/positions/exists", methods=["GET"])
        def check_position_exists(task_id):
            security_code = request.args.get("security_code")
            if not security_code:
                return self._error("security_code is required")

            if self._ensure_api_handler():
                exists = self.api_handler.check_position_exists(security_code, task_id)
            else:
                exists = G.orm.check_position_exists(security_code, task_id)
            return self._success({"exists": exists})

        @self.app.route("/api/positions/<int:position_id>", methods=["PUT"])
        def update_position(position_id):
            raw_data = request.get_json(silent=True) or {}
            payload, error_message = self._normalize_payload(
                raw_data, self.POSITION_MUTABLE_FIELDS
            )
            if error_message:
                return self._error(error_message)
            if not payload:
                return self._error("no valid position fields were provided")

            if self._ensure_api_handler():
                ok = self.api_handler.update_position(position_id, payload)
            else:
                ok = G.orm.update_position(position_id, payload)
            if not ok:
                return self._error("update position failed", 500)
            return self._success(True, message="position updated")

        @self.app.route("/api/positions/<int:position_id>", methods=["DELETE"])
        def delete_position(position_id):
            if self._ensure_api_handler():
                ok = self.api_handler.delete_position_by_id(position_id)
            else:
                ok = G.orm.delete_position_by_id(position_id)
            if not ok:
                return self._error("delete position failed", 500)
            return self._success(True, message="position deleted")

        @self.app.route("/api/account_fund", methods=["GET"])
        def account_fund():
            account_id = request.args.get("account_id")
            task_id = request.args.get("task_id")
            strategy_code = request.args.get("strategy_code")

            if account_id in (None, "") and task_id in (None, "") and strategy_code in (
                None,
                "",
            ):
                if self._ensure_api_handler():
                    return self._success(self.api_handler.get_account_info())
                return self._success(
                    {
                        "cash": 0,
                        "frozen_cash": 0,
                        "market_value": 0,
                        "total_asset": 0,
                    }
                )

            account, error_message, status_code = self._get_account_by_identifier(
                account_id=account_id, task_id=task_id, strategy_code=strategy_code
            )
            if error_message:
                return self._error(error_message, status_code)

            if self._ensure_api_handler():
                return self._success(self.api_handler.get_account_info(account["id"]))
            return self._success(self.trade_controller.get_account_info(account))

        @self.app.route("/api/accounts", methods=["GET"])
        def get_accounts():
            with_fund = str(request.args.get("with_fund", "0")).lower() in (
                "1",
                "true",
                "yes",
            )
            accounts = G.orm.get_account_list()
            if not with_fund:
                return self._success(accounts)

            account_items = []
            for account in accounts:
                account_item = dict(account)
                if self._ensure_api_handler():
                    account_item["fund"] = self.api_handler.get_account_info(account["id"])
                else:
                    account_item["fund"] = self.trade_controller.get_account_info(account)
                account_items.append(account_item)
            return self._success(account_items)

        @self.app.route("/api/accounts/<int:account_id>/fund", methods=["GET"])
        def get_account_fund(account_id):
            account = G.orm.get_account_by_id(account_id)
            if not account:
                return self._error("account not found", 404)

            if self._ensure_api_handler():
                data = self.api_handler.get_account_info(account_id)
            else:
                data = self.trade_controller.get_account_info(account)
            return self._success(data)

        @self.app.route("/api/accounts/<int:account_id>/positions", methods=["GET"])
        def get_account_positions(account_id):
            account = G.orm.get_account_by_id(account_id)
            if not account:
                return self._error("account not found", 404)

            if not self._ensure_api_handler():
                return self._error("account positions are not available", 500)

            try:
                data = self.api_handler.get_account_postion(account_id)
            except Exception as e:
                return self._error(f"get account positions failed: {str(e)}", 500)
            return self._success(data)

        @self.app.route("/api/order", methods=["POST"])
        @self.app.route("/api/orders", methods=["POST"])
        def order():
            data = request.get_json(silent=True) or {}
            task_id = data.get("task_id")
            strategy_code = data.get("strategy_code")
            stock_code = data.get("stock_code") or data.get("security_code") or data.get("code")
            volume = data.get("volume") if data.get("volume") not in (None, "") else data.get("amount")
            price = data.get("price")
            order_type = data.get("order_type", 1)
            side = data.get("side")
            is_buy = data.get("is_buy", 1)

            if task_id in (None, "") and not strategy_code:
                return self._error("task_id or strategy_code is required")
            if not stock_code:
                return self._error("stock_code is required")
            if volume in (None, ""):
                return self._error("volume is required")
            if price in (None, ""):
                return self._error("price is required")
            if order_type in (None, ""):
                return self._error("order_type is required")
            if side in (None, "") and is_buy is None:
                return self._error("is_buy is required")

            ok, result = self.trade_controller.manage_api_trader(data)
            if not ok:
                return self._error(result, 400)
            return self._success(result, message="order accepted")

        @self.app.route("/api/task/position_ratio", methods=["POST", "PUT"])
        def update_task_position_ratio():
            data = request.get_json(silent=True) or {}
            task_id = data.get("task_id")
            strategy_code = data.get("strategy_code")
            task, error_message, status_code = self._get_task_by_identifier(
                task_id, strategy_code
            )
            if error_message:
                return self._error(error_message, status_code)

            position_ratio = data.get("position_ratio")
            if position_ratio in (None, ""):
                return self._error("position_ratio is required")

            updated_task, error_message, status_code = self._update_task_fields(
                task["id"], {"position_ratio": position_ratio}
            )
            if error_message:
                return self._error(error_message, status_code)

            return self._success(
                {
                    "task_id": updated_task["id"],
                    "strategy_code": updated_task.get("strategy_code"),
                    "position_ratio": updated_task.get("position_ratio"),
                },
                message="task position_ratio updated",
            )

        @self.app.route("/api/today_trades", methods=["GET"])
        def today_trades():
            task_id = request.args.get("task_id")
            strategy_code = request.args.get("strategy_code")
            task, error_message, status_code = self._get_task_by_identifier(
                task_id=task_id, strategy_code=strategy_code
            )
            if error_message:
                return self._error(error_message, status_code)

            if self._ensure_api_handler():
                data = self.api_handler.query_trade_today(task["id"])
            else:
                data = G.orm.query_trade_today(task["id"])
            return self._success(data)

        @self.app.route("/api/tasks/<int:task_id>/today_trades", methods=["GET"])
        def get_task_today_trades(task_id):
            task = G.orm.get_task_detail({"id": task_id})
            if not task or task.get("delete_time"):
                return self._error("task not found", 404)

            if self._ensure_api_handler():
                data = self.api_handler.query_trade_today(task_id)
            else:
                data = G.orm.query_trade_today(task_id)
            return self._success(data)

        @self.app.route("/api/tasks/<int:task_id>/clear_all_stock", methods=["POST"])
        def clear_all_stock(task_id):
            task = G.orm.get_task_detail({"id": task_id})
            if not task or task.get("delete_time"):
                return self._error("task not found", 404)
            if not self._ensure_api_handler():
                return self._error("clear all stock is not available", 500)

            ok = self.api_handler.clear_all_stock_by_task_id(task_id)
            if not ok:
                return self._error("clear all stock failed", 500)
            return self._success(True, message="clear all stock success")

        @self.app.route("/api/total_account_information", methods=["GET"])
        def total_account_information():
            return self._success(self._build_account_overview())

    def start(self, host="localhost", port=5000):
        if self._is_running:
            print("Server is already running")
            return

        try:
            port = int(port)
        except (TypeError, ValueError):
            print(f"Invalid port: {port}")
            return

        from werkzeug.serving import make_server

        self.server = make_server(host, port, self.app, threaded=True)
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True
        self.thread.start()
        self._is_running = True
        print(f"Server started on {host}:{port}")

    def stop(self):
        if not self._is_running:
            print("Server is not running")
            return

        try:
            if self.server:
                self.server.shutdown()
                self.server.server_close()

            if self.thread:
                self.thread.join(timeout=2.0)

        except Exception as e:
            print(f"Error stopping server: {e}")
        finally:
            self._is_running = False
            self.server = None
            self.thread = None
            print("Server stopped")

    def is_running(self):
        return self._is_running and self.thread.is_alive()
