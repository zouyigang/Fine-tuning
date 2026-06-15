<template>
  <div class="sidebar" :class="{ collapsed: appStore.sidebarCollapsed }">
    <div class="logo">
      <el-icon class="logo-icon"><Cpu /></el-icon>
      <span v-show="!appStore.sidebarCollapsed" class="logo-text">模型微调平台</span>
    </div>
    <el-scrollbar>
      <el-menu
        :default-active="activeMenu"
        :collapse="appStore.sidebarCollapsed"
        :collapse-transition="false"
        background-color="#001529"
        text-color="#b7c0cd"
        active-text-color="#ffffff"
        router
      >
        <template v-for="route in menuRoutes" :key="route.path">
          <!-- 单层菜单（工作台） -->
          <el-menu-item v-if="route.meta?.single" :index="resolvePath(route, route.children[0])">
            <el-icon><component :is="route.meta.icon" /></el-icon>
            <template #title>{{ route.meta.title }}</template>
          </el-menu-item>

          <!-- 多层菜单 -->
          <el-sub-menu v-else :index="route.path">
            <template #title>
              <el-icon><component :is="route.meta.icon" /></el-icon>
              <span>{{ route.meta.title }}</span>
            </template>
            <el-menu-item
              v-for="child in route.children"
              :key="child.path"
              :index="resolvePath(route, child)"
            >
              <el-icon><component :is="child.meta.icon" /></el-icon>
              <template #title>{{ child.meta.title }}</template>
            </el-menu-item>
          </el-sub-menu>
        </template>
      </el-menu>
    </el-scrollbar>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { asyncRoutes } from '@/router'
import { useAppStore } from '@/store/app'

const appStore = useAppStore()
const route = useRoute()

const menuRoutes = computed(() => asyncRoutes.filter((r) => !r.meta?.hidden))
const activeMenu = computed(() => route.path)

function resolvePath(parent, child) {
  return `${parent.path}/${child.path}`.replace(/\/+/g, '/')
}
</script>

<style lang="scss" scoped>
.sidebar {
  width: $sidebar-width;
  height: 100%;
  background-color: $sidebar-bg;
  transition: width 0.28s;
  display: flex;
  flex-direction: column;
  overflow: hidden;

  &.collapsed {
    width: $sidebar-collapsed-width;
  }
}

.logo {
  height: $navbar-height;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 18px;
  color: #fff;
  flex-shrink: 0;
  background-color: #002140;

  .logo-icon {
    font-size: 24px;
    color: $primary-color;
  }
  .logo-text {
    font-size: 16px;
    font-weight: 600;
    white-space: nowrap;
  }
}

:deep(.el-menu) {
  border-right: none;
}
</style>
