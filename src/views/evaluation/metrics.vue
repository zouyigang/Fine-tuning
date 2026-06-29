<template>
  <div>
    <PageHeader title="自动化指标评估" description="选择某个微调版本与已发布测试集，真实加载模型跑推理，自动计算 P/R/F1、完全匹配率与各类别细分指标" />

    <el-card shadow="never" class="mb-16">
      <el-form :inline="true" class="run-form">
        <el-form-item label="模型版本">
          <el-select v-model="runModel" filterable placeholder="选择模型" style="width: 240px">
            <el-option v-for="m in models" :key="m.id" :label="m.label" :value="m.id" />
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
          <el-button type="primary" :icon="DataAnalysis" :loading="running" :disabled="!canRun" @click="startEval">
            {{ running ? `评估中 ${prog.done}/${prog.total || '—'}` : '开始评估' }}
          </el-button>
        </el-form-item>
      </el-form>
      <el-progress v-if="running" :percentage="progPct" :stroke-width="10" striped striped-flow class="mt-8" />
      <div v-if="!models.length || !datasets.length" class="hint">
        提示：需先有「带真实产物的微调版本」与「已发布测试集」。无可选项时请先完成训练与数据集发布。
      </div>
    </el-card>

    <el-card shadow="never" class="mb-16">
      <div class="type-bar">
        <span class="type-label">当前模型类型：</span>
        <el-tag v-if="viewType" type="primary" effect="plain">{{ currentTypeLabel }}</el-tag>
        <span v-else class="src-tip">请先选择模型版本</span>
        <span class="src-tip">{{ srcTip }}</span>
      </div>
    </el-card>

    <el-row :gutter="16" class="mb-16" v-if="data.metrics.length">
      <el-col v-for="m in data.metrics" :key="m.name" :xs="12" :md="6">
        <div class="metric-card">
          <div class="metric-value">{{ m.value }}<span class="metric-unit">{{ m.unit }}</span></div>
          <div class="metric-name">{{ m.name }}</div>
        </div>
      </el-col>
    </el-row>
    <el-empty v-else description="该类型暂无评估指标，请先运行一次评估" />

    <el-card shadow="never" v-if="data.perClass.length">
      <template #header>各类别细分指标</template>
      <el-row :gutter="16">
        <el-col :md="14">
          <el-table :data="data.perClass" border>
            <el-table-column prop="label" label="类别" />
            <el-table-column prop="precision" label="精确率(%)" sortable />
            <el-table-column prop="recall" label="召回率(%)" sortable />
            <el-table-column prop="f1" label="F1(%)" sortable>
              <template #default="{ row }">
                <span :class="{ 'low-score': row.f1 < 88 }">{{ row.f1 }}</span>
              </template>
            </el-table-column>
          </el-table>
        </el-col>
        <el-col :md="10"><BaseChart :option="chartOption" height="280px" /></el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onActivated, onDeactivated } from 'vue'
import { DataAnalysis } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'
import BaseChart from '@/components/BaseChart.vue'
import { getMetrics, runEvaluation, getEvaluationRun } from '@/api/modules/evaluation'
import { getInferModels } from '@/api/modules/inference'
import { getDatasetList, getDatasetTypes } from '@/api/modules/dataset'

const viewType = ref('ner')
const typeOptions = ref([])
const data = reactive({ metrics: [], perClass: [] })

const models = ref([])
const datasets = ref([])
const runModel = ref('')
const runDataset = ref('')
const runLimit = ref(50)
const running = ref(false)
const prog = reactive({ done: 0, total: 0 })
let pollTimer = null

const canRun = computed(() => runModel.value && runDataset.value && !running.value)
const progPct = computed(() => (prog.total ? Math.round((prog.done / prog.total) * 100) : 0))
// 指标类型由所选模型版本决定，仅作回显；展示的是该类型最近一次评估结果
const currentTypeLabel = computed(() => {
  const t = typeOptions.value.find((x) => x.value === viewType.value)
  return t ? t.label : viewType.value
})
const srcTip = computed(() => (data.metrics.length ? '（展示该类型最近一次评估结果）' : ''))

