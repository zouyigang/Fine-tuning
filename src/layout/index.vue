<template>
  <div class="app-wrapper">
    <Sidebar class="sidebar-container" />
    <div class="main-container" :class="{ collapsed: appStore.sidebarCollapsed }">
      <div class="fixed-header">
        <Navbar />
        <TagsView />
      </div>
      <section class="app-main">
        <router-view v-slot="{ Component }">
          <transition name="fade-transform" mode="out-in">
            <keep-alive>
              <component :is="Component" />
            </keep-alive>
          </transition>
        </router-view>
      </section>
    </div>
  </div>
</template>

<script setup>
import Sidebar from './components/Sidebar.vue'
import Navbar from './components/Navbar.vue'
import TagsView from './components/TagsView.vue'
import { useAppStore } from '@/store/app'

const appStore = useAppStore()
</script>

<style lang="scss" scoped>
.app-wrapper {
  height: 100%;
  display: flex;
}

.sidebar-container {
  flex-shrink: 0;
}

.main-container {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.fixed-header {
  flex-shrink: 0;
}

.app-main {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 12px 16px;
  background-color: $page-bg;
}
</style>
