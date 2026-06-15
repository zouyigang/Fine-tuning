<template>
  <div>
    <PageHeader title="自动化指标评估" description="针对不同模型类型自动计算业务指标：OCR 字符/行准确率、实体识别 P/R/F1、关系三元组准确率、事件识别准确率等" />

    <el-card shadow="never" class="mb-16">
      <el-form :inline="true">
        <el-form-item label="评估模型">
          <el-select v-model="modelType" style="width: 200px" @change="load">
            <el-option label="OCR 识别" value="ocr" />
            <el-option label="实体识别" value="ner" />
            <el-option label="关系抽取" value="relation" />
            <el-option label="事件构建" value="event" />
          </el-select>
        </el-form-item>
        <el-form-item label="测试集">
          <el-select v-model="testset" style="width: 220px">
            <el-option label="标准测试集-2026Q2" value="1" />
            <el-option label="疑难样本测试集" value="2" />
          </el-select>
        </el-form-item>
        <el-form-item><el-button type="primary" :icon="DataAnalysis" :loading="loading" @click="load">开始评估</el-button></el-form-item>
      </el-form>
    </el-card>

    <el-row :gutter="16" class="mb-16">
      <el-col v-for="m in data.metrics" :key="m.name" :xs="12" :md="6">
        <div class="metric-card">
          <div class="metric-value">{{ m.value }}<span class="metric-unit">{{ m.unit }}</span></div>
          <div class="metric-name">{{ m.name }}</div>
        </div>
      </el-col>
    </el-row>

    <el-card shadow="never">
      <template #header>各类别细分指标</template>
      <el-row :gutter="16">
        <el-col :md="14">
          <el-table :data="data.perClass" border>
            <el-table-column prop="label" label="类别" />
            <el-table-column prop="precision" label="精确率(%)" sortable />
            <el-table-column prop="recall" label="召回率(%)" sortable />
            <el-table-column prop="f1" label="F1(%)" sortable>
              <template #default="{ row }">
                <span :class="{ 'low-score': row.f1 < 88 }">{{ row.f1 }}</span>
              </template>
            </el-table-column>
          </el-table>
        </el-col>
        <el-col :md="10"><BaseChart :option="chartOption" height="320px" /></el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { DataAnalysis } from '@element-plus/icons-vue'
import PageHeader from '@/components/PageHeader.vue'
import BaseChart from '@/components/BaseChart.vue'
import { getMetrics } from '@/api/modules/evaluation'

const modelType = ref('ner')
const testset = ref('1')
const loading = ref(false)
const data = reactive({ metrics: [], perClass: [] })

async function load() {
  loading.value = true
  Object.assign(data, await getMetrics(modelType.value))
  loading.value = false
}
onMounted(load)

const chartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['精确率', '召回率', 'F1'] },
  grid: { left: 40, right: 20, top: 40, bottom: 30 },
  xAxis: { type: 'category', data: data.perClass.map((c) => c.label) },
  yAxis: { type: 'value', min: 70, max: 100 },
  color: ['#2f54eb', '#13c2c2', '#52c41a'],
  series: [
    { name: '精确率', type: 'bar', data: data.perClass.map((c) => c.precision) },
    { name: '召回率', type: 'bar', data: data.perClass.map((c) => c.recall) },
    { name: 'F1', type: 'bar', data: data.perClass.map((c) => c.f1) }
  ]
}))
</script>

<style lang="scss" scoped>
.metric-card {
  background: linear-gradient(135deg, #2f54eb, #5b7cfa);
  border-radius: 6px;
  padding: 22px;
  color: #fff;
  text-align: center;
}
.metric-value {
  font-size: 30px;
  font-weight: 700;
  .metric-unit { font-size: 14px; margin-left: 2px; opacity: 0.85; }
}
.metric-name { margin-top: 6px; font-size: 13px; opacity: 0.9; }
.low-score { color: #f5222d; font-weight: 600; }
</style>
