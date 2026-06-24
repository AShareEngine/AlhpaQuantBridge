<template>
  <div class="p-home-container">
    <div class="p-home-container-content">
      <router-view />
    </div>
    <transition name="terminal-transition">
      <Terminal :showTerminal="showTerminal" :class="showTerminal ? 'p-terminal' : 'p-terminal-hide'"/>
    </transition>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import  Terminal  from '@/components/terminal/index.vue'
import { useCommonStore } from '@/store/common.js'
const commonStoreDic = computed(() => {
  return useCommonStore()
})
const showTerminal = computed(() => {
  return commonStoreDic.value.showTerminal
})
</script>

<style scoped lang="less">
.p-home-container{
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  .p-home-container-content{
    flex: 1;
    overflow: hidden;
    display: flex;
    // flex-direction: column;
  }
  .p-terminal{
    flex: 1;
    min-height: 140px;
    max-height: 140px;
    width: 100%;
    transition: all 0.1s ease-in-out;
  }
  .p-terminal-hide{
    flex: 1;
    min-height: 50px;
    max-height: 50px;
    width: 100%;
    transition: all 0.1s ease-in-out;
  }
}

.terminal-transition-enter-active,
.terminal-transition-leave-active {
  transition: all 0.1s ease-in-out;
}

.terminal-transition-enter-from,
.terminal-transition-leave-to {
  opacity: 0;
  transform: translateY(20px);
}
</style>
