<template>
  <div ref="chartRef" :style="{ height, width: '100%' }" />
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, onActivated, watch, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  option: { type: Object, required: true },
  height: { type: String, default: '320px' }
})

const chartRef = ref(null)
let chart = null
let ro = null
let raf = null

function render() {
  if (!chart && chartRef.value) {
    chart = echarts.init(chartRef.value)
  }
  chart && chart.setOption(props.option, true)
}

// 容器宽度为 0（被 keep-alive 移出布局/隐藏）时跳过，避免图表被压缩成一条线
function resize() {
  if (chart && chartRef.value && chartRef.value.clientWidth) {
    chart.resize()
  }
}

// 用 rAF 合并连续触发（拖拽改变窗口大小时 ResizeObserver 会高频回调）
function scheduleResize() {
  if (raf) return
  raf = requestAnimationFrame(() => {
    raf = null
    resize()
  })
}

onMounted(() => {
  nextTick(render)
  // 监听容器自身尺寸：窗口缩放、keep-alive 重新显示、布局变化都会触发，
  // 容器脱离布局（宽 0）时不会回调，从根本上避免“缩在一起”的问题
  ro = new ResizeObserver(scheduleResize)
  if (chartRef.value) ro.observe(chartRef.value)
})

// keep-alive 缓存的页面被重新激活时，主动补一次 resize 以贴合当前容器尺寸
// （ResizeObserver 在后台标签可能被节流，此生命周期不依赖 rAF，确保“改窗口大小后再打开菜单”一定生效）
onActivated(() => nextTick(resize))

onBeforeUnmount(() => {
  if (raf) cancelAnimationFrame(raf)
  ro && ro.disconnect()
  ro = null
  chart && chart.dispose()
  chart = null
})

watch(() => props.option, render, { deep: true })
</script>
