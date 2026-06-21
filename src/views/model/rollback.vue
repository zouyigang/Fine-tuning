<template>
  <div>
    <PageHeader title="模型快速回滚" description="上线后出现问题时，一键回滚至上一个稳定版本，回滚过程不中断业务运行，所有操作全程审计" />

    <el-row :gutter="16">
      <el-col :md="14">
        <el-card shadow="never" class="mb-16">
          <template #header>当前线上模型</template>
          <div class="online-banner">
            <div>
              <div class="ob-name">实体识别模型 v5.2</div>
              <div class="ob-meta">上线时间：2026-06-08 15:00 · F1 0.935</div>
            </div>
            <el-tag type="success" effect="dark" size="large">运行中</el-tag>
          </div>
        </el-card>

        <el-card shadow="never">
          <template #header>可回滚的稳定版本</template>
          <el-table v-loading="loading" :data="pagedCandidates" border>
            <el-table-column prop="name" label="模型" min-width="130" />
            <el-table-column prop="version" label="版本" width="80" />
            <el-table-column prop="f1" label="F1" width="90" />
            <el-table-column label="稳定性" width="100">
              <template #default="{ row }"><el-tag :type="row.stable ? 'success' : 'info'" size="small">{{ row.stable ? '稳定' : '一般' }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="trainAt" label="训练时间" width="150" />
            <el-table-column label="操作" width="120" fixed="right">
              <template #default="{ row }"><el-button type="warning" size="small" :icon="RefreshLeft" @click="rollback(row)">回滚至此</el-button></template>
            </el-table-column>
          </el-table>
          <el-pagination class="mt-16" background layout="total, sizes, prev, pager, next" :page-sizes="[10, 20, 50, 100]" :total="candidates.length" v-model:current-page="page" v-model:page-size="pageSize" />
        </el-card>
      </el-col>

      <el-col :md="10">
        <el-card shadow="never">
          <template #header>回滚审计记录</template>
          <el-timeline>
            <el-timeline-item v-for="(h, i) in history" :key="i" :timestamp="h.time" :type="h.action === '回滚' ? 'warning' : 'primary'" placement="top">
              <b>{{ h.version }}</b> · {{ h.action }}
              <div class="text-muted" style="font-size: 12px">操作人：{{ h.operator }}</div>
              <div v-if="h.note" class="text-muted" style="font-size: 12px">{{ h.note }}</div>
            </el-timeline-item>
          </el-timeline>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { RefreshLeft } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'
import { getRollbackCandidates, getReleaseHistory, rollbackModel } from '@/api/modules/model'

const loading = ref(false)
const candidates = ref([])
const history = ref([])

// 前端分页（本地数据），与各列表页分页控件保持统一，默认每页 10 条
const page = ref(1)
const pageSize = ref(10)
const pagedCandidates = computed(() => candidates.value.slice((page.value - 1) * pageSize.value, page.value * pageSize.value))

async function load() {
  loading.value = true
  candidates.value = await getRollbackCandidates()
  history.value = await getReleaseHistory()
  loading.value = false
}
async function rollback(row) {
  await ElMessageBox.confirm(`确认回滚至 ${row.name} ${row.version}？业务不会中断。`, '快速回滚', { type: 'warning' })
  await rollbackModel(row.id, { note: `手动回滚至 ${row.version}` })
  ElMessage.success(`已回滚至 ${row.version}，回滚记录已写入审计日志`)
  await load()
}
onMounted(load)
</script>

<style lang="scss" scoped>
.online-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  background: linear-gradient(135deg, #f6ffed, #fff);
  border: 1px solid #b7eb8f;
  border-radius: 6px;
}
.ob-name { font-size: 16px; font-weight: 600; }
.ob-meta { font-size: 12px; color: #8a919f; margin-top: 4px; }
</style>
