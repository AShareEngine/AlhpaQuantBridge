<template>
  <div class="api-container">
    <div class="api-container-top">
      <div class="setting-item">
        <div class="setting-item-title">HOST设置</div>
        <el-input style="width: 140px" :disabled="apiRunning" class="setting-item-input" v-model="setting.host" />
      </div>
      <div class="setting-item">
        <div class="setting-item-title">端口设置</div>
        <el-input style="width: 80px" :disabled="apiRunning" class="setting-item-input" v-model="setting.port" />
      </div>
      <div class="setting-item token-setting">
        <div class="setting-item-title">Token</div>
        <el-input class="token-input" :disabled="apiRunning" readonly v-model="setting.token" />
        <el-button :disabled="apiRunning" @click="refreshApiTokenAction">刷新</el-button>
        <el-button :disabled="!setting.token" @click="copyText(authHeader, 'Token Header')">复制Header</el-button>
      </div>
      <el-tag disable-transitions v-if="apiRunning" type="success" style="margin-right: 10px">服务正在运行</el-tag>
      <el-tag disable-transitions v-else type="danger" style="margin-right: 10px">服务未运行</el-tag>
      <el-button v-if="!apiRunning" type="primary" @click="openHttpServerAction(true)">开启</el-button>
      <el-button v-else type="danger" @click="openHttpServerAction(false)">关闭</el-button>
    </div>
    <div class="api-container-bottom">
      <div class="api-header">
        <h5 style="margin: 0">本地 API 说明</h5>
      </div>
      <div class="api-doc-switch">
        <el-radio-group v-model="activeApiDocGroup" size="small">
          <el-radio-button v-for="group in apiDocGroups" :key="group.name" :label="group.name">
            {{ group.title }}
          </el-radio-button>
        </el-radio-group>
        <span class="api-doc-count">{{ activeApiDocGroupInfo.docs.length }} 个接口</span>
      </div>
      <section class="api-doc-group">
        <div class="api-doc-group-header">
          <div>
            <h6>{{ activeApiDocGroupInfo.title }}</h6>
            <p>{{ activeApiDocGroupInfo.description }}</p>
          </div>
          <el-tag effect="plain">{{ activeApiDocGroupInfo.docs.length }} 个接口</el-tag>
        </div>
        <el-collapse :key="activeApiDocGroupInfo.name" expand-icon-position="left">
          <el-collapse-item v-for="doc in activeApiDocGroupInfo.docs" :key="doc.name" :title="doc.title" :name="doc.name">
            <div class="api-introduction">
              <h4>请求：</h4>
              <div class="copy-block" @click="copyText(doc.url, 'URL')">
                <code>
                  <span :class="['method-tag', `method-${doc.method.toLowerCase()}`]">{{ doc.method }}</span>
                  <span class="url-text">{{ doc.url }}</span>
                </code>
                <span class="copy-tip">点击复制 URL</span>
              </div>

              <template v-if="doc.body">
                <h4>Body：</h4>
                <div class="copy-block" @click="copyText(doc.body, 'Body')">
                  <pre>{{ doc.body }}</pre>
                  <span class="copy-tip">点击复制 Body</span>
                </div>
              </template>

              <template v-if="doc.description?.length">
                <h4>说明：</h4>
                <code class="description-block">
                  <template v-for="(line, index) in doc.description" :key="index">
                    {{ line }}<br v-if="index < doc.description.length - 1" />
                  </template>
                </code>
              </template>

              <template v-if="doc.response">
                <h4>返回：</h4>
                <pre class="response-block">{{ doc.response }}</pre>
              </template>
            </div>
          </el-collapse-item>
        </el-collapse>
      </section>
    </div>
  </div>
</template>

<script setup>
import { getApiToken, isHttpServerRunning, openHttpServer, refreshApiToken } from '@/api/comm_tube'
import { useCommonStore } from '@/store/common'
import { ElMessage } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'

const commonStore = useCommonStore()
const setting = reactive({
  host: '127.0.0.1',
  port: '8080',
  token: ''
})
const apiRunning = computed(() => commonStore.apiServerRunning)

const baseUrl = computed(() => `http://${setting.host}:${setting.port}`)
const authHeader = computed(() => `Authorization: Bearer ${setting.token}`)
const activeApiDocGroup = ref('original')

