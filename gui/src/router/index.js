import { createRouter, createWebHashHistory } from 'vue-router'

export const routes = [
  {
    path: '/',
    name: 'Loading',
    component: () => import('../views/loading/index.vue'),
    show: false,
    meta: {
      title: '启动中',
      showBack: false
    }
  },
  {
    path: '/home',
    name: 'Home',
    chName: 'API任务',
    icon: 'House',
    component: () => import('../views/home/index.vue'),
    redirect: '/home/list',
    children: [
      {
        path: '/home/detail',
        name: 'HomeDetail',
        component: () => import('../views/home/components/detail.vue'),
        meta: {
          title: '任务详情',
          showBack: true
        }
      },
      {
        path: '/home/list',
        name: 'HomeList',
        component: () => import('../views/home/components/list.vue'),
        meta: {
          title: 'API任务',
          showBack: false
        }
      }
    ]
  },
  {
    path: '/api',
    name: 'api',
    chName: 'API服务',
    icon: 'List',
    component: () => import('../views/httpserver/index.vue'),
    meta: {
      title: 'API服务',
      showBack: false
    }
  },
  {
    path: '/logging',
    name: 'Logging',
    chName: '查看日志',
    icon: 'InfoFilled',
    component: () => import('../views/logging/index.vue'),
    meta: {
      title: '日志',
      showBack: false
    }
  },
  {
    path: '/setting',
    name: 'Setting',
    chName: '设置',
    icon: 'Setting',
    component: () => import('../views/setting/index.vue'),
    redirect: '/setting/local',
    children: [
      {
        path: '/setting/local',
        name: 'SettingLocal',
        component: () => import('../views/setting/components/local.vue'),
        meta: {
          title: '本地设置',
          showBack: false
        }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

export default router
