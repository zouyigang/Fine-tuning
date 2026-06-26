<template>
  <div>
    <PageHeader title="评估报告生成" description="自动生成标准化模型评估报告，包含训练参数、指标对比、业务验证、错误案例分析，支持导出 PDF/Excel 用于审批存档">
      <template #extra><el-button type="primary" :icon="Plus" @click="genDialog = true">生成报告</el-button></template>
    </PageHeader>

    <el-card shadow="never">
      <el-table v-loading="loading" :data="list" border>
        <el-table-column prop="name" label="报告名称" min-width="240" show-overflow-tooltip />
        <el-table-column prop="model" label="模型版本" width="130" />
        <el-table-column prop="f1" label="F1" width="90" />
        <el-table-column label="评估结论" width="150">
          <template #default="{ row }">
            <el-tag :type="row.conclusion === '建议上线' ? 'success' : row.conclusion === '不建议上线' ? 'danger' : 'warning'" size="small">{{ row.conclusion }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }"><el-tag size="small" effect="plain">{{ row.status }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="creator" label="生成人" width="90" />
        <el-table-column prop="createdAt" label="生成时间" width="120" />
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="preview(row)">预览</el-button>
            <el-button link type="primary" size="small" @click="doExport(row, 'pdf')">导出 PDF</el-button>
            <el-button link type="primary" size="small" @click="doExport(row, 'excel')">导出 Excel</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination class="mt-16" background layout="total, sizes, prev, pager, next" :page-sizes="[10, 20, 50, 100]" :total="total" v-model:current-page="query.page" v-model:page-size="query.pageSize" @change="load" />
    </el-card>

    <!-- 生成报告对话框 -->
    <el-dialog v-model="genDialog" title="生成评估报告" width="560px">
      <el-form label-width="110px">
        <el-form-item label="选择模型">
          <el-select v-model="genModel" placeholder="请选择" style="width: 100%" filterable>
            <el-option v-for="m in models" :key="m.id" :label="`${m.name} ${m.version}`" :value="`${m.name} ${m.version}`" />
          </el-select>
        </el-form-item>
        <el-form-item label="报告内容">
          <el-checkbox-group v-model="sections">
            <el-checkbox value="params">训练参数</el-checkbox>
            <el-checkbox value="metrics">指标对比</el-checkbox>
            <el-checkbox value="scene">业务验证</el-checkbox>
            <el-checkbox value="errors">错误案例分析</el-checkbox>
            <el-checkbox value="review">人工复核结果</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="导出格式">
          <el-radio-group v-model="format"><el-radio value="pdf">PDF</el-radio><el-radio value="excel">Excel</el-radio><el-radio value="both">两者</el-radio></el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer><el-button @click="genDialog = false">取消</el-button><el-button type="primary" :loading="gen" @click="generate">生成</el-button></template>
    </el-dialog>

    <!-- 报告预览 -->
    <el-drawer v-model="previewDrawer" :title="current?.name" size="60%">
      <div class="report-doc">
        <h2>{{ current?.name }}</h2>
        <p class="text-muted">生成人：{{ current?.creator }} · 生成时间：{{ current?.createdAt }}</p>
        <el-divider content-position="left">一、模型概况</el-divider>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="模型版本">{{ current?.model }}</el-descriptions-item>
          <el-descriptions-item label="基础模型">Qwen2-7B</el-descriptions-item>
          <el-descriptions-item label="训练数据集">审讯笔录数据集 v1.3（48,200 条）</el-descriptions-item>
          <el-descriptions-item label="微调方式">LoRA</el-descriptions-item>
        </el-descriptions>
        <el-divider content-position="left">二、核心指标</el-divider>
        <el-descriptions :column="3" border>
          <el-descriptions-item label="精确率">94.8%</el-descriptions-item>
          <el-descriptions-item label="召回率">92.3%</el-descriptions-item>
          <el-descriptions-item label="F1">{{ current?.f1 }}</el-descriptions-item>
        </el-descriptions>
        <el-divider content-position="left">三、评估结论</el-divider>
        <el-alert :title="current?.conclusion" :type="current?.conclusion === '建议上线' ? 'success' : 'warning'" :closable="false" show-icon />
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, onActivated } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'
import { getReportList, generateReport, exportReport } from '@/api/modules/evaluation'
import { getModelList } from '@/api/modules/model'

const loading = ref(false)
const list = ref([])
const total = ref(0)
const query = reactive({ page: 1, pageSize: 10 })

const genDialog = ref(false)
const gen = ref(false)
const sections = ref(['params', 'metrics', 'scene', 'errors'])
const format = ref('pdf')
const genModel = ref('')
const models = ref([])

const previewDrawer = ref(false)
const current = ref(null)

async function load() {
  loading.value = true
  const res = await getReportList(query)
  list.value = res.list
  total.value = res.total
  loading.value = false
}
async function generate() {
  if (!genModel.value) {
    ElMessage.warning('请选择要评估的模型')
    return
  }
  gen.value = true
  try {
    await generateReport({ model: genModel.value, sections: sections.value, format: format.value })
    genDialog.value = false
    genModel.value = ''
    ElMessage.success('报告已生成')
    await load()
  } finally {
    gen.value = false
  }
}
function preview(row) {
  current.value = row
  previewDrawer.value = true
}
async function doExport(row, format) {
  await exportReport(row.id, format)
  ElMessage.success(`已导出 ${format === 'excel' ? 'Excel' : 'PDF'} 报告`)
}
onActivated(async () => {
  await load()
  const res = await getModelList({ pageSize: 100 })
  models.value = res.list || []
})
</script>

<style lang="scss" scoped>
.report-doc {
  padding: 0 12px;
  h2 { text-align: center; margin-bottom: 6px; }
  .text-muted { text-align: center; font-size: 12px; margin-bottom: 20px; }
}
</style>