const dataSuccessResponse = (message, data = `{
    "items": []
  }`) => `{
  "code": 200,
  "success": true,
  "message": "${message}",
  "data": ${data}
}`

const originalApiDocs = computed(() => [
  {
    name: 'order',
    title: '触发下单',
    method: 'POST',
    url: `${baseUrl.value}/api/order`,
    body: `{
  "task_id": 1,
  "stock_code": "600031",
  "volume": 100,
  "price": 18.23,
  "is_buy": 1,
  "order_type": 1
}`,
    description: [
      'task_id 对应桌面端任务 ID；新接入请使用该字段',
      'is_buy: 1 买入, 0 卖出；side: "buy"/"sell" 也支持',
      'order_type: 1 市价, 2 限价；也兼容 MarketOrderStyle / LimitOrderStyle(18.23)',
      '任务必须为 API 调用任务且已开启，QMT 账号必须已连接'
    ],
    response: `{
  "code": 200,
  "message": "order accepted",
  "data": {
    "order_id": 12,
    "task_id": 1,
    "task_id": 1
  }
}`
  },
  {
    name: 'tasks',
    title: '获取任务列表',
    method: 'GET',
    url: `${baseUrl.value}/api/tasks`,
    description: ['支持 query 参数: id / account_id / platform / is_open / order_count_type'],
    response: `{
  "code": 200,
  "data": [
    {
      "id": 1,
      "name": "API任务",
      "platform": 10
    }
  ]
}`
  },
  {
    name: 'create-task',
    title: '创建 API 任务',
    method: 'POST',
    url: `${baseUrl.value}/api/tasks`,
    body: `{
  "name": "API任务",
  "account_id": 1,
  "allocation_amount": 100000,
  "service_charge": 0.00025,
  "lower_limit_of_fees": 5,
  "open_mandatory_limit_order": 1
}`,
    description: ['未传 platform/task_type/order_count_type 时会自动按 API 下单任务补齐默认值'],
    response: `{
  "code": 200,
  "message": "task created",
  "data": true
}`
  },
  {
    name: 'run-task',
    title: '启停任务',
    method: 'POST',
    url: `${baseUrl.value}/api/tasks/1/run`,
    body: `{
  "is_open": 1
}`,
    description: ['is_open: 1 开启, 0 关闭；关闭后 /api/order 会拒绝该任务下单'],
    response: `{
  "code": 200,
  "message": "task running state updated",
  "data": true
}`
  },
  {
    name: 'account-fund',
    title: '获取账户资金',
    method: 'GET',
    url: `${baseUrl.value}/api/account_fund?account_id=1`,
    description: ['支持 account_id / task_id；都不传则返回所有账户汇总资金'],
    response: `{
  "code": 200,
  "data": {
    "cash": 100000,
    "frozen_cash": 0,
    "market_value": 50000,
    "total_asset": 150000
  }
}`
  },
  {
    name: 'account-positions',
    title: '获取账户持仓',
    method: 'GET',
    url: `${baseUrl.value}/api/accounts/1/positions`,
    description: ['直接读取交易端账户持仓，需要账号已连接'],
    response: `{
  "code": 200,
  "data": [
    {
      "stock_code": "600031.SH",
      "volume": 100
    }
  ]
}`
  },
  {
    name: 'task-positions',
    title: '获取任务本地持仓',
    method: 'GET',
    url: `${baseUrl.value}/api/tasks/1/positions`,
    description: ['返回本地数据库记录的任务持仓，用于任务级清仓和成交后的持仓维护'],
    response: `{
  "code": 200,
  "data": [
    {
      "id": 1,
      "security_code": "600031.SH",
      "volume": 100
    }
  ]
}`
  },
  {
    name: 'add-position',
    title: '新增任务持仓',
    method: 'POST',
    url: `${baseUrl.value}/api/tasks/1/positions`,
    body: `{
  "security_code": "600031",
  "volume": 100,
  "average_price": 18.23,
  "is_mock": 0
}`,
    description: ['security_code 支持不带后缀，接口会转换为 QMT 使用的 .SH/.SZ 格式'],
    response: `{
  "code": 200,
  "message": "position created",
  "data": true
}`
  },
  {
    name: 'today-trades',
    title: '获取今日成交',
    method: 'GET',
    url: `${baseUrl.value}/api/tasks/1/today_trades`,
    description: ['兼容旧接口: GET /api/today_trades?task_id=1'],
    response: `{
  "code": 200,
  "data": []
}`
  },
  {
    name: 'clear-all',
    title: '按任务持仓一键清仓',
    method: 'POST',
    url: `${baseUrl.value}/api/tasks/1/clear_all_stock`,
    description: ['按任务当前本地持仓逐个发起卖单，需要账号已连接'],
    response: `{
  "code": 200,
  "message": "clear all stock success",
  "data": true
}`
  }
])

