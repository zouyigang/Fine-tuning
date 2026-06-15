<template>
  <div class="stat-card">
    <div class="icon" :style="{ background: bg }">
      <el-icon :size="24"><component :is="icon" /></el-icon>
    </div>
    <div class="info">
      <div class="value">{{ value }}<span v-if="unit" class="unit">{{ unit }}</span></div>
      <div class="label">{{ label }}</div>
    </div>
    <div v-if="trend !== null" class="trend" :class="trend >= 0 ? 'up' : 'down'">
      <el-icon><component :is="trend >= 0 ? 'Top' : 'Bottom'" /></el-icon>
      {{ Math.abs(trend) }}%
    </div>
  </div>
</template>

<script setup>
defineProps({
  label: String,
  value: [String, Number],
  unit: { type: String, default: '' },
  icon: { type: String, default: 'DataLine' },
  bg: { type: String, default: '#2f54eb' },
  trend: { type: Number, default: null }
})
</script>

<style lang="scss" scoped>
.stat-card {
  background: #fff;
  border-radius: 4px;
  padding: 18px 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  position: relative;
  height: 100%;
}
.icon {
  width: 52px;
  height: 52px;
  border-radius: 10px;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.info {
  flex: 1;
  min-width: 0;
}
.value {
  font-size: 24px;
  font-weight: 700;
  line-height: 1.2;
  .unit {
    font-size: 13px;
    font-weight: 400;
    color: #8a919f;
    margin-left: 4px;
  }
}
.label {
  font-size: 13px;
  color: #8a919f;
  margin-top: 4px;
}
.trend {
  position: absolute;
  top: 16px;
  right: 16px;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 2px;
  &.up {
    color: #f5222d;
  }
  &.down {
    color: #52c41a;
  }
}
</style>
