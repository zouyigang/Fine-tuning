<template>
  <div class="tags-view">
    <el-scrollbar class="tags-scroll">
      <div class="tags-wrap">
        <router-link
          v-for="tag in appStore.visitedTags"
          :key="tag.path"
          :to="tag.path"
          class="tag-item"
          :class="{ active: isActive(tag) }"
        >
          <span class="dot" />
          {{ tag.title }}
          <el-icon
            v-if="appStore.visitedTags.length > 1"
            class="close"
            @click.prevent.stop="closeTag(tag)"
          >
            <Close />
          </el-icon>
        </router-link>
      </div>
    </el-scrollbar>
  </div>
</template>

<script setup>
import { watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '@/store/app'

const appStore = useAppStore()
const route = useRoute()
const router = useRouter()

const isActive = (tag) => tag.path === route.path

watch(
  () => route.path,
  () => appStore.addTag(route),
  { immediate: true }
)

function closeTag(tag) {
  const remaining = appStore.removeTag(tag.path)
  if (isActive(tag)) {
    const last = remaining[remaining.length - 1]
    router.push(last ? last.path : '/dashboard/index')
  }
}
</script>

<style lang="scss" scoped>
.tags-view {
  height: $tags-height;
  background: #fff;
  border-top: 1px solid #f0f0f0;
  box-shadow: 0 1px 3px rgba(0, 21, 41, 0.04);
  padding: 0 12px;
  display: flex;
  align-items: center;
}

.tags-scroll {
  width: 100%;
}

.tags-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
}

.tag-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 28px;
  padding: 0 10px;
  font-size: 12px;
  color: #5e6470;
  background: #fafafa;
  border: 1px solid #e4e7ed;
  border-radius: 3px;
  cursor: pointer;

  .dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #c0c4cc;
  }

  &.active {
    color: #fff;
    background: $primary-color;
    border-color: $primary-color;
    .dot {
      background: #fff;
    }
  }

  .close {
    font-size: 12px;
    border-radius: 50%;
    &:hover {
      background: rgba(0, 0, 0, 0.15);
    }
  }
}
</style>
