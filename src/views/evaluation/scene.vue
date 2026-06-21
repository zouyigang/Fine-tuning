<template>
  <div>
    <PageHeader title="真实业务场景验证" description="导入真实审讯案件数据进行批量测试，验证模型在实际办案场景中的表现，统计对疑难样本的识别准确率">
      <template #extra><el-button type="primary" :icon="Upload">导入案件数据</el-button></template>
    </PageHeader>

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
import { reactive, ref, computed, onMounted } from 'vue'
import { Upload } from '@element-plus/icons-vue'
import PageHeader from '@/components/PageHeader.vue'
import StatCard from '@/components/StatCard.vue'
import { getSceneValidation } from '@/api/modules/evaluation'

const data = reactive({ summary: null, cases: [] })

// 前端分页（本地数据），与各列表页分页控件保持统一，默认每页 10 条
const page = ref(1)
const pageSize = ref(10)
const pagedCases = computed(() => data.cases.slice((page.value - 1) * pageSize.value, page.value * pageSize.value))

onMounted(async () => Object.assign(data, await getSceneValidation()))
</script>
