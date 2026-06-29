<template>
  <div>
    <PageHeader title="基准模型对比" description="选择某个微调版本，与其基座模型在同一已发布测试集上各跑一遍评估，多维度对比并高亮微调带来的提升/下降" />

    <el-card shadow="never" class="mb-16">
      <el-form :inline="true">
        <el-form-item label="基座模型">
          <el-select v-model="runBase" filterable placeholder="选择基座模型" style="width: 220px">
            <el-option v-for="b in baseOptions" :key="b" :label="b" :value="b" />
          </el-select>
        </el-form-item>
        <el-form-item label="微调版本">
          <el-select v-model="runModel" filterable placeholder="选择微调版本" style="width: 240px" :disabled="!runBase">
            <el-option v-for="m in filteredModels" :key="m.id" :label="m.label" :value="m.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="测试集">
          <el-select v-model="runDataset" filterable placeholder="选择已发布数据集" style="width: 220px">
            <el-option v-for="d in datasets" :key="d.id" :label="d.name + '（' + d.type + '）'" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="样本上限">
          <el-input-number v-model="runLimit" :min="1" :max="300" :step="10" controls-position="right" style="width: 110px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Histogram" :loading="running" :disabled="!canRun" @click="startBench">
            {{ running ? `对比中 ${prog.done}/${prog.total || '—'}` : '开始对比' }}
          </el-button>
        </el-form-item>
      </el-form>
      <el-progress v-if="running" :percentage="progPct" :stroke-width="10" striped striped-flow class="mt-8" />
      <div v-if="!models.length || !datasets.length" class="hint">提示：需先有「带真实产物的微调版本」与「已发布测试集」。</div>
    </el-card>

    <el-row :gutter="16">
      <el-col :md="12">
        <el-card shadow="never" class="mb-16">
          <template #header>多维度雷达对比</template>
          <BaseChart :option="radarOption" height="360px" />
        </el-card>
      </el-col>
      <el-col :md="12">
        <el-card shadow="never" class="mb-16">
          <template #header>指标柱状对比</template>
          <BaseChart :option="barOption" height="360px" />
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never">
      <template #header>对比明细（微调模型 vs 基座模型）</template>
      <el-table :data="data.compare" border>
        <el-table-column prop="dim" label="评估维度" />
        <el-table-column prop="prod" label="基座模型" />
        <el-table-column prop="current" label="微调模型" />
        <el-table-column label="差值" width="160">
          <template #default="{ row }">
            <el-tag :type="row.diff >= 0 ? 'success' : 'danger'" effect="light">
              <el-icon><component :is="row.diff >= 0 ? 'Top' : 'Bottom'" /></el-icon>
              {{ row.diff >= 0 ? '+' : '' }}{{ row.diff }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="结论" width="120">
          <template #default="{ row }">
            <span :class="row.diff >= 0 ? 'text-up' : 'text-down'">{{ row.diff >= 0 ? '提升' : '下降' }}</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onActivated, onDeactivated } from 'vue'
import { Histogram } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'
import BaseChart from '@/components/BaseChart.vue'
import { getBenchmark, runBenchmark, getBenchmarkRun } from '@/api/modules/evaluation'
import { getInferModels } from '@/api/modules/inference'
import { getDatasetList } from '@/api/modules/dataset'

const data = reactive({ dims: [], models: [], compare: [] })

const models = ref([])
const datasets = ref([])
const runBase = ref('')
const runModel = ref('')
const runDataset = ref('')
const runLimit = ref(50)
const running = ref(false)
const prog = reactive({ done: 0, total: 0 })
let pollTimer = null

// 基座 → 微调版本 二级联动：基座选项取自各微调版本的血缘基座（去重）
const baseOptions = computed(() => [...new Set(models.value.map((m) => m.base).filter(Boolean))])
const filteredModels = computed(() => models.value.filter((m) => m.base === runBase.value))
const canRun = computed(() => runBase.value && runModel.value && runDataset.value && !running.value)

// 切换基座后，若当前微调版本不属于该基座则重置为该基座下第一项
watch(runBase, () => {
  if (!filteredModels.value.some((m) => m.id === runModel.value)) {
    runModel.value = filteredModels.value[0]?.id || ''
  }
})
const progPct = computed(() => (prog.total ? Math.round((prog.done / prog.total) * 100) : 0))

async function loadBenchmark() {
  Object.assign(data, await getBenchmark())
}

async function loadOptions() {
  try {
    models.value = (await getInferModels()).filter((m) => m.kind === 'finetuned' && m.base)
    const res = await getDatasetList({ page: 1, pageSize: 100 })
    datasets.value = (res.list || []).filter((d) => d.stage === '已发布')
    if (!runBase.value && baseOptions.value.length) runBase.value = baseOptions.value[0]
    if (!runModel.value && filteredModels.value.length) runModel.value = filteredModels.value[0].id
    if (!runDataset.value && datasets.value.length) runDataset.value = datasets.value[0].id
  } catch { /* ignore */ }
}

async function startBench() {
  if (!canRun.value) return
  running.value = true
  prog.done = 0
  prog.total = 0
  try {
    const { benchRunId } = await runBenchmark({
      modelId: runModel.value, datasetId: runDataset.value, limit: runLimit.value
    })
    pollTimer = setInterval(() => poll(benchRunId), 2000)
  } catch {
    running.value = false
  }
}

async function poll(eid) {
  let st
  try { st = await getBenchmarkRun(eid) } catch { return }
  prog.done = st.done
  prog.total = st.total
  if (st.status === '已完成') {
    stopPoll()
    await loadBenchmark()
    ElMessage.success('基准对比完成')
  } else if (st.status === '失败') {
    stopPoll()
    ElMessage.error(`对比失败：${st.error || '未知错误'}`)
  }
}

function stopPoll() {
  running.value = false
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

onActivated(async () => {
  await loadBenchmark()
  await loadOptions()
})
onDeactivated(stopPoll)

// 图例/系列顺序：基座模型在左、微调模型在右（历史最优若有则置后）
const MODEL_RANK = { 基座模型: 0, 微调模型: 1 }
const orderedModels = computed(() =>
  [...data.models].sort((a, b) => (MODEL_RANK[a.name] ?? 9) - (MODEL_RANK[b.name] ?? 9))
)

const radarOption = computed(() => ({
  tooltip: {},
  legend: { data: orderedModels.value.map((m) => m.name), bottom: 0 },
  color: ['#fa8c16', '#2f54eb', '#52c41a'],
  radar: { indicator: data.dims.map((d) => ({ name: d, max: 100 })), radius: '65%' },
  series: [
    {
      type: 'radar',
      data: orderedModels.value.map((m) => ({ name: m.name, value: m.values, areaStyle: { opacity: 0.1 } }))
    }
  ]
}))

const barOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: orderedModels.value.map((m) => m.name), bottom: 0 },
  grid: { left: 40, right: 20, top: 20, bottom: 50 },
  xAxis: { type: 'category', data: data.dims },
  yAxis: { type: 'value', min: 0, max: 100 },
  color: ['#fa8c16', '#2f54eb', '#52c41a'],
  series: orderedModels.value.map((m) => ({ name: m.name, type: 'bar', data: m.values }))
}))
</script>

<style lang="scss" scoped>
.text-up { color: #52c41a; font-weight: 600; }
.text-down { color: #f5222d; font-weight: 600; }
.mt-8 { margin-top: 8px; }
.hint { margin-top: 10px; font-size: 12px; color: #e6a23c; }
</style>
