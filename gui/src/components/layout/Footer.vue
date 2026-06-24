<template>
  <div class="footer-container">
    <!-- <div class="xuntou-khd" v-if="settingConfig.client_type == 2">
      <span class="label-tips">mini迅投客户端:</span>
      <div v-if="isQmtState == true" class="footer-cell">
        <div class="tips">已打开</div>
        <el-icon color="green"><CircleCheckFilled /></el-icon>
      </div>
      <div v-else class="footer-cell">
        <div class="tips">暂未打开</div>
        <el-icon color="red"><CircleCloseFilled /></el-icon>
      </div>
    </div> -->

    <div class="api-state">
      <span class="label-tips">API服务:</span>
      <div v-if="apiRunning" class="footer-cell">
        <div class="tips">运行中</div>
        <el-icon color="green"><CircleCheckFilled /></el-icon>
      </div>
      <div v-else class="footer-cell">
        <div class="tips">未运行</div>
        <el-icon color="red"><CircleCloseFilled /></el-icon>
      </div>
    </div>
    <div class="date-time-cell">
      <!-- 时间显示 -->
      <div class="time-cell">
        <span class="time">{{ time }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { CircleCheckFilled, CircleCloseFilled } from '@element-plus/icons-vue'
import { isHttpServerRunning, isProcessExist } from '@/api/comm_tube'
import { useCommonStore } from '@/store/common'

const time = ref('')
const commonStore = useCommonStore()
const apiRunning = computed(() => commonStore.apiServerRunning)
defineOptions({
  name: 'LayoutFooter'
})

const refreshApiServerState = async () => {
  try {
    const running = await isHttpServerRunning()
    commonStore.setApiServerRunning(running)
  } catch (error) {
    commonStore.setApiServerRunning(false)
  }
}

onMounted(async () => {
  await refreshApiServerState()

  setInterval(async () => {
    isProcessExist()
  }, 2000)

  setInterval(async () => {
    await refreshApiServerState()
  }, 2000)

  setInterval(async () => {
    time.value = new Date().toLocaleString()
  }, 1000)
})
</script>

<style lang="less" scoped>
.footer-container {
  display: flex;
  align-items: center;
  // justify-content: space-between;
  height: 100%;
  .label-tips {
    color: #fff;
    font-size: 12px;
    margin-right: 4px;
    font-weight: bold;
  }
  .footer-cell {
    display: flex;
    align-items: center;
    margin-top: 2px;
    .tips {
      color: #fff;
      margin-right: 4px;
      font-size: 12px;
      margin-top: -2px;
      font-weight: bold;
    }
  }
  .xuntou-khd {
    display: flex;
    align-items: center;
  }
  .api-state {
    display: flex;
    align-items: center;
  }
  .ths-state {
    display: flex;
    align-items: center;
  }
  .date-time-cell {
    display: flex;
    align-items: center;
    position: absolute;
    right: 10px;
    .time-cell {
      display: flex;
      color: #fff;
      font-size: 16px;
      margin-right: 4px;
      font-weight: bold;
    }
  }
}
</style>
