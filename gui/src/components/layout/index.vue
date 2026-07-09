<template>
  <el-container class="main-container">
    <LayoutSide />
    <el-container class="container">
      <LayoutHeader class="header" />
      <el-main class="main">
        <router-view></router-view>
      </el-main>
      <el-footer class="footer">
        <LayoutFooter />
      </el-footer>
    </el-container>
  </el-container>
</template>

<script setup>
import LayoutSide from './Side.vue'
import LayoutHeader from './Header.vue'
import LayoutFooter from './Footer.vue'

defineOptions({
  name: 'Layout'
})
</script>

<style lang="less" scoped>
.main-container {
  box-sizing: border-box;
  height: 100vh;
  overflow-y: hidden;
  .container {
    position: relative;
    background: var(--app-bg);
    .header {
      position: absolute;
      width: 100%;
      z-index: 1000;
      height: 50px;
    }
    .main {
      padding: 0;
      background: var(--app-bg);
      overflow: hidden;
      position: absolute;
      bottom: 0;
      left: 0;
      right: 0;
      top: 50px;
      height: calc(100vh - 90px);
    }
    .footer {
      position: absolute;
      bottom: 0;
      left: 0;
      right: 0;
      height: 40px;
      background: var(--app-sidebar);
    }
  }
}
</style>
