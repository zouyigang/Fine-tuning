<template>
  <div>
    <PageHeader title="模型归档与清理" description="对已下线的历史模型进行归档存储，清理无效模型版本释放存储空间，核心模型版本永久保留便于追溯" />

    <el-row :gutter="16" class="mb-16">
      <el-col :xs="12" :md="6"><StatCard label="归档模型" :value="total" unit="个" icon="FolderOpened" bg="#2f54eb" /></el-col>
      <el-col :xs="12" :md="6"><StatCard label="占用存储" value="1.8" unit="TB" icon="Coin" bg="#fa8c16" /></el-col>
      <el-col :xs="12" :md="6"><StatCard label="可清理空间" value="640" unit="GB" icon="Delete" bg="#f5222d" /></el-col>
      <el-col :xs="12" :md="6"><StatCard label="永久保留" value="6" unit="个" icon="Lock" bg="#52c41a" /></el-col>
    </el-row>

    <el-card shadow="never">
      <template #header>
        <div class="flex-between">
          <span>归档模型列表</span>
          <el-button type="danger" plain :icon="Delete" :disabled="!selection.length" @click="batchClean">批量清理（{{ selection.length }}）</el-button>
        </div>
      </template>
      <el-table v-loading="loading" :data="list" border @selection-change="(v) => (selection = v)">
        <el-table-column type="selection" width="50" :selectable="(row) => !row.permanent" />
        <el-table-column prop="name" label="模型" min-width="140" />
        <el-table-column prop="version" label="版本" width="80" />
        <el-table-column prop="f1" label="F1" width="90" />
        <el-table-column prop="size" label="大小" width="90" />
        <el-table-column prop="archivedAt" label="归档时间" width="120" />
        <el-table-column label="保留策略" width="120">
          <template #default="{ row }">
            <el-tag :type="row.permanent ? 'success' : 'info'" size="small">{{ row.permanent ? '永久保留' : '可清理' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="restore(row)">恢复</el-button>
            <el-button link type="primary" size="small" @click="download(row)">下载</el-button>
            <el-button link type="danger" size="small" :disabled="row.permanent" @click="clean(row)">清理</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination class="mt-16" background layout="total, sizes, prev, pager, next" :page-sizes="[10, 20, 50, 100]" :total="total" v-model:current-page="query.page" v-model:page-size="query.pageSize" @change="load" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Delete } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'
import StatCard from '@/components/StatCard.vue'
import { getArchiveList, cleanArchive, batchCleanArchive, restoreArchive, downloadModel } from '@/api/modules/model'

const loading = ref(false)
const list = ref([])
const total = ref(0)
const selection = ref([])
const query = reactive({ page: 1, pageSize: 10 })

async function load() {
  loading.value = true
  const res = await getArchiveList(query)
  list.value = res.list
  total.value = res.total
  loading.value = false
}
async function clean(row) {
  await ElMessageBox.confirm(`确认清理 ${row.name} ${row.version}？清理后不可恢复。`, '清理模型', { type: 'warning' })
  await cleanArchive(row.id)
  ElMessage.success('已清理，释放存储空间')
  load()
}
async function batchClean() {
  await ElMessageBox.confirm(`确认批量清理 ${selection.value.length} 个模型版本？`, '批量清理', { type: 'warning' })
  const res = await batchCleanArchive(selection.value.map((r) => r.id))
  ElMessage.success(`批量清理完成，共清理 ${res.cleaned} 个`)
  load()
}
async function restore(row) {
  await ElMessageBox.confirm(`确认恢复 ${row.name} ${row.version}？恢复后状态置为「已下线」。`, '恢复模型', { type: 'info' })
  await restoreArchive(row.id)
  ElMessage.success('已恢复')
  load()
}
async function download(row) {
  await downloadModel(row.id)
  ElMessage.success('开始下载模型产物')
}
onMounted(load)
</script>
