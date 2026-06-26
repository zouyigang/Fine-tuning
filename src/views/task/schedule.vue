<template>
  <div>
    <PageHeader title="批量微调任务调度" description="支持创建批量微调任务，按优先级排队执行；可配置定时微调任务，自动在业务低峰期执行训练">
      <template #extra>
        <el-button type="primary" :icon="Plus" @click="dialog = true">新建批量任务</el-button>
      </template>
    </PageHeader>

    <el-row :gutter="16" class="mb-16">
      <el-col :xs="12" :md="6"><StatCard label="排队任务" :value="queue.length" unit="个" icon="List" bg="#2f54eb" /></el-col>
      <el-col :xs="12" :md="6"><StatCard label="并发上限" value="4" unit="个" icon="SetUp" bg="#13c2c2" /></el-col>
      <el-col :xs="12" :md="6"><StatCard label="定时任务" value="3" unit="个" icon="Timer" bg="#722ed1" /></el-col>
      <el-col :xs="12" :md="6"><StatCard label="低峰执行窗口" value="00-06" unit="时" icon="MoonNight" bg="#fa8c16" /></el-col>
    </el-row>

    <el-card shadow="never">
      <template #header>调度队列（按优先级排序，可拖动调整）</template>
      <el-table :data="pagedQueue" border row-key="id">
        <el-table-column label="顺序" width="70" align="center">
          <template #default="{ row }"><el-tag type="info" round>{{ row.order }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="name" label="任务名称" min-width="200" show-overflow-tooltip />
        <el-table-column label="优先级" width="100">
          <template #default="{ row }">
            <el-tag :type="row.priority === '高' ? 'danger' : row.priority === '中' ? 'warning' : 'info'" size="small">{{ row.priority }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }"><el-tag :type="TASK_STATUS[row.status].type" size="small">{{ TASK_STATUS[row.status].label }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="gpu" label="资源" width="110" />
        <el-table-column prop="scheduledAt" label="计划执行时间" width="150" />
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" :disabled="queue[0] === row" @click="moveUp(row)">上移</el-button>
            <el-button link type="primary" size="small" :disabled="queue[queue.length - 1] === row" @click="moveDown(row)">下移</el-button>
            <el-button link type="danger" size="small" @click="remove(row)">移除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination class="mt-16" background layout="total, sizes, prev, pager, next" :page-sizes="[10, 20, 50, 100]" :total="queue.length" v-model:current-page="page" v-model:page-size="pageSize" />
    </el-card>

    <el-dialog v-model="dialog" title="新建批量微调任务" width="600px">
      <el-form label-width="120px">
        <el-form-item label="批量任务名称"><el-input v-model="form.name" placeholder="如：6月实体模型批量优化" /></el-form-item>
        <el-form-item label="选择数据集">
          <el-select v-model="form.datasets" multiple placeholder="可多选" style="width: 100%">
            <el-option label="审讯笔录数据集-2026001" value="1" />
            <el-option label="资金流水数据集-2026002" value="2" />
            <el-option label="涉案人员数据集-2026003" value="3" />
          </el-select>
        </el-form-item>
        <el-form-item label="优先级"><el-radio-group v-model="form.priority"><el-radio value="高">高</el-radio><el-radio value="中">中</el-radio><el-radio value="低">低</el-radio></el-radio-group></el-form-item>
        <el-form-item label="执行方式">
          <el-radio-group v-model="form.runMode">
            <el-radio value="now">立即排队</el-radio>
            <el-radio value="timer">定时执行</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="form.runMode === 'timer'" label="执行时间">
          <el-time-picker v-model="form.runTime" placeholder="选择低峰执行时间" value-format="HH:mm" />
        </el-form-item>
      </el-form>
      <template #footer><el-button @click="dialog = false">取消</el-button><el-button type="primary" :loading="creating" @click="create">创建</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onActivated } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'
import StatCard from '@/components/StatCard.vue'
import { TASK_STATUS } from '@/utils/dict'
import { getScheduleQueue, createScheduleItem, removeScheduleItem, reorderSchedule } from '@/api/modules/task'

const queue = ref([])
const dialog = ref(false)
const creating = ref(false)
const form = reactive({ name: '', datasets: [], priority: '中', runMode: 'now', runTime: null })

// 前端分页（本地数据），与各列表页分页控件保持统一，默认每页 10 条
const page = ref(1)
const pageSize = ref(10)
const pagedQueue = computed(() => queue.value.slice((page.value - 1) * pageSize.value, page.value * pageSize.value))

async function load() {
  queue.value = await getScheduleQueue()
}
function reorderLocal() {
  queue.value.forEach((q, i) => (q.order = i + 1))
}
// 顺序变更后持久化到后端（按当前 id 顺序）
async function persistOrder() {
  reorderLocal()
  await reorderSchedule(queue.value.map((q) => q.id))
}
// 基于行对象（而非分页后的下标）操作，避免分页导致的错位
async function moveUp(row) {
  const i = queue.value.indexOf(row)
  if (i <= 0) return
  ;[queue.value[i - 1], queue.value[i]] = [queue.value[i], queue.value[i - 1]]
  await persistOrder()
}
async function moveDown(row) {
  const i = queue.value.indexOf(row)
  if (i < 0 || i >= queue.value.length - 1) return
  ;[queue.value[i + 1], queue.value[i]] = [queue.value[i], queue.value[i + 1]]
  await persistOrder()
}
async function remove(row) {
  await removeScheduleItem(row.id)
  ElMessage.success('已移除')
  load()
}
async function create() {
  if (!form.name) {
    ElMessage.warning('请输入批量任务名称')
    return
  }
  creating.value = true
  try {
    await createScheduleItem({
      name: form.name,
      priority: form.priority,
      scheduledAt: form.runMode === 'timer' && form.runTime ? `每日 ${form.runTime}` : '立即执行'
    })
    dialog.value = false
    form.name = ''
    form.datasets = []
    ElMessage.success('批量任务已创建')
    load()
  } finally {
    creating.value = false
  }
}
onActivated(load)
</script>
