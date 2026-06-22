<template>
  <div class="screen" :class="{ ready }">
    <!-- 动态背景：网格 + 光晕 -->
    <div class="bg-grid"></div>
    <div class="bg-glow glow-1"></div>
    <div class="bg-glow glow-2"></div>

    <!-- 顶部标题栏 -->
    <header class="screen-head">
      <div class="head-side left">
        <span class="chip"><i class="dot ok"></i>集群在线</span>
        <span class="chip"><i class="dot ok"></i>调度正常</span>
      </div>
      <h1 class="title">
        <span class="title-main">公安模型微调通用平台</span>
        <span class="title-sub">数 据 可 视 化 指 挥 中 心</span>
      </h1>
      <div class="head-side right">
        <div class="clock">
          <span class="time">{{ now.time }}</span>
          <span class="date">{{ now.date }} {{ now.week }}</span>
        </div>
        <button class="exit-btn" @click="exit">返回工作台</button>
      </div>
    </header>

    <!-- 主体三栏 -->
    <main class="screen-body">
      <!-- 左栏 -->
      <section class="col col-side">
        <Panel title="核心指标概览" sub="REAL-TIME OVERVIEW">
          <div class="metric-grid">
            <div v-for="m in data.headline" :key="m.key" class="metric-cell">
              <div class="metric-val">
                <CountUp :value="m.value" />
                <em>{{ m.unit }}</em>
              </div>
              <div class="metric-label">{{ m.label }}</div>
              <div class="metric-trend" :class="{ up: m.up }">
                {{ m.up ? '▲' : '▼' }} {{ m.trend }}%
              </div>
            </div>
          </div>
        </Panel>

        <Panel title="数据集类型分布" sub="DATASET DISTRIBUTION">
          <BaseChart :option="distOption" height="100%" />
        </Panel>

        <Panel title="各警种标注进度" sub="ANNOTATION PROGRESS">
          <BaseChart :option="annoOption" height="100%" />
        </Panel>
      </section>

      <!-- 中栏 -->
      <section class="col col-main">
        <div class="spotlight-row">
          <div v-for="s in data.spotlight" :key="s.label" class="spot-card">
            <div class="spot-ring"></div>
            <div class="spot-val">
              <CountUp :value="s.value" :decimals="String(s.value).includes('.') ? 1 : 0" />
              <em>{{ s.unit }}</em>
            </div>
            <div class="spot-label">{{ s.label }}</div>
            <div class="spot-sub">{{ s.sub }}</div>
          </div>
        </div>

        <Panel title="微调任务趋势（近 14 天）" sub="FINE-TUNING TASK TREND" class="grow">
          <BaseChart :option="trendOption" height="100%" />
        </Panel>

        <Panel title="GPU 集群实时负载" sub="GPU CLUSTER LOAD">
          <BaseChart :option="gpuOption" height="100%" />
        </Panel>
      </section>

      <!-- 右栏 -->
      <section class="col col-side">
        <Panel title="模型效果评估" sub="MODEL EVALUATION">
          <BaseChart :option="radarOption" height="100%" />
        </Panel>

        <Panel title="模型上线状态" sub="RELEASE PIPELINE">
          <div class="release-list">
            <div v-for="r in data.release" :key="r.name" class="release-item">
              <div class="release-top">
                <span class="rname">{{ r.name }}</span>
                <span class="rstage" :style="{ color: r.color }">{{ r.stage }}</span>
              </div>
              <div class="release-bar">
                <div class="release-fill" :style="{ width: r.percent + '%', background: r.color }"></div>
              </div>
            </div>
          </div>
        </Panel>

        <Panel title="实时操作流水" sub="LIVE OPERATION LOG">
          <div class="log-view">
            <div class="log-track" :class="{ run: data.logs.length }">
              <div v-for="log in loopLogs" :key="log.id + log.time" class="log-row">
                <span class="log-time">{{ log.time }}</span>
                <span class="log-tag" :class="log.level">{{ log.module }}</span>
                <span class="log-actor">{{ log.actor }}</span>
                <span class="log-text">{{ log.text }}</span>
              </div>
            </div>
          </div>
        </Panel>
      </section>
    </main>

    <!-- 底部滚动任务表 -->
    <footer class="screen-foot">
      <Panel title="微调任务运行状态" sub="TASK RUNNING STATUS" flat>
        <div class="task-table">
          <div class="t-head">
            <span>任务编号</span><span class="c-name">任务名称</span><span>基座模型</span>
            <span>资源</span><span>Loss</span><span class="c-prog">进度</span><span>状态</span><span>预计剩余</span>
          </div>
          <div class="t-body">
            <div v-for="t in data.tasks" :key="t.id" class="t-row">
              <span class="mono">{{ t.id }}</span>
              <span class="c-name">{{ t.name }}</span>
              <span>{{ t.base }}</span>
              <span class="mono">{{ t.gpu }}</span>
              <span class="mono">{{ t.loss }}</span>
              <span class="c-prog">
                <span class="mini-bar"><i :style="{ width: t.progress + '%', background: statusColor(t.status) }"></i></span>
                <em>{{ t.progress }}%</em>
              </span>
              <span class="status" :style="{ color: statusColor(t.status) }">
                <i class="s-dot" :style="{ background: statusColor(t.status) }"></i>{{ statusText(t.status) }}
              </span>
              <span class="mono">{{ t.eta }}</span>
            </div>
          </div>
        </div>
      </Panel>
    </footer>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, h } from 'vue'
