import { defineStore } from 'pinia'
import { ref } from 'vue'

// 全局应用状态：侧边栏折叠 + 多页签
export const useAppStore = defineStore('app', () => {
  const sidebarCollapsed = ref(false)

  // 多页签（tags-view）
  const visitedTags = ref([])

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function addTag(route) {
    if (route.meta?.hidden || !route.name) return
    const exists = visitedTags.value.find((t) => t.path === route.path)
    if (!exists) {
      visitedTags.value.push({
        path: route.path,
        title: route.meta?.title || route.name,
        name: route.name
      })
    }
  }

  function removeTag(targetPath) {
    const idx = visitedTags.value.findIndex((t) => t.path === targetPath)
    if (idx > -1) visitedTags.value.splice(idx, 1)
    return visitedTags.value
  }

  function removeOtherTags(targetPath) {
    visitedTags.value = visitedTags.value.filter((t) => t.path === targetPath)
  }

  return {
    sidebarCollapsed,
    visitedTags,
    toggleSidebar,
    addTag,
    removeTag,
    removeOtherTags
  }
})
