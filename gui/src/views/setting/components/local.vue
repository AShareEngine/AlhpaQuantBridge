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
      </div>
    </section>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

const goApi = () => {
  router.push('/api')
}
</script>

<style scoped lang="less">
.setting-container {
  display: flex;
  align-items: center;
  flex-direction: column;
  justify-content: center;
  height: 100%;
  background-color: var(--app-bg);
}

.setting-panel {
  width: 60vw;
  max-width: 760px;
  min-width: 520px;
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  border: 1px solid var(--app-border);
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
    color: var(--app-text);
    font-weight: 700;
  }

  p {
    margin: 0;
    color: var(--app-text-muted);
    font-size: 13px;
    line-height: 1.6;
  }
}

.actions {
  display: flex;
  gap: 10px;
  margin-top: 18px;
}

</style>