import { useRouter } from 'vue-router'
import BaseChart from '@/components/BaseChart.vue'
import { getScreenData } from '@/api/modules/screen'

const router = useRouter()
const ready = ref(false)

const data = reactive({
  headline: [], spotlight: [], taskTrend: { dates: [] }, datasetDist: [],
  annotation: [], radar: { indicators: [], series: [] }, gpuNodes: [],
  release: [], logs: [], tasks: []
})

/* ---------- 轻量内联组件：数字滚动 ---------- */
const CountUp = {
  props: { value: { type: [Number, String], default: 0 }, decimals: { type: [Number, String], default: 0 } },
  setup(props) {
    const display = ref(0)
    let raf = null
    const animate = (to) => {
      const from = display.value
      const start = performance.now()
      const dur = 900
      const step = (t) => {
        const p = Math.min((t - start) / dur, 1)
        const e = 1 - Math.pow(1 - p, 3)
        display.value = from + (to - from) * e
        if (p < 1) raf = requestAnimationFrame(step)
      }
      cancelAnimationFrame(raf)
      raf = requestAnimationFrame(step)
    }
    animate(Number(props.value) || 0)
    return { display, props }
  },
  render() {
    const d = Number(this.props.decimals)
    const n = Number(this.display).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d })
    return h('span', n)
  }
}

