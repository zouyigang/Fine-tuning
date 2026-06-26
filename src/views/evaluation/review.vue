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
        <div class="flex-between"><span>复核样本</span><el-button type="primary" size="small">分配复核任务</el-button></div>
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
  </div>
</template>

<script setup>
import { ref, reactive, onActivated } from 'vue'
import { ElMessage } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'
import StatCard from '@/components/StatCard.vue'
import { getReviewSamples, getReviewSummary, submitReviewResults } from '@/api/modules/evaluation'

const loading = ref(false)
const list = ref([])
const total = ref(0)
const summary = ref(null)
const query = reactive({ page: 1, pageSize: 10 })

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
  load()
})
</script>
