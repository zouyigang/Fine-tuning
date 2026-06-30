<template>
  <div>
    <PageHeader title="任务启停与重试" description="支持暂停、继续、终止训练任务；训练失败自动保存断点，支持从断点重试，避免重复训练" />

    <el-card shadow="never">
      <div class="flex-between mb-16">
        <el-radio-group v-model="query.status" @change="load">
          <el-radio-button value="">全部</el-radio-button>
          <el-radio-button value="draft">未启动</el-radio-button>
          <el-radio-button value="running">训练中</el-radio-button>
          <el-radio-button value="paused">已暂停</el-radio-button>
          <el-radio-button value="failed">失败</el-radio-button>
          <el-radio-button value="success">已完成</el-radio-button>
        </el-radio-group>
        <el-input v-model="query.keyword" placeholder="搜索任务" :prefix-icon="Search" style="width: 220px" @keyup.enter="load" clearable />
      </div>

      <el-table v-loading="loading" :data="list" border>
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="hp-detail">
              <el-descriptions :column="4" size="small" border>
                <el-descriptions-item label="微调方式">{{ (row.method || 'lora').toUpperCase() }}</el-descriptions-item>
                <el-descriptions-item label="学习率">{{ hp(row).lr ?? '-' }}</el-descriptions-item>
                <el-descriptions-item label="批次大小">{{ hp(row).batchSize ?? '-' }}</el-descriptions-item>
                <el-descriptions-item label="训练轮数">{{ hp(row).epochs ?? '-' }}</el-descriptions-item>
                <el-descriptions-item label="优化器">{{ hp(row).optimizer ?? '-' }}</el-descriptions-item>
                <el-descriptions-item v-if="hp(row).maxLen != null" label="最大序列长度">{{ hp(row).maxLen }}</el-descriptions-item>
                <el-descriptions-item v-if="hp(row).warmup != null" label="Warmup 比例">{{ hp(row).warmup }}</el-descriptions-item>
              </el-descriptions>
              <p v-if="!row.hyperparams" class="hp-empty">该任务未记录超参配置</p>
            </div>
          </template>
        </el-table-column>
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
            <el-button v-if="row.status === 'draft'" link type="success" size="small" :icon="VideoPlay" @click="retry(row)">启动</el-button>
            <el-button v-if="row.status === 'running'" link type="warning" size="small" :icon="VideoPause" @click="change(row, 'paused')">暂停</el-button>
            <el-button v-if="row.status === 'paused'" link type="success" size="small" :icon="VideoPlay" @click="change(row, 'running')">继续</el-button>
            <el-button v-if="['running', 'paused'].includes(row.status)" link type="danger" size="small" :icon="CircleClose" @click="change(row, 'failed')">终止</el-button>
            <el-button v-if="row.status === 'failed'" link type="primary" size="small" :icon="RefreshRight" @click="retry(row)">断点重试</el-button>
            <el-button link type="info" size="small" :icon="Document" @click="viewLogs(row)">日志</el-button>
            <el-button v-if="row.status !== 'running'" link type="danger" size="small" :icon="Delete" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination class="mt-16" background layout="total, sizes, prev, pager, next" :page-sizes="[10, 20, 50, 100]" :total="total" v-model:current-page="query.page" v-model:page-size="query.pageSize" @change="load" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onActivated } from 'vue'
import { useRouter } from 'vue-router'
import { Search, VideoPause, VideoPlay, CircleClose, RefreshRight, Document, Delete } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'
import { TASK_STATUS } from '@/utils/dict'
import { getTaskList, updateTaskStatus, deleteTask } from '@/api/modules/task'

const router = useRouter()

const loading = ref(false)
const list = ref([])
const total = ref(0)
const query = reactive({ keyword: '', status: '', page: 1, pageSize: 10 })

// 该任务的超参对象（兼容未记录的旧任务）
const hp = (row) => row.hyperparams || {}

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
// 查看日志：跳到「训练日志管理」并定位到该任务
function viewLogs(row) {
  router.push({ path: '/task/logs', query: { taskId: row.id } })
}
async function retry(row) {
  await updateTaskStatus(row.id, 'running')
  ElMessage.success('已重新入队，等待引擎调度')
  await load()
}
async function remove(row) {
  await ElMessageBox.confirm(
    `确认删除任务「${row.name}」？将一并清除其训练指标、日志与产物记录，且不可恢复。`,
    '删除任务', { type: 'warning' }
  )
  try {
    // 已产出模型版本/运行中的任务后端会拒绝并自动弹出原因
    await deleteTask(row.id)
    ElMessage.success('任务已删除')
    await load()
  } catch (e) { /* 失败原因已由响应拦截器提示 */ }
}
onActivated(load)
</script>

<style lang="scss" scoped>
.hp-detail { padding: 8px 16px; }
.hp-empty { margin: 8px 0 0; color: #909399; font-size: 13px; }
</style>
