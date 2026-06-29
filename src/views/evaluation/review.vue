<template>
  <div>
    <PageHeader title="人工复核评估" description="办案人员与标注人员对模型输出进行抽样复核，计算人工复核准确率，作为模型上线的最终依据" />

    <el-row :gutter="16" class="mb-16" v-if="summary">
      <el-col :xs="12" :md="6"><StatCard label="抽样总数" :value="summary.total" icon="Files" bg="#2f54eb" /></el-col>
      <el-col :xs="12" :md="6"><StatCard label="已复核" :value="summary.reviewed" icon="View" bg="#13c2c2" /></el-col>
      <el-col :xs="12" :md="6"><StatCard label="复核准确率" :value="summary.accuracy" unit="%" icon="CircleCheck" bg="#52c41a" /></el-col>
      <el-col :xs="12" :md="6"><StatCard label="待复核" :value="summary.pending" icon="Clock" bg="#fa8c16" /></el-col>
    </el-row>

    <el-card shadow="never">
      <template #header>
        <div class="flex-between">
          <span>复核样本</span>
          <el-button type="primary" size="small" :icon="Plus" @click="sampleDialog = true">抽样复核任务</el-button>
        </div>
      </template>
      <el-table v-loading="loading" :data="list" border>
        <el-table-column type="index" label="#" width="50" />
        <el-table-column prop="content" label="样本内容" min-width="280" show-overflow-tooltip />
        <el-table-column prop="modelOutput" label="模型输出" min-width="240" show-overflow-tooltip />
        <el-table-column prop="reviewer" label="复核人" width="120" />
        <el-table-column label="复核结果" width="160">
          <template #default="{ row }">
            <el-radio-group v-model="row.result" size="small">
              <el-radio-button value="正确">正确</el-radio-button>
              <el-radio-button value="错误">错误</el-radio-button>
            </el-radio-group>
          </template>
        </el-table-column>
      </el-table>
      <div class="flex-between mt-16">
        <el-pagination background layout="total, sizes, prev, pager, next" :page-sizes="[10, 20, 50, 100]" :total="total" v-model:current-page="query.page" v-model:page-size="query.pageSize" @change="load" />
        <el-button type="success" @click="submit">提交复核结果</el-button>
      </div>
    </el-card>

    <!-- 抽样复核任务：真模型对测试集预测，入复核队列 -->
    <el-dialog v-model="sampleDialog" title="抽样复核任务" width="520px">
      <el-form label-width="100px">
        <el-form-item label="模型">
          <el-select v-model="runModel" filterable placeholder="选择模型" style="width: 100%">
            <el-option v-for="m in models" :key="m.id" :label="m.label" :value="m.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="测试集">
          <el-select v-model="runDataset" filterable placeholder="选择已发布数据集" style="width: 100%">
            <el-option v-for="d in datasets" :key="d.id" :label="d.name + '（' + d.type + '）'" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="抽样数量">
          <el-input-number v-model="runCount" :min="1" :max="100" :step="5" controls-position="right" />
        </el-form-item>
        <el-form-item label="复核人">
          <el-input v-model="reviewer" placeholder="（可选）默认当前用户" />
        </el-form-item>
        <el-progress v-if="running" :percentage="progPct" :stroke-width="10" striped striped-flow />
      </el-form>
      <template #footer>
        <el-button @click="sampleDialog = false" :disabled="running">关闭</el-button>
        <el-button type="primary" :loading="running" :disabled="!canRun" @click="startSampling">
          {{ running ? `抽样中 ${prog.done}/${prog.total || '—'}` : '开始抽样' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onActivated, onDeactivated } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'
import StatCard from '@/components/StatCard.vue'
import {
  getReviewSamples, getReviewSummary, submitReviewResults,
  runReviewSampling, getReviewRun
} from '@/api/modules/evaluation'
import { getInferModels } from '@/api/modules/inference'
import { getDatasetList } from '@/api/modules/dataset'

const loading = ref(false)
const list = ref([])
const total = ref(0)
const summary = ref(null)
const query = reactive({ page: 1, pageSize: 10 })

const sampleDialog = ref(false)
const models = ref([])
const datasets = ref([])
const runModel = ref('')
const runDataset = ref('')
const runCount = ref(10)
const reviewer = ref('')
const running = ref(false)
const prog = reactive({ done: 0, total: 0 })
let pollTimer = null

const canRun = computed(() => runModel.value && runDataset.value && !running.value)
const progPct = computed(() => (prog.total ? Math.round((prog.done / prog.total) * 100) : 0))

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

async function startSampling() {
  if (!canRun.value) return
  running.value = true
  prog.done = 0
  prog.total = 0
  try {
    const { reviewRunId } = await runReviewSampling({
      modelId: runModel.value, datasetId: runDataset.value,
      count: runCount.value, reviewer: reviewer.value || undefined
    })
    pollTimer = setInterval(() => poll(reviewRunId), 2000)
  } catch {
    running.value = false
  }
}

async function poll(eid) {
  let st
  try { st = await getReviewRun(eid) } catch { return }
  prog.done = st.done
  prog.total = st.total
  if (st.status === '已完成') {
    stopPoll()
    sampleDialog.value = false
    ElMessage.success(`已抽样 ${st.done} 条进入复核队列`)
    summary.value = await getReviewSummary()
    query.page = 1
    await load()
  } else if (st.status === '失败') {
    stopPoll()
    ElMessage.error(`抽样失败：${st.error || '未知错误'}`)
  }
}

function stopPoll() {
  running.value = false
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

async function load() {
  loading.value = true
  const res = await getReviewSamples(query)
  list.value = res.list
  total.value = res.total
  loading.value = false
}
async function submit() {
  // 仅提交当前页已给出「正确/错误」结论的样本
  const results = list.value
    .filter((r) => r.result === '正确' || r.result === '错误')
    .map((r) => ({ id: r.id, result: r.result }))
  if (!results.length) {
    ElMessage.warning('请先对样本标注复核结果')
    return
  }
  await submitReviewResults(results)
  ElMessage.success('复核结果已提交，准确率已更新')
  summary.value = await getReviewSummary()
  await load()
}
onActivated(async () => {
  summary.value = await getReviewSummary()
  await load()
  await loadOptions()
})
onDeactivated(stopPoll)
</script>
