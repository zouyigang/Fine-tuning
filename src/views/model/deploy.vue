<template>
  <div>
    <PageHeader title="模型导出与部署" description="支持导出 ONNX、PMML、TorchScript 等多种格式，提供一键部署至本地服务器、昇腾 NPU 集群、云环境的功能" />

    <el-row :gutter="16">
      <el-col :md="10">
        <el-card shadow="never">
          <template #header>模型导出</template>
          <el-form label-width="100px">
            <el-form-item label="选择模型">
              <el-select v-model="model" placeholder="请选择" style="width: 100%" filterable>
                <el-option v-for="m in models" :key="m.id" :label="`${m.name} ${m.version}`" :value="m.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="导出格式">
              <el-select v-model="format" style="width: 100%">
                <el-option v-for="f in EXPORT_FORMATS" :key="f" :label="f" :value="f" />
              </el-select>
            </el-form-item>
            <el-form-item label="量化">
              <el-radio-group v-model="quant"><el-radio value="none">不量化</el-radio><el-radio value="int8">INT8</el-radio><el-radio value="fp16">FP16</el-radio></el-radio-group>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :icon="Download" :loading="exporting" @click="exportModel">导出模型</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <el-col :md="14">
        <el-card shadow="never">
          <template #header>部署目标环境</template>
          <el-table :data="pagedTargets" border>
            <el-table-column prop="name" label="部署环境" min-width="160" />
            <el-table-column prop="type" label="类型" width="90">
              <template #default="{ row }"><el-tag size="small" effect="plain">{{ row.type }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="spec" label="算力规格" width="130" />
            <el-table-column label="状态" width="90">
              <template #default="{ row }"><el-tag :type="row.status === '在线' ? 'success' : 'info'" size="small">{{ row.status }}</el-tag></template>
            </el-table-column>
            <el-table-column label="负载" width="140">
              <template #default="{ row }"><el-progress :percentage="row.load" :stroke-width="8" /></template>
            </el-table-column>
            <el-table-column label="操作" width="100" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" size="small" :disabled="row.status !== '在线'" @click="deploy(row)">部署</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination class="mt-16" background layout="total, sizes, prev, pager, next" :page-sizes="[10, 20, 50, 100]" :total="targets.length" v-model:current-page="page" v-model:page-size="pageSize" />
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" class="mt-16" v-if="deployLogs.length">
      <template #header>部署日志</template>
      <div class="deploy-log">
        <div v-for="(l, i) in deployLogs" :key="i">{{ l }}</div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onActivated } from 'vue'
import { Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'
import { getDeployTargets, getModelList, exportModel as apiExport, downloadExport, deployModel, EXPORT_FORMATS } from '@/api/modules/model'

const model = ref(null)
const format = ref('ONNX')
const quant = ref('none')
const exporting = ref(false)
const deploying = ref(false)
const targets = ref([])
const models = ref([])
const deployLogs = ref([])

// 前端分页（本地数据），与各列表页分页控件保持统一，默认每页 10 条
const page = ref(1)
const pageSize = ref(10)
const pagedTargets = computed(() => targets.value.slice((page.value - 1) * pageSize.value, page.value * pageSize.value))

async function exportModel() {
  if (!model.value) {
    ElMessage.warning('请先选择要导出的模型')
    return
  }
  exporting.value = true
  try {
    // 后端生成产物并落库，随即下载该产物文件
    const rec = await apiExport(model.value, { format: format.value, quant: quant.value })
    await downloadExport(rec.id)
    ElMessage.success(`已导出 ${format.value} 格式模型文件`)
  } finally {
    exporting.value = false
  }
}
async function deploy(row) {
  if (!model.value) {
    ElMessage.warning('请先选择要部署的模型')
    return
  }
  deploying.value = true
  try {
    const res = await deployModel(model.value, { targetId: row.id, format: format.value })
    deployLogs.value = res.logs || []
    ElMessage.success(`已部署至 ${row.name}`)
    targets.value = await getDeployTargets() // 刷新负载
  } finally {
    deploying.value = false
  }
}
onActivated(async () => {
  targets.value = await getDeployTargets()
  const res = await getModelList({ pageSize: 100 })
  models.value = res.list || []
  if (models.value.length) model.value = models.value[0].id
})
</script>

<style lang="scss" scoped>
.deploy-log {
  background: #1e1e1e;
  color: #9cdcfe;
  padding: 14px;
  border-radius: 4px;
  font-family: Consolas, monospace;
  font-size: 12.5px;
  line-height: 1.9;
}
</style>
