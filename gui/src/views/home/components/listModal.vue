<template>
  <el-dialog v-model="dialogVisible" :title="editDic ? '编辑 API 任务' : '新建 API 任务'" width="560px" center>
    <el-form :model="form" label-width="120px">
      <el-form-item label="任务名称" required>
        <el-input v-model="form.name" placeholder="请输入任务名称" />
      </el-form-item>
      <el-form-item label="关联账号" required>
        <el-select v-model="form.account_id" placeholder="请选择账号" :disabled="!!fixedAccountId">
          <el-option v-for="item in accountOptions" :key="item.id" :label="item.label" :value="item.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="任务编号" required>
        <el-input v-model="form.strategy_code" placeholder="例如 API001，外部下单时传 strategy_code" maxlength="32" />
      </el-form-item>
      <el-form-item label="强制限价单">
        <el-switch v-model="form.open_mandatory_limit_order" :active-value="1" :inactive-value="0" />
      </el-form-item>
      <el-form-item label="初始资金">
        <el-input-number v-model="form.allocation_amount" :min="0" :precision="2" :step="1000" />
      </el-form-item>
      <el-form-item label="手续费设置">
        <div class="service-charge">
          <div class="service-charge-item">
            <span>费率</span>
            <el-input-number v-model="form.service_charge" :min="0" :precision="6" :step="0.00001" />
          </div>
          <div class="service-charge-item">
            <span>最低手续费</span>
            <el-input-number v-model="form.lower_limit_of_fees" :min="0" :precision="2" :step="1" />
          </div>
        </div>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="handleSubmit">保存</el-button>
        <el-button @click="dialogVisible = false">取消</el-button>
      </el-form-item>
    </el-form>
  </el-dialog>
</template>

<script setup>
import { createTask, getAccountList, getUniqueID } from '@/api/comm_tube'
import { ElMessage, ElMessageBox } from 'element-plus'
import { reactive, ref } from 'vue'

const emit = defineEmits(['getTaskList', 'callBack'])
const dialogVisible = ref(false)
const accountOptions = ref([])
const fixedAccountId = ref(undefined)
const isEdit = ref(false)
const editDic = ref(null)

const form = reactive({
  name: '',
  account_id: undefined,
  strategy_code: '',
  allocation_amount: 100000,
  service_charge: 0.00025,
  lower_limit_of_fees: 5,
  open_mandatory_limit_order: 1
})

const loadAccountOptions = async () => {
  const res = await getAccountList()
  accountOptions.value = (res || [])
    .filter((item) => item.status === 1)
    .map((item) => ({
      id: item.id,
      label: `${item.client_type === 1 ? '同花顺' : 'QMT'} - ${item.client_type === 1 ? item.ths_client_id : item.client_id}`
    }))
}

const showModal = async (dic, initialAccountId) => {
  dialogVisible.value = true
  fixedAccountId.value = initialAccountId || undefined
  await loadAccountOptions()

  if (dic) {
    isEdit.value = true
    editDic.value = dic
    form.name = dic.name
    form.account_id = dic.account_id
    form.strategy_code = dic.strategy_code
    form.allocation_amount = Number(dic.allocation_amount || dic.can_use_amount || 100000)
    form.service_charge = Number(dic.service_charge ?? 0.00025)
    form.lower_limit_of_fees = Number(dic.lower_limit_of_fees ?? 5)
    form.open_mandatory_limit_order = dic.open_mandatory_limit_order ?? 1
  } else {
    isEdit.value = false
    editDic.value = null
    form.name = ''
    form.account_id = initialAccountId || undefined
    form.strategy_code = ''
    form.allocation_amount = 100000
    form.service_charge = 0.00025
    form.lower_limit_of_fees = 5
    form.open_mandatory_limit_order = 1
  }
}

const handleSubmit = async () => {
  if (!form.name) {
    ElMessage.error('请输入任务名称')
    return
  }
  if (!form.account_id) {
    ElMessage.error('请选择关联账号')
    return
  }
  if (!form.strategy_code) {
    ElMessage.error('请输入任务编号')
    return
  }

  if (isEdit.value && editDic.value.strategy_code !== form.strategy_code) {
    const confirm = await ElMessageBox.confirm('任务编号是外部 API 的调用标识，确认修改吗？', '确认', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning'
    }).catch(() => false)
    if (!confirm) return
  }

  const userId = await getUniqueID()
  const payload = {
    id: editDic.value?.id || undefined,
    name: form.name,
    account_id: form.account_id,
    strategy_code: form.strategy_code,
    order_count_type: 2,
    dynamic_calculation_type: 1,
    strategy_amount: 0,
    allocation_amount: form.allocation_amount,
    can_use_amount: form.allocation_amount,
    accruing_amounts: form.allocation_amount,
    service_charge: form.service_charge,
    lower_limit_of_fees: form.lower_limit_of_fees,
    task_type: 1,
    user_id: userId,
    platform: 10,
    position_ratio: 1,
    open_mandatory_limit_order: form.open_mandatory_limit_order,
    mock_allocation_amount: form.allocation_amount,
    mock_service_charge: form.service_charge,
    mock_lower_limit_of_fees: form.lower_limit_of_fees
  }

  await createTask(payload)
  emit('getTaskList')
  emit('callBack')
  dialogVisible.value = false
  ElMessage.success('保存成功')
}

defineExpose({
  showModal
})
</script>

<style scoped lang="less">
.service-charge {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.service-charge-item {
  display: flex;
  flex-direction: column;
  gap: 6px;

  span {
    color: #667085;
    font-size: 12px;
  }
}
</style>
