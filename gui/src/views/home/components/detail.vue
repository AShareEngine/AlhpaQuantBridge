<template>
  <div class="detail-container">
    <div class="detail-container-content">
      <div class="bottom-container-left">
        <div class="cur-position">
          <div class="section-toolbar">
            <span class="section-title">本地持仓</span>
            <div>
              <el-button size="small" type="primary" @click="autoPositionAction">自动添加</el-button>
              <el-button size="small" type="primary" @click="addPositionAction">手动添加</el-button>
            </div>
          </div>
          <el-table :data="currentPositionList" stripe style="width: 100%; margin-top: 10px" size="small" height="100%">
            <el-table-column align="center" label="股票代码" width="140">
              <template #default="{ row }">
                {{ row.security_code }}
                ({{ row.security_name }})
              </template>
            </el-table-column>
            <el-table-column align="center" label="数量" width="150">
              <template #default="{ row }">
                <span v-if="!row.is_edit">{{ row.volume }}</span>
                <el-input-number size="small" v-else v-model="row.volume" :min="0" />
              </template>
            </el-table-column>
            <el-table-column align="center" label="均价" width="150">
              <template #default="{ row }">
                {{ Number(row.average_price || 0).toFixed(2) }}
              </template>
            </el-table-column>
            <el-table-column align="center" label="市值">
              <template #default="{ row }">
                {{ (Number(row.average_price || 0) * Number(row.volume || 0)).toFixed(2) }}
              </template>
            </el-table-column>
            <el-table-column fixed="right" label="操作" align="center" :width="isEdit ? 200 : 100">
              <template #default="{ row }">
                <el-button v-if="!row.is_edit" @click="editPosition(row)" type="primary" size="small">编辑</el-button>
                <div v-else class="row-actions">
                  <el-button @click="savePosition(row)" type="success" size="small">保存</el-button>
                  <el-button @click="editPosition(row)" size="small">取消</el-button>
                  <el-button @click="deletePosition(row)" type="danger" size="small">删除</el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>
          <div class="task-detail">
            <span>任务编号: {{ taskDic.strategy_code || '-' }}</span>
            <span>可用资金: {{ Number(taskDic.can_use_amount || 0).toFixed(2) }}</span>
          </div>
        </div>

        <div class="place-orders">
          <div class="section-toolbar">
            <span class="section-title">今日成交</span>
          </div>
          <el-table stripe :data="todayTradeList" size="small" height="100%">
            <el-table-column prop="created_at" label="时间" />
            <el-table-column prop="stock_code" label="股票代码" />
            <el-table-column label="价格">
              <template #default="{ row }">
                {{ Number(row.traded_price || 0).toFixed(2) }}
              </template>
            </el-table-column>
            <el-table-column prop="traded_volume" label="数量" />
            <el-table-column label="金额">
              <template #default="{ row }">
                {{ Number(row.traded_amount || 0).toFixed(2) }}
              </template>
            </el-table-column>
            <el-table-column label="方向">
              <template #default="{ row }">
                <el-tag :type="row.order_type === 23 ? 'success' : 'danger'" size="small">{{ row.order_type === 23 ? '买入' : '卖出' }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <div class="bottom-container-right">
        <div class="task-info-container">
          <span class="section-title">API 调用</span>
          <el-descriptions :column="1" size="small" border style="margin-top: 10px">
            <el-descriptions-item label="任务ID">{{ taskDic.id || '-' }}</el-descriptions-item>
            <el-descriptions-item label="任务编号">{{ taskDic.strategy_code || '-' }}</el-descriptions-item>
            <el-descriptions-item label="状态">{{ taskDic.is_open == 1 ? '已开启' : '已关闭' }}</el-descriptions-item>
          </el-descriptions>
        </div>
        <div class="btn-container">
          <span class="section-title">操作</span>
          <div class="btn-container-inner">
            <el-button size="small" @click="editTask" plain>编辑</el-button>
            <el-button size="small" type="danger" @click="clearAllStockAction" plain>一键清仓</el-button>
            <el-button size="small" type="danger" @click="deleteStock" plain>删除</el-button>
          </div>
        </div>
      </div>
    </div>
    <ListModal ref="listModalRef" @callBack="getTaskDetailAction" />
    <AddPosition ref="addPositionRef" @callBack="getCurrentPositionList" />
    <AutoPostion ref="autoPositionRef" @callBack="getCurrentPositionList" />
  </div>
</template>

<script setup>
import { clearAllStockByTaskId, deletePositionById, deleteTask, getPositionByTaskId, getTaskDetail, queryTradeToday, updatePosition } from '@/api/comm_tube'
import { ElMessage, ElMessageBox } from 'element-plus'
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AddPosition from './addPosition.vue'
import AutoPostion from './autoPostion.vue'
import ListModal from './listModal.vue'

const router = useRouter()
const route = useRoute()
const listModalRef = ref(null)
const isEdit = ref(false)
const todayTradeList = ref([])
const currentPositionList = ref([])
const addPositionRef = ref(null)
const autoPositionRef = ref(null)
const taskDic = ref({})

const getTaskDetailAction = async () => {
  const res = await getTaskDetail({ id: route.query.id })
  taskDic.value = res
}

const queryTradeTodayAction = async () => {
  const list = await queryTradeToday(taskDic.value.id)
  todayTradeList.value = list || []
}

const getCurrentPositionList = async () => {
  const positions = await getPositionByTaskId(taskDic.value.id)
  currentPositionList.value = (positions || [])
    .filter((item) => item.volume > 0)
    .map((item) => ({
      ...item,
      is_edit: false
    }))
}

onMounted(async () => {
  await getTaskDetailAction()
  await queryTradeTodayAction()
  await getCurrentPositionList()
})

const editPosition = (row) => {
  isEdit.value = !isEdit.value
  currentPositionList.value = currentPositionList.value.map((item) => {
    if (item.security_code === row.security_code) {
      return {
        ...item,
        is_edit: !item.is_edit
      }
    }
    return item
  })
}

const clearAllStockAction = async () => {
  try {
    await ElMessageBox.confirm('确定要按当前任务持仓逐个卖出清仓吗？此操作不可恢复。', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await clearAllStockByTaskId(taskDic.value.id)
    ElMessage.success('已发起清仓')
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
    ElMessage.error(error.message || '清仓失败')
  }
}

const goToHome = () => {
  router.go(-1)
}

const deleteStock = async () => {
  try {
    await ElMessageBox.confirm(`是否确认删除任务"${taskDic.value.name}"`, '确认删除', {
      confirmButtonText: '是',
      cancelButtonText: '否'
    })
    await deleteTask({ id: taskDic.value.id })
    ElMessage.success('删除成功')
    goToHome()
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
    ElMessage.info('已取消')
  }
}

const editTask = async () => {
  listModalRef.value.showModal(taskDic.value)
}

const savePosition = async (row) => {
  isEdit.value = false
  await updatePosition(row.id, {
    volume: row.volume
  })
  await getCurrentPositionList()
  ElMessage.success('保存成功')
}

const autoPositionAction = () => {
  autoPositionRef.value.showModal({
    account_id: taskDic.value.account_id,
    task_id: taskDic.value.id
  })
}

const addPositionAction = () => {
  addPositionRef.value.showModal(taskDic.value.id)
}

const deletePosition = async (row) => {
  isEdit.value = false
  await deletePositionById(row.id)
  await getCurrentPositionList()
  ElMessage.success('删除成功')
}
</script>

<style scoped lang="less">
.detail-container {
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  height: 100%;
  width: 100%;
  overflow: hidden;
}

.detail-container-content {
  display: flex;
  flex-direction: row;
  padding: 10px;
  gap: 10px;
  flex: 1;
  overflow: hidden;
}

.bottom-container-left {
  width: 65%;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 10px;
  height: 100%;
}

.section-title {
  font-weight: bold;
  font-size: 14px;
  color: #434343;
  margin-right: 10px;
}

.section-toolbar {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
}

.cur-position,
.place-orders {
  display: flex;
  flex-direction: column;
  background: #fff;
  flex: 1;
  padding: 7px;
  min-height: 0;
}

.cur-position {
  padding-bottom: 0;
}

.el-table {
  flex: 1;
  overflow: hidden;
}

.task-detail {
  display: flex;
  gap: 18px;
  font-size: 13px;
  height: 30px;
  align-items: center;
  color: #434343;
}

.bottom-container-right {
  flex: 1;
  min-height: 100%;
}

.task-info-container,
.btn-container {
  padding: 10px;
  background: #fff;
}

.btn-container {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
}

.btn-container-inner {
  display: flex;
  flex-wrap: wrap;
  background: #fff;
  gap: 10px;
  margin-top: 10px;
  justify-content: flex-start;

  .el-button + .el-button {
    margin-left: 0;
  }
}

.row-actions {
  display: flex;
  align-items: center;
}
</style>