/* ---------- 时钟 ---------- */
const now = reactive({ time: '', date: '', week: '' })
const WEEK = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六']
function tick() {
  const d = new Date()
  const p = (n) => String(n).padStart(2, '0')
  now.time = `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`
  now.date = `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
  now.week = WEEK[d.getDay()]
}

/* ---------- Panel 容器（内联组件，统一边框/标题样式） ---------- */
const Panel = {
  props: { title: String, sub: String, flat: Boolean },
  setup(props, { slots }) {
    return () => h('div', { class: ['panel', { flat: props.flat }] }, [
      h('div', { class: 'panel-head' }, [
        h('span', { class: 'panel-deco' }),
        h('span', { class: 'panel-title' }, props.title),
        props.sub ? h('span', { class: 'panel-sub' }, props.sub) : null
      ]),
      h('div', { class: 'panel-body' }, slots.default ? slots.default() : [])
    ])
  }
}

/* ---------- 状态字典 ---------- */
const statusColor = (s) => ({ running: '#00e5ff', finished: '#52c41a', queued: '#faad14', failed: '#ff4d6d' }[s] || '#8aa')
const statusText = (s) => ({ running: '训练中', finished: '已完成', queued: '排队中', failed: '失败' }[s] || s)

/* ---------- 滚动日志：复制一份实现无缝滚动 ---------- */
const loopLogs = computed(() => [...data.logs, ...data.logs])

/* ---------- ECharts 配置 ---------- */
const AXIS = '#7fa8d8'
const SPLIT = 'rgba(127,168,216,0.12)'

const distOption = computed(() => ({
  tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
  legend: { bottom: 0, textStyle: { color: AXIS, fontSize: 11 }, itemWidth: 10, itemHeight: 10 },
  color: ['#00e5ff', '#2f9bff', '#7c5cff', '#ff9f43', '#26de81', '#ff6b9d'],
  series: [{
    type: 'pie', radius: ['42%', '66%'], center: ['50%', '42%'],
    roseType: 'radius', avoidLabelOverlap: true,
    itemStyle: { borderColor: 'rgba(6,13,42,0.6)', borderWidth: 2 },
    label: { color: AXIS, fontSize: 11, formatter: '{b}\n{d}%' },
    labelLine: { length: 6, length2: 8 },
    data: data.datasetDist
  }]
}))

const annoOption = computed(() => ({
  grid: { left: 8, right: 24, top: 10, bottom: 6, containLabel: true },
  tooltip: { trigger: 'axis', formatter: '{b}: {c}%' },
  xAxis: { type: 'value', max: 100, axisLabel: { color: AXIS, formatter: '{value}%' }, splitLine: { lineStyle: { color: SPLIT } }, axisLine: { show: false } },
  yAxis: { type: 'category', inverse: true, data: data.annotation.map((a) => a.name), axisLabel: { color: AXIS }, axisLine: { lineStyle: { color: SPLIT } }, axisTick: { show: false } },
  series: [{
    type: 'bar', barWidth: 12,
    data: data.annotation.map((a) => a.value),
    label: { show: true, position: 'right', color: '#cfe3ff', formatter: '{c}%' },
    itemStyle: {
      borderRadius: 6,
      color: { type: 'linear', x: 0, y: 0, x2: 1, y2: 0, colorStops: [{ offset: 0, color: '#2f9bff' }, { offset: 1, color: '#00e5ff' }] }
    }
  }]
}))

const trendOption = computed(() => {
  const grad = (c1, c2) => ({ type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: c1 }, { offset: 1, color: c2 }] })
  return {
    tooltip: { trigger: 'axis' },
    legend: { right: 10, top: 0, textStyle: { color: AXIS }, icon: 'roundRect' },
    grid: { left: 12, right: 20, top: 36, bottom: 8, containLabel: true },
    xAxis: { type: 'category', boundaryGap: false, data: data.taskTrend.dates, axisLabel: { color: AXIS }, axisLine: { lineStyle: { color: SPLIT } } },
    yAxis: { type: 'value', axisLabel: { color: AXIS }, splitLine: { lineStyle: { color: SPLIT } } },
    series: [
      {
        name: '新建任务', type: 'line', smooth: true, symbol: 'circle', symbolSize: 6, showSymbol: false,
        lineStyle: { color: '#00e5ff', width: 2.5 }, itemStyle: { color: '#00e5ff' },
        areaStyle: { color: grad('rgba(0,229,255,0.35)', 'rgba(0,229,255,0)') }, data: data.taskTrend.created
      },
      {
        name: '完成任务', type: 'line', smooth: true, symbol: 'circle', symbolSize: 6, showSymbol: false,
        lineStyle: { color: '#7c5cff', width: 2.5 }, itemStyle: { color: '#7c5cff' },
        areaStyle: { color: grad('rgba(124,92,255,0.3)', 'rgba(124,92,255,0)') }, data: data.taskTrend.finished
      }
    ]
  }
})

const gpuOption = computed(() => ({
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  legend: { right: 10, top: 0, textStyle: { color: AXIS }, data: ['算力利用率', '显存占用'] },
  grid: { left: 12, right: 16, top: 34, bottom: 6, containLabel: true },
  xAxis: { type: 'category', data: data.gpuNodes.map((n) => n.name), axisLabel: { color: AXIS }, axisLine: { lineStyle: { color: SPLIT } } },
  yAxis: { type: 'value', max: 100, axisLabel: { color: AXIS, formatter: '{value}%' }, splitLine: { lineStyle: { color: SPLIT } } },
  series: [
    { name: '算力利用率', type: 'bar', barWidth: 14, data: data.gpuNodes.map((n) => n.util), itemStyle: { borderRadius: [4, 4, 0, 0], color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: '#00e5ff' }, { offset: 1, color: 'rgba(0,229,255,0.15)' }] } } },
    { name: '显存占用', type: 'bar', barWidth: 14, data: data.gpuNodes.map((n) => n.mem), itemStyle: { borderRadius: [4, 4, 0, 0], color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: '#7c5cff' }, { offset: 1, color: 'rgba(124,92,255,0.15)' }] } } }
  ]
}))

const radarOption = computed(() => ({
  tooltip: { trigger: 'item' },
  legend: { bottom: 0, textStyle: { color: AXIS }, data: data.radar.series.map((s) => s.name) },
  radar: {
    indicator: data.radar.indicators, radius: '62%', center: ['50%', '46%'],
    axisName: { color: AXIS, fontSize: 11 },
    splitLine: { lineStyle: { color: SPLIT } },
    splitArea: { areaStyle: { color: ['rgba(0,229,255,0.03)', 'rgba(0,229,255,0.06)'] } },
    axisLine: { lineStyle: { color: SPLIT } }
  },
  color: ['#00e5ff', '#ff9f43'],
  series: [{
    type: 'radar',
    data: data.radar.series.map((s) => ({
      name: s.name, value: s.value,
      areaStyle: { opacity: 0.25 }, lineStyle: { width: 2 }, symbolSize: 4
    }))
  }]
}))

/* ---------- 生命周期 ---------- */
let clockTimer = null
let dataTimer = null

async function load() {
  Object.assign(data, await getScreenData())
}

onMounted(async () => {
  tick()
  clockTimer = setInterval(tick, 1000)
  await load()
  ready.value = true
  // 周期刷新模拟实时跳动（后期对接真实接口同样生效）
  dataTimer = setInterval(load, 8000)
})

onBeforeUnmount(() => {
  clearInterval(clockTimer)
  clearInterval(dataTimer)
})

function exit() {
  router.push('/dashboard/index')
}
</script>

<style lang="scss" scoped>
$cyan: #00e5ff;
$txt: #cfe3ff;

.screen {
  position: fixed;
  inset: 0;
  background: radial-gradient(1200px 600px at 50% -10%, #123a7a 0%, #0a1f4d 40%, #060d2a 100%);
  color: $txt;
  font-family: 'Microsoft YaHei', system-ui, sans-serif;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  padding: 0 18px 16px;
  opacity: 0;
  transition: opacity 0.6s ease;
  &.ready { opacity: 1; }
}

/* 背景装饰 */
.bg-grid {
  position: absolute; inset: 0; pointer-events: none;
  background-image:
    linear-gradient(rgba(0, 229, 255, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 229, 255, 0.05) 1px, transparent 1px);
  background-size: 48px 48px;
  mask-image: radial-gradient(circle at 50% 40%, #000 30%, transparent 85%);
}
.bg-glow {
  position: absolute; border-radius: 50%; filter: blur(80px); pointer-events: none; opacity: 0.5;
}
.glow-1 { width: 480px; height: 480px; background: rgba(0, 130, 255, 0.35); top: -160px; left: -120px; }
.glow-2 { width: 520px; height: 520px; background: rgba(124, 92, 255, 0.28); bottom: -200px; right: -120px; }

/* 顶部标题 */
.screen-head {
  position: relative; z-index: 2;
  height: 78px; flex-shrink: 0;
  display: grid; grid-template-columns: 1fr auto 1fr; align-items: center;
}
.head-side { display: flex; align-items: center; gap: 14px; }
.head-side.right { justify-content: flex-end; }
.chip {
  display: inline-flex; align-items: center; gap: 6px;
  font-size: 13px; color: #9fc2f0;
  padding: 5px 12px; border-radius: 14px;
  background: rgba(0, 130, 255, 0.1); border: 1px solid rgba(0, 229, 255, 0.25);
}
.dot { width: 7px; height: 7px; border-radius: 50%; display: inline-block; }
.dot.ok { background: #26de81; box-shadow: 0 0 8px #26de81; animation: pulse 1.6s infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.35; } }

.title { text-align: center; line-height: 1.15; }
.title-main {
  display: block; font-size: 30px; font-weight: 800; letter-spacing: 4px;
  background: linear-gradient(180deg, #fff 30%, #6fd3ff 100%);
  -webkit-background-clip: text; background-clip: text; color: transparent;
  text-shadow: 0 2px 20px rgba(0, 229, 255, 0.4);
}
.title-sub { display: block; font-size: 13px; letter-spacing: 8px; color: #6fa8e0; margin-top: 2px; }

.clock { text-align: right; line-height: 1.25; }
.clock .time { font-size: 24px; font-weight: 700; color: #fff; font-variant-numeric: tabular-nums; letter-spacing: 1px; }
.clock .date { display: block; font-size: 12px; color: #8fb3e6; }
.exit-btn {
  cursor: pointer; color: #bfe0ff; font-size: 13px;
  padding: 8px 16px; border-radius: 8px;
  background: rgba(0, 130, 255, 0.12); border: 1px solid rgba(0, 229, 255, 0.3);
  transition: all 0.2s;
  &:hover { background: rgba(0, 229, 255, 0.25); color: #fff; }
}

/* 主体三栏 */
.screen-body {
  position: relative; z-index: 2;
  flex: 1; min-height: 0;
  display: grid; grid-template-columns: 1fr 1.45fr 1fr; gap: 14px;
  padding-top: 4px;
}
.col { display: flex; flex-direction: column; gap: 14px; min-height: 0; }
.col-side > .panel { flex: 1; min-height: 0; }
.col-main { min-height: 0; }
.col-main .grow { flex: 1.3; }

/* Panel 容器 */
:deep(.panel) {
  position: relative;
  display: flex; flex-direction: column; min-height: 0;
  background: linear-gradient(180deg, rgba(16, 40, 84, 0.55), rgba(10, 24, 56, 0.35));
  border: 1px solid rgba(0, 229, 255, 0.18);
  border-radius: 10px;
  backdrop-filter: blur(4px);
  box-shadow: inset 0 0 24px rgba(0, 100, 200, 0.08);
}
:deep(.panel::before), :deep(.panel::after) {
  content: ''; position: absolute; width: 14px; height: 14px;
  border-color: $cyan; border-style: solid; border-width: 0;
}
:deep(.panel::before) { top: -1px; left: -1px; border-top-width: 2px; border-left-width: 2px; border-top-left-radius: 10px; }
:deep(.panel::after) { bottom: -1px; right: -1px; border-bottom-width: 2px; border-right-width: 2px; border-bottom-right-radius: 10px; }
:deep(.panel-head) {
  flex-shrink: 0; display: flex; align-items: center; gap: 10px;
  padding: 11px 14px 9px;
}
:deep(.panel-deco) {
  width: 4px; height: 15px; border-radius: 2px;
  background: linear-gradient(180deg, $cyan, #2f9bff);
  box-shadow: 0 0 8px rgba(0, 229, 255, 0.6);
}
:deep(.panel-title) { font-size: 16px; font-weight: 700; color: #eaf5ff; letter-spacing: 1px; }
:deep(.panel-sub) { font-size: 11px; color: #5d86bd; letter-spacing: 1px; margin-left: auto; }
:deep(.panel-body) { flex: 1; min-height: 0; padding: 6px 12px 12px; position: relative; }

/* 左栏 - 核心指标 */
.metric-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; height: 100%; }
.metric-cell {
  display: flex; flex-direction: column; justify-content: center;
  padding: 8px 14px; border-radius: 8px;
  background: rgba(0, 130, 255, 0.08);
  border: 1px solid rgba(0, 229, 255, 0.12);
}
.metric-val { font-size: 26px; font-weight: 800; color: #fff; font-variant-numeric: tabular-nums; line-height: 1.1; }
.metric-val em { font-size: 13px; font-weight: 500; color: #8fb3e6; margin-left: 4px; font-style: normal; }
.metric-label { font-size: 13px; color: #a9c8ee; margin-top: 3px; }
.metric-trend { font-size: 12px; margin-top: 2px; color: #ff6b9d; &.up { color: #26de81; } }

/* 中栏 - 大号主指标 */
.spotlight-row { flex-shrink: 0; display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
.spot-card {
  position: relative; overflow: hidden;
  padding: 16px 18px; border-radius: 10px;
  background: linear-gradient(135deg, rgba(0, 130, 255, 0.18), rgba(124, 92, 255, 0.1));
  border: 1px solid rgba(0, 229, 255, 0.22);
}
.spot-ring {
  position: absolute; right: -28px; top: -28px; width: 90px; height: 90px; border-radius: 50%;
  border: 6px solid rgba(0, 229, 255, 0.18);
}
.spot-val { font-size: 34px; font-weight: 800; color: #fff; line-height: 1; font-variant-numeric: tabular-nums; }
.spot-val em { font-size: 15px; font-weight: 500; color: #9fc2f0; margin-left: 4px; font-style: normal; }
.spot-label { font-size: 14px; color: #cfe3ff; margin-top: 8px; }
.spot-sub { font-size: 12px; color: #26de81; margin-top: 3px; }

/* 右栏 - 上线状态 */
.release-list { display: flex; flex-direction: column; justify-content: space-around; height: 100%; gap: 6px; }
.release-item { padding: 2px 0; }
.release-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.rname { font-size: 13px; color: #dceaff; }
.rstage { font-size: 12px; font-weight: 600; }
.release-bar { height: 8px; border-radius: 5px; background: rgba(0, 130, 255, 0.15); overflow: hidden; }
.release-fill { height: 100%; border-radius: 5px; transition: width 0.8s ease; box-shadow: 0 0 8px currentColor; }

/* 右栏 - 滚动日志 */
.log-view { height: 100%; overflow: hidden; position: relative; mask-image: linear-gradient(180deg, transparent, #000 8%, #000 92%, transparent); }
.log-track.run { animation: logscroll 26s linear infinite; }
.log-view:hover .log-track { animation-play-state: paused; }
@keyframes logscroll { 0% { transform: translateY(0); } 100% { transform: translateY(-50%); } }
.log-row {
  display: flex; align-items: center; gap: 8px; padding: 7px 4px;
  border-bottom: 1px solid rgba(127, 168, 216, 0.1); font-size: 12px;
}
.log-time { color: #6fa8e0; font-variant-numeric: tabular-nums; flex-shrink: 0; }
.log-tag {
  flex-shrink: 0; padding: 1px 7px; border-radius: 4px; font-size: 11px;
  background: rgba(0, 130, 255, 0.18); color: #6fd3ff;
  &.success { background: rgba(38, 222, 129, 0.18); color: #4ade80; }
  &.warn { background: rgba(250, 173, 20, 0.18); color: #fbbf24; }
  &.danger { background: rgba(255, 77, 109, 0.18); color: #ff6b9d; }
}
.log-actor { flex-shrink: 0; color: #a9c8ee; }
.log-text { color: #cbdcf5; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* 底部任务表 */
.screen-foot { position: relative; z-index: 2; flex-shrink: 0; height: 200px; margin-top: 14px; }
.screen-foot .panel { height: 100%; }
.task-table { height: 100%; display: flex; flex-direction: column; font-size: 13px; }
.t-head, .t-row {
  display: grid;
  grid-template-columns: 90px 1.6fr 1fr 90px 70px 1.3fr 90px 90px;
  align-items: center; gap: 8px;
}
.t-head { color: #6fa8e0; font-size: 12px; padding: 6px 10px; border-bottom: 1px solid rgba(0, 229, 255, 0.2); flex-shrink: 0; }
.t-body { flex: 1; overflow: hidden; }
.t-row {
  padding: 9px 10px; border-bottom: 1px solid rgba(127, 168, 216, 0.08);
  color: #d4e6ff; transition: background 0.2s;
  &:hover { background: rgba(0, 229, 255, 0.06); }
}
.c-name { color: #fff; font-weight: 600; }
.mono { font-variant-numeric: tabular-nums; color: #a9c8ee; }
.c-prog { display: flex; align-items: center; gap: 8px; }
.mini-bar { flex: 1; height: 6px; border-radius: 3px; background: rgba(0, 130, 255, 0.18); overflow: hidden; }
.mini-bar i { display: block; height: 100%; border-radius: 3px; transition: width 0.6s; }
.c-prog em { font-style: normal; font-size: 12px; color: #a9c8ee; min-width: 34px; }
.status { display: flex; align-items: center; gap: 6px; font-weight: 600; }
.s-dot { width: 7px; height: 7px; border-radius: 50%; box-shadow: 0 0 6px currentColor; }

@media (max-width: 1500px) {
  .title-main { font-size: 24px; }
  .spot-val { font-size: 28px; }
  .metric-val { font-size: 22px; }
}
</style>
