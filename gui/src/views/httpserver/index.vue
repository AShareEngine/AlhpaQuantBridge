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
      <el-tag disable-transitions v-if="apiRunning" type="success" style="margin-right: 10px">服务正在运行</el-tag>
      <el-tag disable-transitions v-else type="danger" style="margin-right: 10px">服务未运行</el-tag>
      <el-button v-if="!apiRunning" type="primary" @click="openHttpServerAction(true)">开启</el-button>
      <el-button v-else type="danger" @click="openHttpServerAction(false)">关闭</el-button>
    </div>
    <div class="api-container-bottom">
      <div class="api-header">
        <h5 style="margin: 0">本地 API 说明</h5>
        <span class="api-copy-note">点击 URL 或 Body 可以直接复制</span>
      </div>
      <el-alert title="下单前需要先在 API任务 页面添加账号、创建任务并开启任务。数据接口使用本机 QMT / xtdata 获取行情和基础资料。" type="info" :closable="false" show-icon />
      <el-collapse expand-icon-position="left" style="margin-top: 10px">
        <el-collapse-item v-for="doc in apiDocs" :key="doc.name" :title="doc.title" :name="doc.name">
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
    </div>
  </div>
</template>

<script setup>
import { isHttpServerRunning, openHttpServer } from '@/api/comm_tube'
import { useCommonStore } from '@/store/common'
import { ElMessage } from 'element-plus'
import { computed, onMounted, reactive } from 'vue'

const commonStore = useCommonStore()
const setting = reactive({
  host: '127.0.0.1',
  port: '8080'
})
const apiRunning = computed(() => commonStore.apiServerRunning)

const baseUrl = computed(() => `http://${setting.host}:${setting.port}`)

const apiDocs = computed(() => [
  {
    name: 'order',
    title: '触发下单',
    method: 'POST',
    url: `${baseUrl.value}/api/order`,
    body: `{
  "strategy_code": "API001",
  "stock_code": "600031",
  "volume": 100,
  "price": 18.23,
  "is_buy": 1,
  "order_type": 1
}`,
    description: [
      'strategy_code 对应桌面端任务编号，也可传 task_id',
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
    "strategy_code": "API001"
  }
}`
  },
  {
    name: 'tasks',
    title: '获取任务列表',
    method: 'GET',
    url: `${baseUrl.value}/api/tasks`,
    description: ['支持 query 参数: id / account_id / strategy_code / platform / is_open / order_count_type'],
    response: `{
  "code": 200,
  "data": [
    {
      "id": 1,
      "name": "API任务",
      "strategy_code": "API001",
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
  "strategy_code": "API001",
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
    description: ['支持 account_id / task_id / strategy_code 三种定位方式；都不传则返回所有账户汇总资金'],
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
    description: ['兼容旧接口: GET /api/today_trades?task_id=1 或 ?strategy_code=API001'],
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
  },
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
    response: `{
  "code": 200,
  "success": true,
  "message": "获取 K 线历史成功",
  "data": {
    "items": [
      {
        "symbol": "600000.SH",
        "bars": []
      }
    ]
  }
}`
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
    response: `{
  "code": 200,
  "success": true,
  "message": "获取全量 Tick 快照成功",
  "data": {
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
  }
}`
  },
  {
    name: 'data-instrument',
    title: '获取合约信息',
    method: 'GET',
    url: `${baseUrl.value}/api/v1/data/instrument/600000.SH?complete=false`,
    description: ['返回 xtdata.get_instrument_detail 的基础信息，字段随 QMT 版本可能不同'],
    response: `{
  "code": 200,
  "success": true,
  "message": "获取合约信息成功",
  "data": {
    "symbol": "600000.SH",
    "fields": {
      "InstrumentID": "600000",
      "InstrumentName": "浦发银行"
    }
  }
}`
  },
  {
    name: 'data-sectors',
    title: '获取板块成分',
    method: 'GET',
    url: `${baseUrl.value}/api/v1/data/sectors?sector_name=沪深A股`,
    description: ['建议传 sector_name，避免遍历所有板块导致请求时间过长'],
    response: `{
  "code": 200,
  "success": true,
  "message": "获取板块列表成功",
  "data": {
    "items": [
      {
        "sector_name": "沪深A股",
        "symbols": ["600000.SH", "000001.SZ"]
      }
    ]
  }
}`
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
    response: `{
  "code": 200,
  "success": true,
  "message": "下载历史行情数据成功",
  "data": {
    "function": "download_history_data",
    "success": true
  }
}`
  }
])

onMounted(() => {
  checkHttpServer()
})

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

const openHttpServerAction = async (open) => {
  try {
    const result = await openHttpServer(open, setting.host, setting.port)
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
}

.api-copy-note {
  color: #8a5a00;
  font-size: 12px;
}

.api-introduction {
  display: flex;
  flex-direction: column;
  padding: 10px;
  user-select: text;
  background: #f5f5f5;
  border-radius: 8px;

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
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    border-color: #409eff;
    box-shadow: 0 4px 14px rgba(64, 158, 255, 0.12);
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
  color: #909399;
  font-size: 12px;
}

.description-block,
.response-block {
  margin: 0;
  padding: 12px;
  background: #ffffff;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
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
  color: #409eff;
}

.method-post {
  color: #67c23a;
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
