<template>
  <div>
    <PageHeader title="训练资源配置" description="配置训练任务的 GPU/CPU 资源配额、最大训练时长、并发任务数，支持按部门分配训练资源，避免资源争抢" />

    <el-row :gutter="16" class="mb-16" v-if="data.cluster">
      <el-col :md="14">
        <el-card shadow="never">
          <template #header>集群资源总览</template>
          <el-row :gutter="20">
            <el-col :span="12">
              <BaseChart :option="gpuGauge" height="200px" />
            </el-col>
            <el-col :span="12">
              <BaseChart :option="cpuGauge" height="200px" />
            </el-col>
          </el-row>
          <el-row class="cluster-stats">
            <el-col :span="6"><div class="cs-val">{{ data.cluster.totalGpu }}</div><div class="cs-label">GPU 总数</div></el-col>
            <el-col :span="6"><div class="cs-val">{{ data.cluster.usedGpu }}</div><div class="cs-label">已占用 GPU</div></el-col>
            <el-col :span="6"><div class="cs-val">{{ data.cluster.runningTasks }}</div><div class="cs-label">运行中任务</div></el-col>
            <el-col :span="6"><div class="cs-val">{{ data.cluster.queuedTasks }}</div><div class="cs-label">排队任务</div></el-col>
          </el-row>
        </el-card>
      </el-col>
      <el-col :md="10">
        <el-card shadow="never">
          <template #header>资源配置说明</template>
          <el-alert title="GPU 配额按部门分配，超出配额的任务将自动排队" type="info" :closable="false" class="mb-16" show-icon />
          <el-alert title="单任务最大训练时长用于防止异常任务长期占用资源" type="info" :closable="false" class="mb-16" show-icon />
          <el-alert title="并发任务数限制保障集群整体稳定性" type="info" :closable="false" show-icon />
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never">
      <template #header>
        <div class="flex-between"><span>部门资源配额</span><el-button type="primary" size="small" @click="save">保存配额</el-button></div>
      </template>
      <el-table :data="pagedQuotas" border>
        <el-table-column prop="dept" label="部门" width="140" />
        <el-table-column label="GPU 配额" width="200">
          <template #default="{ row }"><el-input-number v-model="row.gpuQuota" :min="0" :max="32" size="small" /></template>
        </el-table-column>
        <el-table-column label="已用 / 配额" width="180">
          <template #default="{ row }"><el-progress :percentage="Math.round((row.gpuUsed / row.gpuQuota) * 100)" :format="() => `${row.gpuUsed}/${row.gpuQuota}`" /></template>
        </el-table-column>
        <el-table-column label="最大时长(h)" width="180">
          <template #default="{ row }"><el-input-number v-model="row.maxDuration" :min="1" :max="168" size="small" /></template>
        </el-table-column>
        <el-table-column label="并发任务数" width="180">
          <template #default="{ row }"><el-input-number v-model="row.maxConcurrent" :min="1" :max="10" size="small" /></template>
        </el-table-column>
      </el-table>
      <el-pagination class="mt-16" background layout="total, sizes, prev, pager, next" :page-sizes="[10, 20, 50, 100]" :total="data.quotas.length" v-model:current-page="page" v-model:page-size="pageSize" />
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref, computed, onActivated } from 'vue'
import { ElMessage } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'
import BaseChart from '@/components/BaseChart.vue'
import { getResourceQuotas, saveResourceQuotas } from '@/api/modules/config'

const data = reactive({ cluster: null, quotas: [] })

// 前端分页（本地数据），与各列表页分页控件保持统一，默认每页 10 条
const page = ref(1)
const pageSize = ref(10)
const pagedQuotas = computed(() => data.quotas.slice((page.value - 1) * pageSize.value, page.value * pageSize.value))

function gauge(title, value, color) {
  return {
    series: [
      {
        type: 'gauge',
        radius: '90%',
        progress: { show: true, width: 14, itemStyle: { color } },
        axisLine: { lineStyle: { width: 14 } },
        axisTick: { show: false },
        splitLine: { length: 10 },
        axisLabel: { fontSize: 10 },
        pointer: { width: 4 },
        detail: { valueAnimation: true, formatter: '{value}%', fontSize: 22, offsetCenter: [0, '70%'] },
        title: { offsetCenter: [0, '95%'], fontSize: 13 },
        data: [{ value, name: title }]
      }
    ]
  }
}
const gpuGauge = computed(() => gauge('GPU 使用率', data.cluster ? Math.round((data.cluster.usedGpu / data.cluster.totalGpu) * 100) : 0, '#2f54eb'))
const cpuGauge = computed(() => gauge('CPU 使用率', data.cluster ? Math.round((data.cluster.usedCpu / data.cluster.totalCpu) * 100) : 0, '#13c2c2'))

async function save() {
  await saveResourceQuotas(
    data.quotas.map((q) => ({
      dept: q.dept, gpuQuota: q.gpuQuota, maxDuration: q.maxDuration, maxConcurrent: q.maxConcurrent
    }))
  )
  ElMessage.success('资源配额已保存')
  Object.assign(data, await getResourceQuotas())
}
onActivated(async () => Object.assign(data, await getResourceQuotas()))
</script>

<style lang="scss" scoped>
.cluster-stats { text-align: center; border-top: 1px solid #f0f0f0; padding-top: 16px; }
.cs-val { font-size: 24px; font-weight: 700; color: #2f54eb; }
.cs-label { font-size: 12px; color: #8a919f; }
</style>
