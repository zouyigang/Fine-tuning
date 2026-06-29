<template>
  <div>
    <PageHeader title="真实业务场景验证" description="选择一个模型，在多个已发布业务测试集上各跑一遍评估，按场景统计识别准确率与疑难样本表现" />

    <el-card shadow="never" class="mb-16">
      <el-form :inline="true">
        <el-form-item label="模型">
          <el-select v-model="runModel" filterable placeholder="选择模型" style="width: 220px">
            <el-option v-for="m in models" :key="m.id" :label="m.label" :value="m.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="业务测试集">
          <el-select v-model="runDatasets" multiple collapse-tags filterable placeholder="选择一个或多个已发布数据集" style="width: 300px">
            <el-option v-for="d in datasets" :key="d.id" :label="d.name + '（' + d.type + '）'" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="每场景上限">
          <el-input-number v-model="runLimit" :min="1" :max="300" :step="10" controls-position="right" style="width: 110px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Aim" :loading="running" :disabled="!canRun" @click="startScene">
            {{ running ? `验证中 ${prog.done}/${prog.total || '—'}` : '开始验证' }}
          </el-button>
        </el-form-item>
      </el-form>
      <el-progress v-if="running" :percentage="progPct" :stroke-width="10" striped striped-flow class="mt-8" />
      <div v-if="!models.length || !datasets.length" class="hint">提示：需先有「带真实产物的微调版本」与「已发布测试集」。</div>
    </el-card>

    <el-row :gutter="16" class="mb-16" v-if="data.summary">
      <el-col :xs="12" :md="5"><StatCard label="测试样本" :value="data.summary.total" icon="Files" bg="#2f54eb" /></el-col>
      <el-col :xs="12" :md="5"><StatCard label="识别正确" :value="data.summary.correct" icon="CircleCheck" bg="#52c41a" /></el-col>
      <el-col :xs="12" :md="5"><StatCard label="整体准确率" :value="data.summary.accuracy" unit="%" icon="DataLine" bg="#13c2c2" /></el-col>
      <el-col :xs="12" :md="4"><StatCard label="疑难样本" :value="data.summary.hardCase" icon="WarnTriangleFilled" bg="#fa8c16" /></el-col>
      <el-col :xs="12" :md="5"><StatCard label="疑难样本准确率" :value="data.summary.hardAccuracy" unit="%" icon="Aim" bg="#722ed1" /></el-col>
    </el-row>

    <el-card shadow="never">
      <template #header>按案件类型验证结果</template>
      <el-table :data="pagedCases" border>
        <el-table-column prop="caseNo" label="案件编号" min-width="180" />
        <el-table-column prop="type" label="案件类型" width="120">
          <template #default="{ row }"><el-tag size="small">{{ row.type }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="sampleCount" label="样本数" width="100" />
        <el-table-column label="识别准确率" width="220">
          <template #default="{ row }">
            <el-progress :percentage="Number(row.accuracy)" :status="row.accuracy < 88 ? 'warning' : 'success'" />
          </template>
        </el-table-column>
        <el-table-column label="是否疑难" width="100">
          <template #default="{ row }"><el-tag v-if="row.hard" type="warning" size="small">疑难</el-tag><span v-else class="text-muted">常规</span></template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default><el-button link type="primary" size="small">查看明细</el-button></template>
        </el-table-column>
      </el-table>
      <el-pagination class="mt-16" background layout="total, sizes, prev, pager, next" :page-sizes="[10, 20, 50, 100]" :total="data.cases.length" v-model:current-page="page" v-model:page-size="pageSize" />
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref, computed, onActivated, onDeactivated } from 'vue'
import { Aim } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'
import StatCard from '@/components/StatCard.vue'
import { getSceneValidation, runSceneValidation, getSceneRun } from '@/api/modules/evaluation'
import { getInferModels } from '@/api/modules/inference'
import { getDatasetList } from '@/api/modules/dataset'

const data = reactive({ summary: null, cases: [] })

// 前端分页（本地数据），与各列表页分页控件保持统一，默认每页 10 条
const page = ref(1)
const pageSize = ref(10)
const pagedCases = computed(() => data.cases.slice((page.value - 1) * pageSize.value, page.value * pageSize.value))

const models = ref([])
const datasets = ref([])
const runModel = ref('')
const runDatasets = ref([])
const runLimit = ref(50)
const running = ref(false)
const prog = reactive({ done: 0, total: 0 })
let pollTimer = null

const canRun = computed(() => runModel.value && runDatasets.value.length && !running.value)
const progPct = computed(() => (prog.total ? Math.round((prog.done / prog.total) * 100) : 0))

async function loadScene() {
  Object.assign(data, await getSceneValidation())
}

async function loadOptions() {
  try {
    models.value = (await getInferModels()).filter((m) => m.kind === 'finetuned')
    if (!models.value.length) models.value = await getInferModels()
    const res = await getDatasetList({ page: 1, pageSize: 100 })
    datasets.value = (res.list || []).filter((d) => d.stage === '已发布')
    if (!runModel.value && models.value.length) runModel.value = models.value[0].id
    if (!runDatasets.value.length && datasets.value.length) runDatasets.value = [datasets.value[0].id]
  } catch { /* ignore */ }
}

async function startScene() {
  if (!canRun.value) return
  running.value = true
  prog.done = 0
  prog.total = 0
  try {
    const { sceneRunId } = await runSceneValidation({
      modelId: runModel.value, datasetIds: runDatasets.value, limit: runLimit.value
    })
    pollTimer = setInterval(() => poll(sceneRunId), 2000)
  } catch {
    running.value = false
  }
}

async function poll(eid) {
  let st
  try { st = await getSceneRun(eid) } catch { return }
  prog.done = st.done
  prog.total = st.total
  if (st.status === '已完成') {
    stopPoll()
    page.value = 1
    await loadScene()
    ElMessage.success('场景验证完成')
  } else if (st.status === '失败') {
    stopPoll()
    ElMessage.error(`场景验证失败：${st.error || '未知错误'}`)
  }
}

function stopPoll() {
  running.value = false
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

onActivated(async () => {
  await loadScene()
  await loadOptions()
})
onDeactivated(stopPoll)
</script>

<style lang="scss" scoped>
.text-muted { color: #909399; }
.mt-8 { margin-top: 8px; }
.hint { margin-top: 10px; font-size: 12px; color: #e6a23c; }
</style>
