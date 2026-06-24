# AlphaQuantBridge

本项目是一个基于 `pywebview` 的本地下单桥客户端，用现有桌面 UI 配置 QMT / 同花顺账号，并暴露本机 HTTP API 给外部系统触发股票下单。

## 功能

- 本地配置 QMT / MiniQMT 账号与同花顺下单账号
- 多账号、多 API 任务管理
- 启停任务，使用任务编号 `strategy_code` 控制外部 API 下单权限
- 本地 HTTP API 下单: `POST /api/order` 或 `POST /api/orders`
- 查询账户资金、账户持仓、任务本地持仓、今日成交
- 任务级一键清仓
- QMT 账号连接、订阅、资金查询与窗口显示/隐藏
- 同花顺下单终端打开、显示/隐藏
- 本地日志查看与基础股票数据同步

## 已移除

- 用户登录 / 注册 / 云端分享策略
- 远程 WebSocket 策略信号接收
- 第三方策略代码转换与回测相关 UI
- 依赖远程服务的新股 / 新债申购入口

## API 下单示例

先在客户端中添加账号、创建 API 任务，并开启任务。然后调用：

```bash
curl -X POST http://127.0.0.1:8080/api/order \
  -H 'Content-Type: application/json' \
  -d '{
    "strategy_code": "API001",
    "stock_code": "600031",
    "volume": 100,
    "price": 18.23,
    "is_buy": 1,
    "order_type": 1
  }'
```

字段说明：

- `strategy_code`: 客户端任务编号，也可以改传 `task_id`
- `stock_code`: 股票代码，支持 `600031` / `600031.SH` / `600031.XSHG`
- `volume`: 下单数量，兼容字段名 `amount`
- `price`: 参考价格或限价价格
- `is_buy`: `1` 买入，`0` 卖出；也支持 `side: "buy"` / `"sell"`
- `order_type`: `1` 市价，`2` 限价；也兼容 QMT 风格字符串

## 开发

```bash
mv .example.env .env
pnpm run init
pnpm run alembic
pnpm run start
```

技术栈：

- Python 3.9+
- pywebview
- Vue 3
- Element Plus
- SQLite / SQLAlchemy