const marketDataApiDocs = computed(() => [
  {
    name: 'data-kline',
    title: '获取 K 线历史',
    method: 'POST',
    url: `${baseUrl.value}/api/v1/data/kline-history`,
    body: `{
  "symbols": ["600000.SH"],
  "period": "1d",
  "start_time": "20240101",
  "end_time": "20240131",
  "fields": [],
  "adjust_type": "none",
  "fill_data": true
}`,
    description: [
      '兼容 quant-qmt-proxy 的 REST 路径',
      'symbols 也支持逗号分隔字符串；stock_code/code 会自动转成单个 symbols'
  ],
    response: dataSuccessResponse('获取 K 线历史成功', `{
    "items": [
      {
        "symbol": "600000.SH",
        "bars": []
      }
    ]
  }`)
  },
  {
    name: 'data-tick-history',
    title: '获取 Tick 历史',
    method: 'POST',
    url: `${baseUrl.value}/api/v1/data/tick-history`,
    body: `{
  "symbols": ["600000.SH"],
  "start_time": "20240101093000",
  "end_time": "20240101150000",
  "fields": [],
  "adjust_type": "none"
}`,
    description: ['读取历史 Tick 数据；需要本机 QMT 数据服务可用'],
    response: dataSuccessResponse('获取 Tick 历史成功')
  },
  {
    name: 'data-full-tick',
    title: '获取全量 Tick 快照',
    method: 'POST',
    url: `${baseUrl.value}/api/v1/data/full-tick`,
    body: `{
  "symbols": ["600000.SH", "000001.SZ"]
}`,
    description: ['读取 QMT 当前 full tick 快照；需要本机 QMT 数据服务可用'],
    response: dataSuccessResponse('获取全量 Tick 快照成功', `{
    "items": [
      {
        "symbol": "600000.SH",
        "tick": {
          "last_price": 8.2,
          "ask_price": [8.21],
          "bid_price": [8.19]
        }
      }
    ]
  }`)
  },
  {
    name: 'data-market-data-ex',
    title: '获取扩展行情数据',
    method: 'POST',
    url: `${baseUrl.value}/api/v1/data/market-data-ex`,
    body: `{
  "symbols": ["600000.SH"],
  "period": "1d",
  "start_time": "20240101",
  "end_time": "20240131",
  "count": -1,
  "fields": [],
  "adjust_type": "none",
  "fill_data": true
}`,
    description: ['对应 xtdata.get_market_data_ex，用于获取扩展行情数据'],
    response: dataSuccessResponse('获取扩展行情数据成功')
  },
  {
    name: 'data-local-data',
    title: '获取本地行情数据',
    method: 'POST',
    url: `${baseUrl.value}/api/v1/data/local-data`,
    body: `{
  "symbols": ["600000.SH"],
  "period": "1d",
  "start_time": "20240101",
  "end_time": "20240131",
  "count": -1,
  "fields": [],
  "adjust_type": "none",
  "fill_data": true
}`,
    description: ['对应 xtdata.get_local_data，从本地已下载数据读取行情'],
    response: dataSuccessResponse('获取本地行情数据成功')
  },
  {
    name: 'data-full-kline',
    title: '获取最新交易日 K 线',
    method: 'POST',
    url: `${baseUrl.value}/api/v1/data/full-kline`,
    body: `{
  "symbols": ["600000.SH"],
  "period": "1d",
  "start_time": "",
  "end_time": "",
  "count": 1,
  "fields": [],
  "adjust_type": "none",
  "fill_data": true
}`,
    description: ['未传 count 时默认取 1 条，用于获取最新交易日 K 线'],
    response: dataSuccessResponse('获取最新交易日 K 线成功')
  },
  {
    name: 'data-financial',
    title: '获取财务数据',
    method: 'POST',
    url: `${baseUrl.value}/api/v1/data/financial`,
    body: `{
  "symbols": ["600000.SH"],
  "table_names": ["Balance", "Income", "CashFlow"],
  "start_time": "20240101",
  "end_time": "20241231"
}`,
    description: ['table_names 为必填，也兼容 table_list 字段'],
    response: dataSuccessResponse('获取财务数据成功')
  },
  {
    name: 'data-instrument',
    title: '获取合约信息',
    method: 'GET',
    url: `${baseUrl.value}/api/v1/data/instrument/600000.SH?complete=false`,
    description: ['返回 xtdata.get_instrument_detail 的基础信息，字段随 QMT 版本可能不同'],
    response: dataSuccessResponse('获取合约信息成功', `{
    "symbol": "600000.SH",
    "fields": {
      "InstrumentID": "600000",
      "InstrumentName": "浦发银行"
    }
  }`)
  },
  {
    name: 'data-instrument-type',
    title: '获取合约类型',
    method: 'GET',
    url: `${baseUrl.value}/api/v1/data/instrument-type/600000.SH`,
    description: ['返回 xtdata.get_instrument_type 的结果'],
    response: dataSuccessResponse('获取合约类型成功', `{
    "symbol": "600000.SH",
    "instrument_type": "STOCK"
  }`)
  },
  {
    name: 'data-trade-times',
    title: '获取交易时间段',
    method: 'GET',
    url: `${baseUrl.value}/api/v1/data/trade-times/600000.SH`,
    description: ['返回指定合约的交易时间段'],
    response: dataSuccessResponse('获取交易时间段成功')
  },
  {
    name: 'data-main-contract',
    title: '获取主力合约',
    method: 'GET',
    url: `${baseUrl.value}/api/v1/data/main-contract/IF?start_time=20240101&end_time=20241231`,
    description: ['code_market 为品种市场代码，start_time/end_time 为可选 query 参数'],
    response: dataSuccessResponse('获取主力合约成功')
  },
  {
    name: 'data-trading-calendar',
    title: '获取交易日历',
    method: 'POST',
    url: `${baseUrl.value}/api/v1/data/trading-calendar`,
    body: `{
  "market": "SH",
  "start_time": "20240101",
  "end_time": "20241231"
}`,
    description: ['market 为必填，例如 SH / SZ'],
    response: dataSuccessResponse('获取交易日历成功')
  },
  {
    name: 'data-trading-dates',
    title: '获取交易日列表',
    method: 'POST',
    url: `${baseUrl.value}/api/v1/data/trading-dates`,
    body: `{
  "market": "SH",
  "start_time": "20240101",
  "end_time": "20241231",
  "count": -1
}`,
    description: ['market 为必填；count 默认 -1'],
    response: dataSuccessResponse('获取交易日列表成功')
  },
  {
    name: 'data-holidays',
    title: '获取节假日列表',
    method: 'GET',
    url: `${baseUrl.value}/api/v1/data/holidays`,
    description: ['返回本地 QMT 节假日列表'],
    response: dataSuccessResponse('获取节假日列表成功')
  },
  {
    name: 'data-index-weight',
    title: '获取指数权重',
    method: 'POST',
    url: `${baseUrl.value}/api/v1/data/index-weight`,
    body: `{
  "index_code": "000300.SH"
}`,
    description: ['index_code 为必填'],
    response: dataSuccessResponse('获取指数权重成功')
  },
  {
    name: 'data-periods',
    title: '获取可用周期列表',
    method: 'GET',
    url: `${baseUrl.value}/api/v1/data/periods`,
    description: ['返回 QMT 支持的行情周期列表'],
    response: dataSuccessResponse('获取可用周期列表成功')
  },
  {
    name: 'data-dir',
    title: '获取数据目录',
    method: 'GET',
    url: `${baseUrl.value}/api/v1/data/data-dir`,
    description: ['返回 xtdata 当前数据目录'],
    response: dataSuccessResponse('获取数据目录成功', `{
    "path": "QMT data directory"
  }`)
  },
  {
    name: 'data-sectors',
    title: '获取板块成分',
    method: 'GET',
    url: `${baseUrl.value}/api/v1/data/sectors?sector_name=沪深A股`,
    description: ['建议传 sector_name，避免遍历所有板块导致请求时间过长'],
    response: dataSuccessResponse('获取板块列表成功', `{
    "items": [
      {
        "sector_name": "沪深A股",
        "symbols": ["600000.SH", "000001.SZ"]
      }
    ]
  }`)
  },
  {
    name: 'data-divid-factors',
    title: '获取除权除息数据',
    method: 'POST',
    url: `${baseUrl.value}/api/v1/data/divid-factors`,
    body: `{
  "stock_code": "600000.SH",
  "start_time": "20240101",
  "end_time": "20241231"
}`,
    description: ['stock_code 为必填，也兼容 symbol 字段'],
    response: dataSuccessResponse('获取除权除息数据成功')
  },
  {
    name: 'data-cb-info',
    title: '获取可转债信息',
    method: 'GET',
    url: `${baseUrl.value}/api/v1/data/cb-info/110000.SH`,
    description: ['返回指定可转债信息'],
    response: dataSuccessResponse('获取可转债信息成功')
  },
  {
    name: 'data-ipo-info',
    title: '获取新股申购信息',
    method: 'GET',
    url: `${baseUrl.value}/api/v1/data/ipo-info?start_time=20240101&end_time=20241231`,
    description: ['start_time/end_time 为可选 query 参数'],
    response: dataSuccessResponse('获取新股申购信息成功')
  },
  {
    name: 'data-etf-info-all',
    title: '获取全部 ETF 信息',
    method: 'GET',
    url: `${baseUrl.value}/api/v1/data/etf-info`,
    description: ['不带 symbol 时返回全部 ETF 信息'],
    response: dataSuccessResponse('获取 ETF 信息成功')
  },
  {
    name: 'data-etf-info',
    title: '获取单只 ETF 信息',
    method: 'GET',
    url: `${baseUrl.value}/api/v1/data/etf-info/510300.SH`,
    description: ['返回指定 ETF 信息'],
    response: dataSuccessResponse('获取 ETF 信息成功')
  },
  {
    name: 'data-l2-quote',
    title: '获取 L2 快照',
    method: 'POST',
    url: `${baseUrl.value}/api/v1/data/l2/quote`,
    body: `{
  "symbols": ["600000.SH"],
  "start_time": "20240101093000",
  "end_time": "20240101150000",
  "count": -1,
  "fields": []
}`,
    description: ['需要 QMT L2 数据权限'],
    response: dataSuccessResponse('获取 L2 快照成功')
  },
  {
    name: 'data-l2-order',
    title: '获取 L2 逐笔委托',
    method: 'POST',
    url: `${baseUrl.value}/api/v1/data/l2/order`,
    body: `{
  "symbols": ["600000.SH"],
  "start_time": "20240101093000",
  "end_time": "20240101150000",
  "count": -1,
  "fields": []
}`,
    description: ['需要 QMT L2 数据权限'],
    response: dataSuccessResponse('获取 L2 逐笔委托成功')
  },
  {
    name: 'data-l2-transaction',
    title: '获取 L2 逐笔成交',
    method: 'POST',
    url: `${baseUrl.value}/api/v1/data/l2/transaction`,
    body: `{
  "symbols": ["600000.SH"],
  "start_time": "20240101093000",
  "end_time": "20240101150000",
  "count": -1,
  "fields": []
}`,
    description: ['需要 QMT L2 数据权限'],
    response: dataSuccessResponse('获取 L2 逐笔成交成功')
  },
  {
    name: 'data-download-history',
    title: '下载历史行情',
    method: 'POST',
    url: `${baseUrl.value}/api/v1/data/download/history`,
    body: `{
  "stock_code": "600000.SH",
  "period": "1d",
  "start_time": "20240101",
  "end_time": "20240131",
  "incrementally": false
}`,
    description: ['显式调用 xtdata.download_history_data，用于补齐本地数据后再查询'],
    response: dataSuccessResponse('下载历史行情数据成功', `{
    "function": "download_history_data",
    "success": true
  }`)
  },
  {
    name: 'data-download-history-batch',
    title: '批量下载历史行情',
    method: 'POST',
    url: `${baseUrl.value}/api/v1/data/download/history/batch`,
    body: `{
  "symbols": ["600000.SH", "000001.SZ"],
  "period": "1d",
  "start_time": "20240101",
  "end_time": "20240131",
  "incrementally": false
}`,
    description: ['批量调用 xtdata.download_history_data2'],
    response: dataSuccessResponse('批量下载历史行情数据成功')
  },
  {
    name: 'data-download-financial',
    title: '下载财务数据',
    method: 'POST',
    url: `${baseUrl.value}/api/v1/data/download/financial`,
    body: `{
  "symbols": ["600000.SH"],
  "table_names": ["Balance", "Income", "CashFlow"],
  "start_time": "20240101",
  "end_time": "20241231"
}`,
    description: ['table_names 也兼容 table_list 字段'],
    response: dataSuccessResponse('下载财务数据成功')
  },
  {
    name: 'data-download-index-weight',
    title: '下载指数权重数据',
    method: 'POST',
    url: `${baseUrl.value}/api/v1/data/download/index-weight`,
    body: `{
  "index_code": "000300.SH"
}`,
    description: ['index_code 可选；不传时按 QMT 默认行为执行'],
    response: dataSuccessResponse('下载指数权重数据成功')
  },
  {
    name: 'data-download-history-contracts',
    title: '下载历史合约数据',
    method: 'POST',
    url: `${baseUrl.value}/api/v1/data/download/history-contracts`,
    body: `{
  "market": "SH"
}`,
    description: ['market 可选'],
    response: dataSuccessResponse('下载历史合约数据成功')
  },
  {
    name: 'data-download-sector',
    title: '下载板块数据',
    method: 'POST',
    url: `${baseUrl.value}/api/v1/data/download/sector`,
    body: `{
  "sector_name": "沪深A股"
}`,
    description: ['sector_name 可选；用于同步 QMT 板块数据'],
    response: dataSuccessResponse('下载板块数据成功')
  },
  {
    name: 'data-download-holiday',
    title: '下载节假日数据',
    method: 'POST',
    url: `${baseUrl.value}/api/v1/data/download/holiday`,
    body: `{}`,
    description: ['下载 QMT 节假日数据'],
    response: dataSuccessResponse('下载节假日数据成功')
  },
  {
    name: 'data-download-cb',
    title: '下载可转债数据',
    method: 'POST',
    url: `${baseUrl.value}/api/v1/data/download/cb`,
    body: `{}`,
    description: ['下载 QMT 可转债数据'],
    response: dataSuccessResponse('下载可转债数据成功')
  },
  {
    name: 'data-download-etf',
    title: '下载 ETF 数据',
    method: 'POST',
    url: `${baseUrl.value}/api/v1/data/download/etf`,
    body: `{}`,
    description: ['下载 QMT ETF 信息'],
    response: dataSuccessResponse('下载 ETF 数据成功')
  }
])

