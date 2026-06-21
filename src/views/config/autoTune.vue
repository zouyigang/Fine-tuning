<template>
  <div>
    <PageHeader title="自动调优配置" description="开启自动超参调优，系统自动搜索最优超参组合，可配置调优目标（如最大化 F1、最小化训练时间）" />

    <el-row :gutter="16" class="mb-16">
      <el-col :md="10">
        <el-card shadow="never">
          <template #header>
            <div class="flex-between"><span>调优配置</span><el-switch v-model="cfg.enabled" active-text="启用自动调优" /></div>
          </template>
          <el-form label-width="120px" :disabled="!cfg.enabled">
            <el-form-item label="调优目标">
              <el-select v-model="cfg.objective" style="width: 100%">
                <el-option label="最大化 F1 值" value="maximize_f1" />
                <el-option label="最大化准确率" value="maximize_acc" />
                <el-option label="最小化训练时间" value="minimize_time" />
                <el-option label="最小化验证损失" value="minimize_loss" />
              </el-select>
            </el-form-item>
            <el-form-item label="搜索算法">
              <el-select v-model="cfg.searchAlgo" style="width: 100%">
                <el-option label="贝叶斯优化" value="bayesian" />
                <el-option label="网格搜索" value="grid" />
                <el-option label="随机搜索" value="random" />
                <el-option label="Hyperband" value="hyperband" />
              </el-select>
            </el-form-item>
            <el-form-item label="最大试验次数"><el-input-number v-model="cfg.maxTrials" :min="5" :max="200" /></el-form-item>
            <el-form-item label="并行试验数"><el-input-number v-model="cfg.parallelTrials" :min="1" :max="16" /></el-form-item>
            <el-form-item><el-button type="primary" @click="save">保存并启动调优</el-button></el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <el-col :md="14">
        <el-card shadow="never">
          <template #header>试验结果对比（F1）</template>
          <BaseChart :option="trialChart" height="280px" />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <el-col :md="10">
        <el-card shadow="never">
          <template #header>搜索空间</template>
          <el-table :data="cfg.searchSpace" size="small" border>
            <el-table-column prop="param" label="超参数" />
            <el-table-column prop="range" label="搜索范围" />
            <el-table-column prop="type" label="类型" width="80" />
          </el-table>
        </el-card>
      </el-col>

      <el-col :md="14">
        <el-card shadow="never">
          <template #header>
            <div class="flex-between"><span>试验记录</span><el-tag type="success">最优 F1：{{ bestF1 }}</el-tag></div>
          </template>
          <el-table :data="pagedTrials" border size="small">
            <el-table-column prop="trial" label="#" width="50" />
            <el-table-column prop="lr" label="学习率" />
            <el-table-column prop="batchSize" label="批次" width="70" />
            <el-table-column prop="epochs" label="轮数" width="70" />
            <el-table-column prop="f1" label="F1" sortable>
              <template #default="{ row }"><b :class="{ best: row.f1 === bestF1 }">{{ row.f1 }}</b></template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="90">
              <template #default="{ row }"><el-tag size="small" :type="row.status === '已完成' ? 'success' : 'primary'">{{ row.status }}</el-tag></template>
            </el-table-column>
          </el-table>
          <el-pagination class="mt-16" background layout="total, sizes, prev, pager, next" :page-sizes="[10, 20, 50, 100]" :total="cfg.trials.length" v-model:current-page="page" v-model:page-size="pageSize" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { reactive, ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'
import BaseChart from '@/components/BaseChart.vue'
import { getAutoTuneConfig, saveAutoTuneConfig } from '@/api/modules/config'

const cfg = reactive({ enabled: true, objective: '', searchAlgo: '', maxTrials: 30, parallelTrials: 4, searchSpace: [], trials: [] })
const bestF1 = computed(() => (cfg.trials.length ? Math.max(...cfg.trials.map((t) => t.f1)) : 0))

// 试验记录前端分页（本地数据），与各列表页分页控件保持统一，默认每页 10 条
const page = ref(1)
const pageSize = ref(10)
const pagedTrials = computed(() => cfg.trials.slice((page.value - 1) * pageSize.value, page.value * pageSize.value))

const trialChart = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 40, right: 20, top: 30, bottom: 30 },
  xAxis: { type: 'category', data: cfg.trials.map((t) => `#${t.trial}`) },
  yAxis: { type: 'value', min: 0.85, max: 1 },
  color: ['#2f54eb'],
  series: [
    {
      type: 'bar',
      data: cfg.trials.map((t) => ({ value: t.f1, itemStyle: { color: t.f1 === bestF1.value ? '#52c41a' : '#2f54eb' } })),
      label: { show: true, position: 'top' }
    }
  ]
}))

async function save() {
  await saveAutoTuneConfig({
    enabled: cfg.enabled, objective: cfg.objective, searchAlgo: cfg.searchAlgo,
    maxTrials: cfg.maxTrials, parallelTrials: cfg.parallelTrials
  })
  ElMessage.success('自动调优配置已保存，调优任务已启动')
}
onMounted(async () => Object.assign(cfg, await getAutoTuneConfig()))
</script>

<style lang="scss" scoped>
.best { color: #52c41a; }
</style>
