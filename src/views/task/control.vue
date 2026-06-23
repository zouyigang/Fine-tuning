<template>
  <div>
    <PageHeader title="任务启停与重试" description="支持暂停、继续、终止训练任务；训练失败自动保存断点，支持从断点重试，避免重复训练" />

    <el-card shadow="never">
      <div class="flex-between mb-16">
        <el-radio-group v-model="query.status" @change="load">
          <el-radio-button value="">全部</el-radio-button>
          <el-radio-button value="running">训练中</el-radio-button>
          <el-radio-button value="paused">已暂停</el-radio-button>
          <el-radio-button value="failed">失败</el-radio-button>
          <el-radio-button value="success">已完成</el-radio-button>
        </el-radio-group>
        <el-input v-model="query.keyword" placeholder="搜索任务" :prefix-icon="Search" style="width: 220px" @keyup.enter="load" clearable />
      </div>

      <el-table v-loading="loading" :data="list" border>
        <el-table-column prop="name" label="任务名称" min-width="200" show-overflow-tooltip />
        <el-table-column prop="modelType" label="模型类型" width="110" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }"><el-tag :type="TASK_STATUS[row.status].type" size="small">{{ TASK_STATUS[row.status].label }}</el-tag></template>
        </el-table-column>
        <el-table-column label="进度" width="170">
          <template #default="{ row }"><el-progress :percentage="row.progress" :status="row.status === 'failed' ? 'exception' : ''" /></template>
        </el-table-column>
        <el-table-column prop="gpu" label="GPU" width="100" />
        <el-table-column prop="duration" label="已耗时" width="100" />
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.status === 'running'" link type="warning" size="small" :icon="VideoPause" @click="change(row, 'paused')">暂停</el-button>
            <el-button v-if="row.status === 'paused'" link type="success" size="small" :icon="VideoPlay" @click="change(row, 'running')">继续</el-button>
            <el-button v-if="['running', 'paused'].includes(row.status)" link type="danger" size="small" :icon="CircleClose" @click="change(row, 'failed')">终止</el-button>
            <el-button v-if="row.status === 'failed'" link type="primary" size="small" :icon="RefreshRight" @click="retry(row)">断点重试</el-button>
            <el-button link type="info" size="small" :icon="Document">日志</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination class="mt-16" background layout="total, sizes, prev, pager, next" :page-sizes="[10, 20, 50, 100]" :total="total" v-model:current-page="query.page" v-model:page-size="query.pageSize" @change="load" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Search, VideoPause, VideoPlay, CircleClose, RefreshRight, Document } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'
import { TASK_STATUS } from '@/utils/dict'
import { getTaskList, updateTaskStatus } from '@/api/modules/task'

const loading = ref(false)
const list = ref([])
const total = ref(0)
const query = reactive({ keyword: '', status: '', page: 1, pageSize: 10 })

async function load() {
  loading.value = true
  const res = await getTaskList(query)
  list.value = res.list
  total.value = res.total
  loading.value = false
}
async function change(row, status) {
  if (status === 'failed') await ElMessageBox.confirm('确认终止该训练任务？已训练进度将保存为断点。', '终止任务', { type: 'warning' })
  await updateTaskStatus(row.id, status)
  ElMessage.success('操作成功')
  await load()  // 真实引擎下实际状态以后端为准（如继续=重新入队 pending）
}
async function retry(row) {
  await updateTaskStatus(row.id, 'running')
  ElMessage.success('已重新入队，等待引擎调度')
  await load()
}
onMounted(load)
</script>