const apiDocGroups = computed(() => [
  {
    name: 'original',
    title: '原本任务 / 下单逻辑',
    description: '围绕 API 任务、账号资金、持仓、成交和下单的接口，需要任务和交易账号状态配合。',
    docs: originalApiDocs.value
  },
  {
    name: 'market-data',
    title: '纯行情数据接口',
    description: '只通过本机 QMT / xtdata 获取行情和基础资料，不依赖 API 任务。',
    docs: marketDataApiDocs.value
  }
])

const activeApiDocGroupInfo = computed(() => (
  apiDocGroups.value.find((group) => group.name === activeApiDocGroup.value) || apiDocGroups.value[0]
))

onMounted(async () => {
  await loadApiToken()
  checkHttpServer()
})

const loadApiToken = async () => {
  try {
    const token = await getApiToken()
    if (token) {
      setting.token = token
    }
  } catch (error) {
    ElMessage.error('Token加载失败')
  }
}

const checkHttpServer = async () => {
  try {
    const res = await isHttpServerRunning()
    commonStore.setApiServerRunning(res)
  } catch (error) {
    commonStore.setApiServerRunning(false)
  }
}

const fallbackCopy = (text) => {
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.setAttribute('readonly', 'readonly')
  textarea.style.position = 'fixed'
  textarea.style.top = '-9999px'
  document.body.appendChild(textarea)
  textarea.select()
  document.execCommand('copy')
  document.body.removeChild(textarea)
}

