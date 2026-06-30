<template>
  <div>
    <PageHeader title="训练日志管理" description="完整记录训练过程日志，支持按级别筛选、关键字搜索，并提供日志下载，便于问题排查与模型调优" />

    <el-card shadow="never">
      <div class="flex-between mb-16">
        <el-form :inline="true">
          <el-form-item label="任务">
            <el-select v-model="taskId" style="width: 260px" filterable placeholder="选择任务" @change="onTaskChange">
              <el-option v-for="t in tasks" :key="t.id" :label="`#${t.id} ${t.name}`" :value="t.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="级别">
            <el-select v-model="query.level" placeholder="全部" clearable style="width: 120px" @change="load">
              <el-option v-for="l in ['DEBUG', 'INFO', 'WARN', 'ERROR']" :key="l" :label="l" :value="l" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-input v-model="query.keyword" placeholder="搜索日志内容" :prefix-icon="Search" clearable @input="load" />
          </el-form-item>
        </el-form>
        <div>
          <el-switch v-model="autoScroll" active-text="自动滚动" class="mr-12" />
          <el-button :icon="Download" @click="download">下载日志</el-button>
        </div>
      </div>

      <div ref="logBox" class="log-console">
        <div v-for="log in logs" :key="log.id" class="log-line">
          <span class="log-time">{{ log.time }}</span>
          <span class="log-level" :class="log.level.toLowerCase()">{{ log.level }}</span>
          <span class="log-msg">{{ log.msg }}</span>
        </div>
        <div v-if="!logs.length" class="empty">暂无日志</div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, watch, onActivated, onDeactivated, onUnmounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { Search, Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'
import { getTaskLogs, downloadTaskLogs, getTaskList } from '@/api/modules/task'

const route = useRoute()
const taskId = ref(null)
const tasks = ref([])
const logs = ref([])
const query = reactive({ level: '', keyword: '' })
const autoScroll = ref(true)
const logBox = ref()

// 运行中/排队中的任务才需要实时轮询日志（已完成的日志不再变化）；
// 轮询与「自动滚动」联动：开=实时跟随(拉新+滚底)，关=冻结当前视图便于阅读。
let timer = null
const isLive = () => ['running', 'pending'].includes(tasks.value.find((t) => t.id === taskId.value)?.status)
function startPolling() {
  stopPolling()
  if (isLive() && autoScroll.value) timer = setInterval(load, 3000)
}
function stopPolling() {
  if (timer) { clearInterval(timer); timer = null }
}
watch(autoScroll, startPolling)   // 切换「自动滚动」即开始/停止实时跟随

async function load() {
  // 传 taskId 精确查该任务日志；为空时后端回退当前运行任务
  logs.value = await getTaskLogs({ ...query, taskId: taskId.value || undefined })
  if (autoScroll.value) nextTick(() => logBox.value && (logBox.value.scrollTop = logBox.value.scrollHeight))
}

// 切换任务：重载日志并按新任务状态决定是否继续轮询
async function onTaskChange() {
  await load()
  startPolling()
}
async function download() {
  if (!taskId.value) return ElMessage.warning('请先选择任务')
  try {
    const name = await downloadTaskLogs(taskId.value, { level: query.level, keyword: query.keyword })
    ElMessage.success(`日志已下载（${name}）`)
  } catch (e) {
    /* 错误提示已在 downloadFile 内统一处理 */
  }
}
onActivated(async () => {
  const res = await getTaskList({ page: 1, pageSize: 100 })
  tasks.value = res.list || []
  // 优先用路由带入的 taskId（来自「任务启停与重试」的日志按钮）；否则默认第一个任务
  const routed = Number(route.query.taskId)
  if (routed && tasks.value.some((t) => t.id === routed)) {
    taskId.value = routed
  } else if (!taskId.value && tasks.value.length) {
    taskId.value = tasks.value[0].id
  }
  await load()
  startPolling()           // 运行中任务自动每 3s 拉新日志，无需手动刷新
})
onDeactivated(stopPolling)  // 切走标签页即停止轮询
onUnmounted(stopPolling)
</script>

<style lang="scss" scoped>
.mr-12 { margin-right: 12px; }
.log-console {
  background: #1e1e1e;
  border-radius: 4px;
  padding: 12px 16px;
  height: 500px;
  overflow: auto;
  font-family: Consolas, 'Courier New', monospace;
  font-size: 12.5px;
  line-height: 1.9;
}
.log-line { white-space: nowrap; }
.log-time { color: #6a9955; margin-right: 10px; }
.log-level {
  display: inline-block;
  width: 50px;
  font-weight: 700;
  margin-right: 10px;
  &.info { color: #4fc3f7; }
  &.warn { color: #ffca28; }
  &.error { color: #ef5350; }
  &.debug { color: #9e9e9e; }
}
.log-msg { color: #d4d4d4; }
.empty { color: #777; text-align: center; padding: 40px; }
</style>
