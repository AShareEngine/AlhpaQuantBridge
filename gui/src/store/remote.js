import { useCommonStore } from '@/store/common.js'
import dayjs from 'dayjs'
import { ElMessage } from 'element-plus'
import { defineStore } from 'pinia'

export const useRemoteStore = defineStore('remote', {
  state: () => ({
    connectState: 0,
    messagesArr: [],
    clientId: null
  }),
  actions: {
    changeConnectState(params) {
      this.connectState = params
    },
    changeClientId(params) {
      this.clientId = params
    },
    clearMessagesArr() {
      this.messagesArr = []
    },
    async setRemoteStore(params) {
      if (params.show && params.show === true) {
        if (params.showType) {
          ElMessage({
            message: params.message,
            type: params.showType
          })
        } else {
          ElMessage.info(params.message)
        }
      }

      // 事件处理
      if (params.type) {
        if (params.type == 'qmtProcessCheck') {
          useCommonStore().changeisQmtState(params.event)
        }
        if (params.type == 'accSubSuccess') {
          useCommonStore().changeisAccSubState(params.event)
        }
        if (params.type == 'thsProcessCheck') {
          useCommonStore().changeisThsState(params.event)
        }
      }
      // 本地 API 与交易回调消息
      if (params.data) {
        params.message = typeof params.data === 'string' ? params.data : JSON.stringify(params.data)
      } else {
        this.clientId = params.unique_id
      }
      if (params.message && params.message.length > 2) {
        params.date = dayjs().format('MM-DD HH:mm:ss')
        this.messagesArr.push({
          message: params.message,
          date: params.date
        })
      }
    }
  }
})
