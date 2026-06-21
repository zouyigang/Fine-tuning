<template>
  <div>
    <PageHeader title="训练任务实时监控" description="实时展示训练进度、损失/准确率曲线、GPU/CPU 资源占用，训练异常时自动告警">
      <template #extra>
        <el-tag type="success" effect="dark"><span class="live-dot" />实时监控中</el-tag>
      </template>
    </PageHeader>

    <el-card shadow="never" class="mb-16" v-if="task">
      <div class="task-head">
        <div>
          <span class="task-name">{{ task.name }}</span>
          <el-tag type="primary" size="small" class="ml-8">训练中</el-tag>
        </div>
        <div class="task-meta">
          <span>Epoch {{ task.epoch }}</span><el-divider direction="vertical" />
          <span>Step {{ task.step }}</span><el-divider direction="vertical" />
          <span>预计剩余 {{ task.eta }}</span>
        </div>
      </div>
      <el-progress :percentage="task.progress" :stroke-width="14" striped striped-flow class="mt-16" />
    </el-card>

    <el-row :gutter="16" v-if="task">
      <el-col :xs="12" :md="6"><StatCard label="当前 Loss" :value="task.curLoss" icon="Bottom" bg="#f5222d" class="mb-16" /></el-col>
      <el-col :xs="12" :md="6"><StatCard label="当前准确率" :value="task.curAcc" unit="%" icon="Top" bg="#52c41a" class="mb-16" /></el-col>
      <el-col :xs="12" :md="6"><StatCard label="GPU 利用率" :value="task.gpuUtil" unit="%" icon="Cpu" bg="#2f54eb" class="mb-16" /></el-col>
      <el-col :xs="12" :md="6"><StatCard label="显存占用" :value="task.gpuMem" unit="GB" icon="Coin" bg="#fa8c16" class="mb-16" /></el-col>
    </el-row>

    <el-row :gutter="16">
      <el-col :md="14">
        <el-card shadow="never" class="mb-16">
          <template #header>损失 / 准确率曲线</template>
          <BaseChart :option="curveOption" height="280px" />
        </el-card>
      </el-col>
      <el-col :md="10">
        <el-card shadow="never" class="mb-16">
          <template #header>资源占用（近 30s）</template>
          <BaseChart :option="resourceOption" height="280px" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onActivated, onDeactivated } from 'vue'
import PageHeader from '@/components/PageHeader.vue'
import StatCard from '@/components/StatCard.vue'
import BaseChart from '@/components/BaseChart.vue'
import { getRunningTask, getTrainingCurve, getResourceUsage } from '@/api/modules/task'

const task = ref(null)
const curve = reactive({ steps: [], loss: [], valLoss: [], acc: [] })
const resource = reactive({ points: [], gpu: [], cpu: [], mem: [] })
let timer = null

async function refresh() {
  task.value = await getRunningTask()
  Object.assign(resource, await getResourceUsage())
}

onActivated(async () => {
  task.value = await getRunningTask()
  Object.assign(curve, await getTrainingCurve())
  Object.assign(resource, await getResourceUsage())
  timer = setInterval(refresh, 2000)
})
onDeactivated(() => clearInterval(timer))

const curveOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['训练 Loss', '验证 Loss', '准确率'] },
  grid: { left: 45, right: 45, top: 40, bottom: 30 },
  xAxis: { type: 'category', data: curve.steps, name: 'step' },
  yAxis: [
    { type: 'value', name: 'Loss' },
    { type: 'value', name: 'Acc(%)', min: 50, max: 100 }
  ],
  color: ['#f5222d', '#fa8c16', '#52c41a'],
  series: [
    { name: '训练 Loss', type: 'line', smooth: true, data: curve.loss },
    { name: '验证 Loss', type: 'line', smooth: true, data: curve.valLoss },
    { name: '准确率', type: 'line', smooth: true, yAxisIndex: 1, data: curve.acc }
  ]
}))

const resourceOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['GPU', 'CPU', '显存'] },
  grid: { left: 40, right: 20, top: 40, bottom: 30 },
  xAxis: { type: 'category', boundaryGap: false, data: resource.points },
  yAxis: { type: 'value', max: 100, name: '%' },
  color: ['#2f54eb', '#13c2c2', '#fa8c16'],
  series: [
    { name: 'GPU', type: 'line', smooth: true, areaStyle: { opacity: 0.15 }, data: resource.gpu },
    { name: 'CPU', type: 'line', smooth: true, data: resource.cpu },
    { name: '显存', type: 'line', smooth: true, data: resource.mem }
  ]
}))
</script>

<style lang="scss" scoped>
.live-dot {
  display: inline-block;
  width: 7px;
  height: 7px;
  background: #fff;
  border-radius: 50%;
  margin-right: 5px;
  animation: blink 1.2s infinite;
}
@keyframes blink {
  50% { opacity: 0.3; }
}
.task-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.task-name { font-size: 16px; font-weight: 600; }
.ml-8 { margin-left: 8px; }
.task-meta { font-size: 13px; color: #8a919f; }
</style>
