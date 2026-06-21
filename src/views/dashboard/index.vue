<template>
  <div class="dashboard">
    <PageHeader title="工作台" description="模型微调通用平台总览 · 数据集 / 微调任务 / 模型评估 / 上线发布 全流程一站式管理" />

    <!-- 指标卡 -->
    <el-row :gutter="16" class="dash-row">
      <el-col v-for="s in data.stats" :key="s.label" :xs="12" :sm="12" :md="6">
        <StatCard v-bind="s" class="stat-item" />
      </el-col>
    </el-row>

    <el-row :gutter="16" class="dash-row">
      <el-col :md="16">
        <el-card shadow="never">
          <template #header>
            <div class="flex-between">
              <span>微调任务趋势（近 14 天）</span>
              <el-radio-group v-model="trendType" size="small">
                <el-radio-button value="all">全部</el-radio-button>
                <el-radio-button value="created">新建</el-radio-button>
                <el-radio-button value="finished">完成</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <BaseChart :option="trendOption" height="300px" />
        </el-card>
      </el-col>
      <el-col :md="8">
        <el-card shadow="never">
          <template #header>模型类型分布</template>
          <BaseChart :option="pieOption" height="300px" />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="dash-row">
      <el-col :md="14">
        <el-card shadow="never" class="fill-card">
          <template #header>最近微调任务</template>
          <el-table :data="data.recentTasks" border>
            <el-table-column prop="name" label="任务名称" min-width="200" />
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="TASK_STATUS[row.status].type" size="small">{{ TASK_STATUS[row.status].label }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="进度" width="160">
              <template #default="{ row }">
                <el-progress :percentage="row.progress" :status="row.status === 'failed' ? 'exception' : row.progress === 100 ? 'success' : ''" />
              </template>
            </el-table-column>
            <el-table-column prop="creator" label="创建人" width="90" />
          </el-table>
        </el-card>
      </el-col>
      <el-col :md="10">
        <el-card shadow="never" class="fill-card">
          <template #header>
            <div class="flex-between">
              <span>待办事项</span>
              <el-badge :value="data.todos.length" type="danger" />
            </div>
          </template>
          <div v-for="(t, i) in data.todos" :key="i" class="todo-item">
            <el-tag :type="t.level" size="small" effect="light">{{ t.type }}</el-tag>
            <span class="todo-text">{{ t.text }}</span>
            <el-button link type="primary" size="small">处理</el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import PageHeader from '@/components/PageHeader.vue'
import StatCard from '@/components/StatCard.vue'
import BaseChart from '@/components/BaseChart.vue'
import { TASK_STATUS } from '@/utils/dict'
import { getDashboardOverview } from '@/api/modules/dashboard'

const data = reactive({ stats: [], taskTrend: { dates: [] }, modelTypeDist: [], recentTasks: [], todos: [] })
const trendType = ref('all')

onMounted(async () => {
  Object.assign(data, await getDashboardOverview())
})

const trendOption = computed(() => {
  const series = []
  if (trendType.value !== 'finished')
    series.push({ name: '新建任务', type: 'line', smooth: true, areaStyle: { opacity: 0.1 }, data: data.taskTrend.created })
  if (trendType.value !== 'created')
    series.push({ name: '完成任务', type: 'line', smooth: true, areaStyle: { opacity: 0.1 }, data: data.taskTrend.finished })
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: series.map((s) => s.name) },
    grid: { left: 30, right: 20, top: 40, bottom: 30 },
    xAxis: { type: 'category', boundaryGap: false, data: data.taskTrend.dates },
    yAxis: { type: 'value' },
    color: ['#2f54eb', '#52c41a'],
    series
  }
})

const pieOption = computed(() => ({
  tooltip: { trigger: 'item' },
  // 图例置底（自动换行展示全部类型），环状图上移并缩小，与图例留出安全间距
  legend: { bottom: 4, itemGap: 12, textStyle: { fontSize: 12 } },
  color: ['#2f54eb', '#13c2c2', '#52c41a', '#fa8c16', '#722ed1'],
  series: [
    {
      type: 'pie',
      radius: ['34%', '50%'],
      center: ['50%', '36%'],
      avoidLabelOverlap: true,
      label: { formatter: '{b}\n{d}%', fontSize: 12 },
      labelLine: { length: 8, length2: 10 },
      data: data.modelTypeDist
    }
  ]
}))
</script>

<style lang="scss" scoped>
// 三大区块（指标卡 / 图表 / 表格）行间距统一为 16px。
// 指标卡用 height:100%，其自身 margin 会被吸收，故间距统一交给行来控制。
.dash-row:not(:last-child) {
  margin-bottom: 16px;
}
// 指标卡在小屏换行时（xs/sm 两两换行）需要行内纵向间距
.stat-item {
  margin-bottom: 0;
}
@media (max-width: 992px) {
  .stat-item {
    margin-bottom: 16px;
  }
}
// 底部左右两栏等高：卡片填满各自列（列已被 el-row 拉伸至行高），
// 内容不足的一栏自然在底部留白，避免左右高度不一致
.fill-card {
  height: 100%;
}
.todo-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 0;
  border-bottom: 1px solid #f0f0f0;
  &:last-child {
    border-bottom: none;
  }
  .todo-text {
    flex: 1;
    font-size: 13px;
  }
}
:deep(.el-card__header) {
  padding: 14px 18px;
  font-weight: 600;
}
</style>
