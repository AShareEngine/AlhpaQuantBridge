<template>
  <div class="setting-container">
    <section class="setting-panel">
      <div class="panel-header">
        <div>
          <h3>本地下单模式</h3>
          <p>本项目不再使用账号登录和远程策略服务，外部系统通过本机 HTTP API 触发下单。</p>
        </div>
        <el-tag type="success" effect="plain">本地 API</el-tag>
      </div>

      <el-descriptions :column="1" border size="small">
        <el-descriptions-item label="账号配置">在 API任务 页面添加 QMT 或同花顺账号</el-descriptions-item>
        <el-descriptions-item label="API 服务">在 API服务 页面设置 host/port 并启动</el-descriptions-item>
        <el-descriptions-item label="下单入口">POST /api/order 或 POST /api/orders</el-descriptions-item>
      </el-descriptions>

      <div class="actions">
        <el-button type="primary" @click="goApi">打开 API 服务</el-button>
        <el-button type="warning" :loading="isSyncingData" @click="resyncBaseDataAction">重新同步基础数据</el-button>
      </div>
      <div class="sync-tip">同步范围: 交易日、股票列表、ST 股票数据。限价保护和打新相关功能会使用这些基础数据。</div>
    </section>
  </div>
</template>

<script setup>
import { resyncBaseData } from '@/api/comm_tube'
import { ElMessage } from 'element-plus'
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const isSyncingData = ref(false)

const goApi = () => {
  router.push('/api')
}

const resyncBaseDataAction = async () => {
  if (isSyncingData.value) return
  isSyncingData.value = true
  try {
    const ok = await resyncBaseData()
    if (ok) {
      ElMessage.success('基础数据重新同步成功')
    } else {
      ElMessage.error('基础数据重新同步失败')
    }
  } catch (error) {
    ElMessage.error('基础数据重新同步失败')
  } finally {
    isSyncingData.value = false
  }
}
</script>

<style scoped lang="less">
.setting-container {
  display: flex;
  align-items: flex-start;
  justify-content: center;
  height: 100%;
  background-color: #f5f7fb;
  padding-top: 8vh;
  box-sizing: border-box;
}

.setting-panel {
  width: 64vw;
  max-width: 860px;
  min-width: 520px;
  background: #fff;
  border-radius: 8px;
  padding: 22px;
  border: 1px solid #e5e7eb;
}

.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;

  h3 {
    margin: 0 0 8px;
    font-size: 18px;
    color: #1f2937;
  }

  p {
    margin: 0;
    color: #667085;
    font-size: 13px;
    line-height: 1.6;
  }
}

.actions {
  display: flex;
  gap: 10px;
  margin-top: 18px;
}

.sync-tip {
  margin-top: 10px;
  color: #909399;
  font-size: 12px;
}
</style>