// 选中模型版本即按其业务类型回显指标，无需手动选类型
watch(runModel, (id) => {
  const m = models.value.find((x) => x.id === id)
  if (m && m.modelType) {
    viewType.value = m.modelType
    load()
  }
})

async function load() {
  Object.assign(data, await getMetrics(viewType.value))
}

async function loadTypes() {
  try {
    const rows = await getDatasetTypes(true)
    typeOptions.value = (rows || []).filter((t) => t.value)
    // 当前选中类型不在动态列表里时，回退到第一项，避免下拉空显
    if (typeOptions.value.length && !typeOptions.value.some((t) => t.value === viewType.value)) {
      viewType.value = typeOptions.value[0].value
    }
  } catch { /* ignore */ }
}

async function loadOptions() {
  try {
    models.value = (await getInferModels()).filter((m) => m.kind === 'finetuned')
    if (!models.value.length) models.value = await getInferModels()
    const res = await getDatasetList({ page: 1, pageSize: 100 })
    datasets.value = (res.list || []).filter((d) => d.stage === '已发布')
    if (!runModel.value && models.value.length) runModel.value = models.value[0].id
    if (!runDataset.value && datasets.value.length) runDataset.value = datasets.value[0].id
  } catch { /* ignore */ }
}

async function startEval() {
  if (!canRun.value) return
  running.value = true
  prog.done = 0
  prog.total = 0
  try {
    const { evalTaskId, modelType } = await runEvaluation({
      modelId: runModel.value, datasetId: runDataset.value, limit: runLimit.value
    })
    if (modelType) viewType.value = modelType
    pollTimer = setInterval(() => poll(evalTaskId), 2000)
  } catch {
    running.value = false
  }
}

async function poll(eid) {
  let st
  try {
    st = await getEvaluationRun(eid)
  } catch {
    return
  }
  prog.done = st.done
  prog.total = st.total
  if (st.status === '已完成') {
    stopPoll()
    if (st.modelType) viewType.value = st.modelType
    await load()
    ElMessage.success(`评估完成：F1 ${(st.f1 * 100).toFixed(1)}% · 精确率 ${(st.precision * 100).toFixed(1)}% · 召回率 ${(st.recall * 100).toFixed(1)}%`)
  } else if (st.status === '失败') {
    stopPoll()
    ElMessage.error(`评估失败：${st.error || '未知错误'}`)
  }
}

function stopPoll() {
  running.value = false
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

onActivated(async () => {
  await loadTypes()
  await load()
  await loadOptions()
})
onDeactivated(stopPoll)

const chartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['精确率', '召回率', 'F1'] },
  grid: { left: 40, right: 20, top: 40, bottom: 30 },
  xAxis: { type: 'category', data: data.perClass.map((c) => c.label) },
  yAxis: { type: 'value', min: 0, max: 100 },
  color: ['#2f54eb', '#13c2c2', '#52c41a'],
  series: [
    { name: '精确率', type: 'bar', data: data.perClass.map((c) => c.precision) },
    { name: '召回率', type: 'bar', data: data.perClass.map((c) => c.recall) },
    { name: 'F1', type: 'bar', data: data.perClass.map((c) => c.f1) }
  ]
}))
</script>

<style lang="scss" scoped>
.metric-card {
  background: linear-gradient(135deg, #2f54eb, #5b7cfa);
  border-radius: 6px;
  padding: 22px;
  color: #fff;
  text-align: center;
  margin-bottom: 16px;
}
.metric-value {
  font-size: 30px;
  font-weight: 700;
  .metric-unit { font-size: 14px; margin-left: 2px; opacity: 0.85; }
}
.metric-name { margin-top: 6px; font-size: 13px; opacity: 0.9; }
.low-score { color: #f5222d; font-weight: 600; }
.run-form { margin-bottom: 0; }
.mt-8 { margin-top: 8px; }
.hint { margin-top: 10px; font-size: 12px; color: #e6a23c; }
.src-tip { font-size: 13px; color: #909399; }
.type-bar { display: flex; align-items: center; gap: 8px; }
.type-label { font-size: 14px; color: #606266; }
</style>
