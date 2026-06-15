<template>
  <div class="navbar">
    <div class="left">
      <el-icon class="collapse-btn" @click="appStore.toggleSidebar()">
        <Fold v-if="!appStore.sidebarCollapsed" />
        <Expand v-else />
      </el-icon>
      <el-breadcrumb separator="/">
        <el-breadcrumb-item v-for="item in breadcrumbs" :key="item.path">
          {{ item.title }}
        </el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <div class="right">
      <el-tooltip content="全屏" placement="bottom">
        <el-icon class="action-icon" @click="toggleFullscreen"><FullScreen /></el-icon>
      </el-tooltip>
      <el-badge :value="5" class="action-icon">
        <el-icon><Bell /></el-icon>
      </el-badge>
      <el-dropdown>
        <div class="user-info">
          <el-avatar :size="30" class="avatar">{{ userStore.userInfo.name.charAt(0) }}</el-avatar>
          <div class="user-meta">
            <span class="name">{{ userStore.userInfo.name }}</span>
            <span class="role">{{ userStore.userInfo.role }}</span>
          </div>
          <el-icon><CaretBottom /></el-icon>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item disabled>{{ userStore.userInfo.dept }}</el-dropdown-item>
            <el-dropdown-item divided>个人中心</el-dropdown-item>
            <el-dropdown-item>修改密码</el-dropdown-item>
            <el-dropdown-item divided>退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '@/store/app'
import { useUserStore } from '@/store/user'

const appStore = useAppStore()
const userStore = useUserStore()
const route = useRoute()

const breadcrumbs = computed(() =>
  route.matched
    .filter((r) => r.meta?.title)
    .map((r) => ({ path: r.path, title: r.meta.title }))
)

function toggleFullscreen() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen()
  } else {
    document.exitFullscreen()
  }
}
</script>

<style lang="scss" scoped>
.navbar {
  height: $navbar-height;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
}

.left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.collapse-btn {
  font-size: 20px;
  cursor: pointer;
  color: #5e6470;
  &:hover {
    color: $primary-color;
  }
}

.right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.action-icon {
  font-size: 18px;
  cursor: pointer;
  color: #5e6470;
  &:hover {
    color: $primary-color;
  }
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  outline: none;

  .avatar {
    background: $primary-color;
  }
  .user-meta {
    display: flex;
    flex-direction: column;
    line-height: 1.2;
    .name {
      font-size: 13px;
      font-weight: 600;
    }
    .role {
      font-size: 12px;
      color: #8a919f;
    }
  }
}
</style>
