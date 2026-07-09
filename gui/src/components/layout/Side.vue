<template>
  <el-aside width="200px" class="side-container">
    <img src="@/assets/images/logo.png" :class="['logo']" style="width:80px;height:80px">
    <el-menu
      :default-active="activeMenu"
      active-text-color="#ffffff"
      background-color="#243447"
      class="el-menu-vertical"
      text-color="#d7e1eb"
      @select="handleSelect"
    >
      <el-menu-item
        v-for="route in menuRoutes"
        :key="route.name"
        :index="route.name"
        :data-route-name="route.name"
      >
        <el-icon>
          <component :is="ElementPlusIconsVue[route.icon]" />
        </el-icon>
        <span>{{ route.chName }}</span>
      </el-menu-item>
    </el-menu>

    <div class="side-bottom">
      <CheckUpdate />
    </div>
  </el-aside>
</template>

<script setup>
import { computed } from 'vue'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import CheckUpdate from '@/components/CheckUpdate/index.vue'
import { routes } from '@/router/index.js'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const menuRoutes = computed(() => {
  return routes.filter(route => route.show !== false)
})

const activeMenu = computed(() => {
  const matched = route.matched.find(record => menuRoutes.value.some(item => item.name === record.name))
  return matched?.name || route.name
})

const handleSelect = (key) => {
  router.push({ name: key })
}
</script>

<style scoped lang='less'>
.logo {
  transition: all 0.3s ease;
}

.el-menu-vertical {
  border-right: none;
  width: 100%;
  margin-top: 14px;
  --el-menu-hover-bg-color: rgba(255, 255, 255, 0.08);
}

.el-menu-vertical :deep(.el-menu-item) {
  font-weight: 700;
}

.el-menu-vertical :deep(.el-menu-item.is-active) {
  background: var(--app-primary);
}

.side-container {
  background: var(--app-sidebar);
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 30px;
}

.side-bottom {
  position: absolute;
  bottom: 10px;
  left: 20px;
  right: 0;
}

.side-bottom :deep(.el-button.is-link) {
  color: #ff7a7a;
}
</style> 