const copyText = async (text, label = '内容') => {
  try {
    if (navigator?.clipboard?.writeText) {
      await navigator.clipboard.writeText(text)
    } else {
      fallbackCopy(text)
    }
    ElMessage.success(`${label}已复制`)
  } catch (error) {
    try {
      fallbackCopy(text)
      ElMessage.success(`${label}已复制`)
    } catch (fallbackError) {
      ElMessage.error(`${label}复制失败`)
    }
  }
}

const refreshApiTokenAction = async () => {
  if (apiRunning.value) {
    ElMessage.warning('服务运行中不能刷新Token')
    return
  }
  try {
    const token = await refreshApiToken()
    if (!token) {
      throw new Error('empty token')
    }
    setting.token = token
    ElMessage.success('Token已刷新')
  } catch (error) {
    ElMessage.error('Token刷新失败')
  }
}

const openHttpServerAction = async (open) => {
  try {
    if (open && !setting.token) {
      await refreshApiTokenAction()
    }
    if (open && !setting.token) {
      ElMessage.error('Token不能为空')
      return
    }
    const result = await openHttpServer(open, setting.host, setting.port, setting.token)
    if (typeof result === 'boolean') {
      commonStore.setApiServerRunning(result)
    } else {
      await checkHttpServer()
    }
    if (commonStore.apiServerRunning === open) {
      ElMessage.success(open ? 'API服务已开启' : 'API服务已关闭')
    } else {
      ElMessage.error(open ? 'API服务开启失败' : 'API服务关闭失败')
    }
  } catch (error) {
    await checkHttpServer()
    ElMessage.error(open ? 'API服务开启失败' : 'API服务关闭失败')
  }
}
</script>

