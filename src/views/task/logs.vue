<template>
  <div>
    <PageHeader title="训练日志管理" description="完整记录训练过程日志，支持按级别筛选、关键字搜索，并提供日志下载，便于问题排查与模型调优" />

    <el-card shadow="never">
      <div class="flex-between mb-16">
        <el-form :inline="true">
          <el-form-item label="任务">
            <el-select v-model="taskId" style="width: 220px" @change="load">
              <el-option label="实体识别微调-20260608" :value="1" />
              <el-option label="OCR 识别微调-20260607" :value="2" />
            </el-select>
          </el-form-item>
          <el-form-item label="级别">
            <el-select v-model="query.level" placeholder="全部" clearable style="width: 120px" @change="load">
              <el-option v-for="l in ['INFO', 'WARN', 'ERROR', 'DEBUG']" :key="l" :label="l" :value="l" />
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
import { ref, reactive, onActivated, nextTick } from 'vue'
import { Search, Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'
import { getTaskLogs, downloadTaskLogs } from '@/api/modules/task'

const taskId = ref(1)
const logs = ref([])
const query = reactive({ level: '', keyword: '' })
const autoScroll = ref(true)
const logBox = ref()

async function load() {
  logs.value = await getTaskLogs(query)
  if (autoScroll.value) nextTick(() => logBox.value && (logBox.value.scrollTop = logBox.value.scrollHeight))
}
async function download() {
  try {
    const name = await downloadTaskLogs(taskId.value, { level: query.level, keyword: query.keyword })
    ElMessage.success(`日志已下载（${name}）`)
  } catch (e) {
    /* 错误提示已在 downloadFile 内统一处理 */
  }
}
onActivated(load)
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
