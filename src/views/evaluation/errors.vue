<template>
  <div>
    <PageHeader title="错误案例分析" description="自动收集模型识别错误的样本，按错误类型分类统计，支持导出错误案例用于优化数据集和调整训练参数" />

    <el-row :gutter="16">
      <el-col :md="9">
        <el-card shadow="never" class="mb-16">
          <template #header>错误类型分布</template>
          <BaseChart :option="pieOption" height="320px" />
        </el-card>
      </el-col>
      <el-col :md="15">
        <el-card shadow="never" class="mb-16">
          <template #header>
            <div class="flex-between">
              <span>错误案例</span>
              <div>
                <el-select v-model="query.errorType" placeholder="按错误类型筛选" clearable size="small" style="width: 180px" @change="load">
                  <el-option v-for="t in errorTypes" :key="t" :label="t" :value="t" />
                </el-select>
                <el-button :icon="Download" size="small" class="ml-8" @click="exportCases">导出</el-button>
              </div>
            </div>
          </template>
          <el-table v-loading="loading" :data="list" border size="small">
            <el-table-column prop="errorType" label="错误类型" width="130">
              <template #default="{ row }"><el-tag type="danger" size="small" effect="plain">{{ row.errorType }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="content" label="样本" min-width="180" show-overflow-tooltip />
            <el-table-column prop="expected" label="正确标注" width="130" />
            <el-table-column prop="actual" label="模型输出" width="130" />
            <el-table-column prop="count" label="出现次数" width="90" sortable />
          </el-table>
          <el-pagination class="mt-16" small background layout="total, prev, pager, next" :total="total" v-model:current-page="query.page" @change="load" />
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never">
      <template #header>优化建议</template>
      <el-alert title="“实体边界错误”占比最高（建议补充边界模糊样本，增强分词鲁棒性）" type="warning" :closable="false" class="mb-16" show-icon />
      <el-alert title="“漏识别”集中在长文本场景（建议增大 max_seq_len 至 2048）" type="warning" :closable="false" show-icon />
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'
import BaseChart from '@/components/BaseChart.vue'
import { getErrorCases } from '@/api/modules/evaluation'

const loading = ref(false)
const list = ref([])
const total = ref(0)
const dist = ref([])
const query = reactive({ errorType: '', page: 1, pageSize: 10 })
const errorTypes = ['实体边界错误', '类型误判', '漏识别', '关系抽取错误', '事件要素缺失']

async function load() {
  loading.value = true
  const res = await getErrorCases(query)
  list.value = res.list
  total.value = res.total
  dist.value = res.dist
  loading.value = false
}
function exportCases() {
  ElMessage.success('错误案例已导出（error-cases.xlsx）')
}
onMounted(load)

const pieOption = computed(() => ({
  tooltip: { trigger: 'item' },
  legend: { bottom: 0, type: 'scroll' },
  color: ['#f5222d', '#fa8c16', '#fadb14', '#722ed1', '#13c2c2'],
  series: [{ type: 'pie', roseType: 'radius', radius: ['30%', '65%'], center: ['50%', '42%'], data: dist.value }]
}))
</script>

<style lang="scss" scoped>
.ml-8 { margin-left: 8px; }
</style>