<style scoped lang="less">
.api-container {
  padding: 10px;
  display: flex;
  flex-direction: column;
  height: 100%;
  box-sizing: border-box;

  .api-container-top {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
    background: #fff;
    margin-bottom: 10px;
    padding: 8px;

    .setting-item {
      display: flex;
      align-items: center;
      margin-right: 10px;

      .setting-item-title {
        width: 80px;
        margin-right: 10px;
      }

      .setting-item-input {
        width: 100px;
      }
    }

    .token-setting {
      flex: 1;
      min-width: 460px;
      margin-right: 0;

      .token-input {
        width: min(460px, 100%);
        margin-right: 8px;
      }
    }
  }

  .api-container-bottom {
    padding: 10px;
    background: #fff;
    overflow-y: auto;
  }
}

.api-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;

  h5 {
    color: var(--app-text);
  }
}

.api-doc-switch {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 12px;
}

.api-doc-count {
  color: var(--app-text-muted);
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
}

.api-doc-group {
  margin-top: 14px;
  border: 1px solid var(--app-border);
  border-radius: 6px;
  background: #ffffff;
  overflow: hidden;
}

.api-doc-group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 14px;
  background: #f6f9fa;
  border-bottom: 1px solid var(--app-border);

  h6 {
    margin: 0 0 4px;
    color: var(--app-text);
    font-size: 16px;
    font-weight: 850;
  }

  p {
    margin: 0;
    color: var(--app-text-muted);
    font-size: 13px;
    line-height: 1.5;
  }
}

