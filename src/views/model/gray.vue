<template>
  <div>
    <PageHeader title="模型灰度上线" description="将微调模型灰度发布至生产环境，仅对指定部门或案件生效，实时监控灰度版本运行效果与错误率">
      <template #extra><el-button type="primary" :icon="Promotion" @click="dialog = true">新建灰度发布</el-button></template>
    </PageHeader>

    <el-card shadow="never" class="mb-16">
      <template #header>灰度发布中的版本</template>
      <el-row :gutter="16">
        <el-col v-for="g in releases" :key="g.id" :md="12">
          <div class="gray-card">
            <div class="flex-between">
              <span class="g-name">{{ g.name }}</span>
              <el-tag type="primary" size="small">{{ g.status }}</el-tag>
            </div>
            <div class="g-scope">生效范围：{{ g.scope }}</div>
            <div class="g-traffic">
              <span>流量比例</span>
              <el-slider v-model="g.traffic" :max="100" :format-tooltip="(v) => v + '%'" />
            </div>
            <el-row class="g-stats">
              <el-col :span="8"><div class="s-val">{{ g.requests.toLocaleString() }}</div><div class="s-label">请求数</div></el-col>
              <el-col :span="8"><div class="s-val" :class="{ warn: g.errorRate > 1 }">{{ g.errorRate }}%</div><div class="s-label">错误率</div></el-col>
              <el-col :span="8"><div class="s-val ok">{{ g.accuracy }}%</div><div class="s-label">准确率</div></el-col>
            </el-row>
            <div class="g-actions">
              <el-button size="small" type="success" @click="ElMessage.success('已扩大灰度流量')">扩大流量</el-button>
              <el-button size="small" type="warning">暂停</el-button>
              <el-button size="small" type="danger">回滚</el-button>
            </div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <el-card shadow="never">
      <template #header>灰度运行趋势（准确率 / 错误率）</template>
      <BaseChart :option="trendOption" height="320px" />
    </el-card>

    <el-dialog v-model="dialog" title="新建灰度发布" width="560px">
      <el-form label-width="110px">
        <el-form-item label="选择模型"><el-select placeholder="待评估通过的模型" style="width: 100%"><el-option label="实体识别模型 v5.3" value="1" /></el-select></el-form-item>
        <el-form-item label="生效范围">
          <el-radio-group v-model="scope"><el-radio value="dept">按部门</el-radio><el-radio value="case">按案件</el-radio></el-radio-group>
        </el-form-item>
        <el-form-item :label="scope === 'dept' ? '选择部门' : '选择案件'">
          <el-select multiple placeholder="可多选" style="width: 100%">
            <el-option label="刑侦支队" value="1" /><el-option label="经侦支队" value="2" />
          </el-select>
        </el-form-item>
        <el-form-item label="初始流量"><el-slider v-model="traffic" :max="100" :format-tooltip="(v) => v + '%'" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialog = false">取消</el-button><el-button type="primary" @click="confirm">发布</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Promotion } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'
import BaseChart from '@/components/BaseChart.vue'
import { getGrayReleases, getGrayTrend } from '@/api/modules/model'

const releases = ref([])
const trend = ref({ points: [], accuracy: [], errorRate: [] })
const dialog = ref(false)
const scope = ref('dept')
const traffic = ref(10)

function confirm() {
  dialog.value = false
  ElMessage.success('灰度发布已创建')
}
onMounted(async () => {
  releases.value = await getGrayReleases()
  trend.value = await getGrayTrend()
})

const trendOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['准确率', '错误率'] },
  grid: { left: 45, right: 45, top: 40, bottom: 30 },
  xAxis: { type: 'category', boundaryGap: false, data: trend.value.points },
  yAxis: [
    { type: 'value', name: '准确率(%)', min: 85, max: 100 },
    { type: 'value', name: '错误率(%)', min: 0, max: 3 }
  ],
  color: ['#52c41a', '#f5222d'],
  series: [
    { name: '准确率', type: 'line', smooth: true, data: trend.value.accuracy },
    { name: '错误率', type: 'line', smooth: true, yAxisIndex: 1, data: trend.value.errorRate }
  ]
}))
</script>

<style lang="scss" scoped>
.gray-card {
  border: 1px solid #ebeef5;
  border-radius: 6px;
  padding: 16px;
  margin-bottom: 16px;
}
.g-name { font-weight: 600; font-size: 15px; }
.g-scope { font-size: 12px; color: #8a919f; margin: 8px 0; }
.g-traffic { display: flex; align-items: center; gap: 12px; font-size: 13px; }
.g-traffic :deep(.el-slider) { flex: 1; }
.g-stats { text-align: center; margin: 12px 0; }
.s-val { font-size: 20px; font-weight: 700; &.warn { color: #f5222d; } &.ok { color: #52c41a; } }
.s-label { font-size: 12px; color: #8a919f; }
.g-actions { display: flex; gap: 8px; justify-content: flex-end; }
</style>
