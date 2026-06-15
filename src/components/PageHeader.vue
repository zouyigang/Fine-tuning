<template>
  <div class="page-header">
    <div class="title-row">
      <h2 class="title">{{ title }}</h2>
      <div class="extra">
        <slot name="extra" />
      </div>
    </div>
    <p v-if="description" class="desc">{{ description }}</p>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  description: { type: String, default: '' }
})
</script>

<style lang="scss" scoped>
.page-header {
  background: #fff;
  border-radius: 4px;
  padding: 16px 20px;
  margin-bottom: 16px;
  border-left: 3px solid $primary-color;
}
.title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}
.desc {
  margin: 8px 0 0;
  font-size: 13px;
  color: #8a919f;
  line-height: 1.6;
}
</style>
