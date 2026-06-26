<template>
  <div>
    <PageHeader title="数据集版本管理" description="对不同批次、不同标注阶段的数据集进行版本化管理，记录变更内容、标注人员与时间，支持版本回滚与对比" />

    <el-card shadow="never" class="mb-16">
      <el-form :inline="true">
        <el-form-item label="选择数据集">
          <el-select v-model="datasetId" style="width: 280px" @change="load">
            <el-option label="审讯笔录数据集-2026001" :value="1" />
            <el-option label="资金流水数据集-2026002" :value="2" />
            <el-option label="涉案人员数据集-2026003" :value="3" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="DocumentCopy" :disabled="checked.length !== 2" @click="compareDialog = true">
            版本对比{{ checked.length === 2 ? '' : '（选两个版本）' }}
          </el-button>
          <el-button type="success" :icon="Plus" @click="newDialog = true">新建版本</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never">
      <template #header>版本历史</template>
      <el-timeline>
        <el-timeline-item
          v-for="v in versions"
          :key="v.version"
          :type="v.current ? 'primary' : ''"
          :hollow="!v.current"
          :timestamp="v.time"
          placement="top"
        >
          <el-card shadow="hover" class="version-card">
            <div class="flex-between">
              <div class="flex" style="align-items: center; gap: 10px">
                <el-checkbox-group v-model="checked" :max="2">
                  <el-checkbox :value="v.version" />
                </el-checkbox-group>
                <span class="ver">{{ v.version }}</span>
                <el-tag v-if="v.current" type="success" size="small">当前版本</el-tag>
              </div>
              <div>
                <el-button link type="primary" size="small">查看</el-button>
                <el-button v-if="!v.current" link type="warning" size="small" @click="rollback(v)">回滚至此</el-button>
              </div>
            </div>
            <p class="desc">{{ v.desc }}</p>
            <div class="meta text-muted">
              <span>标注人：{{ v.author }}</span>
              <el-divider direction="vertical" />
              <span>样本量：{{ v.count.toLocaleString() }}</span>
            </div>
          </el-card>
        </el-timeline-item>
      </el-timeline>
    </el-card>

    <el-dialog v-model="newDialog" title="新建版本" width="520px">
      <el-form label-width="90px">
        <el-form-item label="版本号">
          <el-input v-model="newForm.version" placeholder="留空则自动顺延（如 v1.1）" />
        </el-form-item>
        <el-form-item label="变更说明">
          <el-input v-model="newForm.desc" type="textarea" :rows="3" placeholder="描述本次版本的变更内容" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="newDialog = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="createVersion">确认创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="compareDialog" title="版本对比" width="700px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="对比版本">{{ checked[0] }} ↔ {{ checked[1] }}</el-descriptions-item>
        <el-descriptions-item label="样本量变化">+3,200</el-descriptions-item>
        <el-descriptions-item label="新增标注">3,200 条风险样本</el-descriptions-item>
        <el-descriptions-item label="修改标注">1,180 条实体边界</el-descriptions-item>
        <el-descriptions-item label="删除样本">120 条无效样本</el-descriptions-item>
        <el-descriptions-item label="质量评分变化">95.1% → 96.4%</el-descriptions-item>
      </el-descriptions>
      <template #footer><el-button type="primary" @click="compareDialog = false">关闭</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onActivated } from 'vue'
import { DocumentCopy, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'
import { getDatasetVersions, rollbackDatasetVersion, createDatasetVersion } from '@/api/modules/dataset'

const datasetId = ref(1)
const versions = ref([])
const checked = ref([])
const compareDialog = ref(false)
const newDialog = ref(false)
const creating = ref(false)
const newForm = reactive({ version: '', desc: '' })

async function load() {
  versions.value = await getDatasetVersions(datasetId.value)
}
async function createVersion() {
  creating.value = true
  try {
    const v = await createDatasetVersion({ datasetId: datasetId.value, desc: newForm.desc, version: newForm.version || undefined })
    newDialog.value = false
    newForm.version = ''
    newForm.desc = ''
    ElMessage.success(`已创建版本 ${v.version}`)
    await load()
  } finally {
    creating.value = false
  }
}
async function rollback(v) {
  await ElMessageBox.confirm(`确认将数据集回滚至 ${v.version}？当前版本将保留为历史版本。`, '版本回滚', { type: 'warning' })
  await rollbackDatasetVersion(v.id)
  ElMessage.success(`已回滚至 ${v.version}`)
  await load()
}
onActivated(load)
</script>

<style lang="scss" scoped>
.version-card {
  .ver {
    font-weight: 600;
    font-size: 15px;
  }
  .desc {
    margin: 10px 0 8px;
    font-size: 13px;
  }
  .meta {
    font-size: 12px;
  }
}
</style>
