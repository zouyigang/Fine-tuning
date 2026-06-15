<template>
  <div>
    <PageHeader title="数据集统计分析" description="统计数据集规模、标注完成率、实体/关系类型分布、标注质量评分，自动识别标注不均衡问题并给出优化建议" />

    <el-card shadow="never" class="mb-16">
      <el-form :inline="true">
        <el-form-item label="数据集">
          <el-select v-model="datasetId" style="width: 280px" @change="load">
            <el-option label="审讯笔录数据集-2026001" :value="1" />
            <el-option label="资金流水数据集-2026002" :value="2" />
          </el-select>
        </el-form-item>
      </el-form>
    </el-card>

    <el-row :gutter="16" v-if="data.overview">
      <el-col :xs="12" :md="6"><StatCard label="样本总量" :value="data.overview.total.toLocaleString()" icon="Coin" bg="#2f54eb" class="mb-16" /></el-col>
      <el-col :xs="12" :md="6"><StatCard label="已标注" :value="data.overview.labeled.toLocaleString()" icon="EditPen" bg="#13c2c2" class="mb-16" /></el-col>
      <el-col :xs="12" :md="6"><StatCard label="标注质量评分" :value="data.overview.quality" unit="%" icon="Star" bg="#52c41a" class="mb-16" /></el-col>
      <el-col :xs="12" :md="6"><StatCard label="均衡度" :value="data.overview.balance" unit="%" icon="ScaleToOriginal" bg="#fa8c16" class="mb-16" /></el-col>
    </el-row>

    <el-row :gutter="16">
      <el-col :md="12">
        <el-card shadow="never" class="mb-16">
          <template #header>实体类型分布</template>
          <BaseChart :option="barOption" height="320px" />
        </el-card>
      </el-col>
      <el-col :md="12">
        <el-card shadow="never" class="mb-16">
          <template #header>数据类型构成</template>
          <BaseChart :option="pieOption" height="320px" />
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never">
      <template #header>
        <div class="flex"><el-icon color="#fa8c16"><WarningFilled /></el-icon><span style="margin-left: 6px">智能优化建议</span></div>
      </template>
      <el-alert v-for="(s, i) in data.suggestions" :key="i" :title="s" type="warning" :closable="false" show-icon class="mb-16" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import PageHeader from '@/components/PageHeader.vue'
import StatCard from '@/components/StatCard.vue'
import BaseChart from '@/components/BaseChart.vue'
import { getDatasetStatistics } from '@/api/modules/dataset'

const datasetId = ref(1)
const data = reactive({ overview: null, entityDist: [], typeDist: [], suggestions: [] })

async function load() {
  Object.assign(data, await getDatasetStatistics(datasetId.value))
}
onMounted(load)

const barOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 60, right: 20, top: 20, bottom: 30 },
  xAxis: { type: 'value' },
  yAxis: { type: 'category', data: data.entityDist.map((e) => e.name) },
  color: ['#2f54eb'],
  series: [{ type: 'bar', data: data.entityDist.map((e) => e.value), barWidth: '55%', label: { show: true, position: 'right' } }]
}))

const pieOption = computed(() => ({
  tooltip: { trigger: 'item' },
  legend: { bottom: 0 },
  color: ['#2f54eb', '#13c2c2', '#52c41a', '#fa8c16'],
  series: [{ type: 'pie', radius: ['40%', '68%'], center: ['50%', '44%'], label: { formatter: '{b} {d}%' }, data: data.typeDist }]
}))
</script>
