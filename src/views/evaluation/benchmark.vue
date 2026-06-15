<template>
  <div>
    <PageHeader title="基准模型对比" description="自动将微调模型与原生产模型、历史最优模型进行多维度指标对比，生成对比图表，高亮性能提升/下降项" />

    <el-row :gutter="16">
      <el-col :md="12">
        <el-card shadow="never" class="mb-16">
          <template #header>多维度雷达对比</template>
          <BaseChart :option="radarOption" height="360px" />
        </el-card>
      </el-col>
      <el-col :md="12">
        <el-card shadow="never" class="mb-16">
          <template #header>指标柱状对比</template>
          <BaseChart :option="barOption" height="360px" />
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never">
      <template #header>对比明细（微调模型 vs 当前生产模型）</template>
      <el-table :data="data.compare" border>
        <el-table-column prop="dim" label="评估维度" />
        <el-table-column prop="current" label="本次微调模型" />
        <el-table-column prop="prod" label="当前生产模型" />
        <el-table-column label="差值" width="160">
          <template #default="{ row }">
            <el-tag :type="row.diff >= 0 ? 'success' : 'danger'" effect="light">
              <el-icon><component :is="row.diff >= 0 ? 'Top' : 'Bottom'" /></el-icon>
              {{ row.diff >= 0 ? '+' : '' }}{{ row.diff }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="结论" width="120">
          <template #default="{ row }">
            <span :class="row.diff >= 0 ? 'text-up' : 'text-down'">{{ row.diff >= 0 ? '提升' : '下降' }}</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, computed, onMounted } from 'vue'
import PageHeader from '@/components/PageHeader.vue'
import BaseChart from '@/components/BaseChart.vue'
import { getBenchmark } from '@/api/modules/evaluation'

const data = reactive({ dims: [], models: [], compare: [] })
onMounted(async () => Object.assign(data, await getBenchmark()))

const radarOption = computed(() => ({
  tooltip: {},
  legend: { data: data.models.map((m) => m.name), bottom: 0 },
  color: ['#2f54eb', '#fa8c16', '#52c41a'],
  radar: { indicator: data.dims.map((d) => ({ name: d, max: 100 })), radius: '65%' },
  series: [
    {
      type: 'radar',
      data: data.models.map((m) => ({ name: m.name, value: m.values, areaStyle: { opacity: 0.1 } }))
    }
  ]
}))

const barOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: data.models.map((m) => m.name), bottom: 0 },
  grid: { left: 40, right: 20, top: 20, bottom: 50 },
  xAxis: { type: 'category', data: data.dims },
  yAxis: { type: 'value', min: 70, max: 100 },
  color: ['#2f54eb', '#fa8c16', '#52c41a'],
  series: data.models.map((m) => ({ name: m.name, type: 'bar', data: m.values }))
}))
</script>

<style lang="scss" scoped>
.text-up { color: #52c41a; font-weight: 600; }
.text-down { color: #f5222d; font-weight: 600; }
</style>