.api-introduction {
  display: flex;
  flex-direction: column;
  padding: 10px;
  user-select: text;
  background: #f5f5f5;
  border-radius: 6px;

  h4 {
    margin: 15px 0 8px;
    font-size: 16px;
    font-weight: 900;
  }
}

.copy-block {
  position: relative;
  padding: 12px;
  background: #ffffff;
  border: 1px solid var(--app-border);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    border-color: var(--app-primary-line);
    box-shadow: 0 4px 14px rgba(31, 111, 139, 0.12);
  }

  code,
  pre {
    margin: 0;
    white-space: pre-wrap;
    word-break: break-word;
    font-family: Menlo, Monaco, Consolas, 'Courier New', monospace;
  }
}

.copy-tip {
  display: inline-block;
  margin-top: 8px;
  color: var(--app-text-faint);
  font-size: 12px;
}

.description-block,
.response-block {
  margin: 0;
  padding: 12px;
  background: #ffffff;
  border-radius: 6px;
  border: 1px solid var(--app-border);
  white-space: pre-wrap;
  word-break: break-word;
  font-family: Menlo, Monaco, Consolas, 'Courier New', monospace;
}

.method-tag {
  display: inline-block;
  min-width: 50px;
  margin-right: 10px;
  font-weight: 700;
}

.method-get {
  color: #2f80ed;
}

.method-post {
  color: var(--app-success);
}

.method-put {
  color: #e6a23c;
}

.method-delete {
  color: #f56c6c;
}

.url-text {
  color: #1f7a8c;
}
</style>
