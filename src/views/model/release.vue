<template>
  <div>
    <PageHeader title="模型全量上线" description="灰度验证通过后，一键将模型全量上线至所有业务模块，自动同步至模型管理模块并替换原有模型" />

    <el-row :gutter="16">
      <el-col :md="14">
        <el-card shadow="never" class="mb-16">
          <template #header>待上线模型</template>
          <el-table :data="candidates" border @current-change="(r) => (selected = r)" highlight-current-row>
            <el-table-column width="50">
              <template #default="{ row }"><el-radio :model-value="selected?.id" :value="row.id" @change="selected = row"><span></span></el-radio></template>
            </el-table-column>
            <el-table-column prop="name" label="模型" min-width="140" />
            <el-table-column prop="version" label="版本" width="80" />
            <el-table-column prop="grayResult" label="灰度结果" width="120">
              <template #default="{ row }"><el-tag type="success" size="small">{{ row.grayResult }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="f1" label="F1" width="80" />
          </el-table>
        </el-card>

        <el-card shadow="never">
          <template #header>上线审批流程</template>
          <el-steps :active="approveStep" align-center finish-status="success">
            <el-step title="算法工程师申请" description="张三 · 06-08 14:00" />
            <el-step title="技术负责人审核" description="李四 · 06-08 16:30" />
            <el-step title="审批管理员批准" :description="approveStep >= 3 ? '王五 · 06-09 09:00' : '待审批'" />
            <el-step title="全量上线" :description="approveStep >= 4 ? '已上线' : '待执行'" />
          </el-steps>
        </el-card>
      </el-col>

      <el-col :md="10">
        <el-card shadow="never">
          <template #header>全量上线操作</template>
          <el-result v-if="!selected" icon="info" title="请先选择待上线模型" />
          <template v-else>
            <el-descriptions :column="1" border class="mb-16">
              <el-descriptions-item label="模型">{{ selected.name }} {{ selected.version }}</el-descriptions-item>
              <el-descriptions-item label="灰度准确率">93.6%</el-descriptions-item>
              <el-descriptions-item label="替换目标">生产环境同类模型</el-descriptions-item>
              <el-descriptions-item label="影响业务">实体识别、关系抽取模块</el-descriptions-item>
            </el-descriptions>
            <el-alert title="上线后将自动同步至模型管理模块并替换原有模型，原模型转为历史版本可回滚" type="warning" :closable="false" show-icon class="mb-16" />
            <el-button type="primary" size="large" :icon="Upload" :loading="releasing" style="width: 100%" @click="release">
              确认全量上线
            </el-button>
          </template>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Upload } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'

const candidates = ref([
  { id: 1, name: '实体识别模型', version: 'v5.2', grayResult: '验证通过', f1: 0.935 },
  { id: 2, name: 'OCR 识别模型', version: 'v3.4', grayResult: '验证通过', f1: 0.978 }
])
const selected = ref(null)
const approveStep = ref(2)
const releasing = ref(false)

async function release() {
  await ElMessageBox.confirm('确认将该模型全量上线？此操作将替换生产环境同类模型。', '全量上线', { type: 'warning' })
  releasing.value = true
  setTimeout(() => {
    releasing.value = false
    approveStep.value = 4
    ElMessage.success('模型已全量上线并同步至模型管理模块')
  }, 1500)
}
</script>
