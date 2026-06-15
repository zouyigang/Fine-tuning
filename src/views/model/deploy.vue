<template>
  <div>
    <PageHeader title="模型导出与部署" description="支持导出 ONNX、PMML、TorchScript 等多种格式，提供一键部署至本地服务器、昇腾 NPU 集群、云环境的功能" />

    <el-row :gutter="16">
      <el-col :md="10">
        <el-card shadow="never" class="mb-16">
          <template #header>模型导出</template>
          <el-form label-width="100px">
            <el-form-item label="选择模型">
              <el-select v-model="model" placeholder="请选择" style="width: 100%">
                <el-option label="实体识别模型 v5.2" value="1" />
                <el-option label="OCR 识别模型 v3.4" value="2" />
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
          <el-table :data="targets" border>
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
import { ref, onMounted } from 'vue'
import { Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'
import { getDeployTargets, EXPORT_FORMATS } from '@/api/modules/model'

const model = ref('1')
const format = ref('ONNX')
const quant = ref('none')
const exporting = ref(false)
const targets = ref([])
const deployLogs = ref([])

function exportModel() {
  exporting.value = true
  setTimeout(() => {
    exporting.value = false
    ElMessage.success(`已导出 ${format.value} 格式模型文件`)
  }, 1200)
}
function deploy(row) {
  deployLogs.value = [
    `[1/4] 正在将模型 ${format.value} 推送至「${row.name}」...`,
    `[2/4] 校验模型完整性... OK`,
    `[3/4] 加载模型到推理引擎... OK`,
    `[4/4] 健康检查通过，服务已就绪 ✓`
  ]
  ElMessage.success(`已部署至 ${row.name}`)
}
onMounted(async () => {
  targets.value = await getDeployTargets()
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
