<template>
  <div>
    <PageHeader title="模型对话对比" description="手动选择基座模型或任意微调版本进行对话，左右并排直观比较微调前后的效果差异">
      <template #extra>
        <el-popover placement="bottom-end" :width="320" trigger="click">
          <template #reference>
            <el-button :icon="'Cpu'">已加载 {{ loaded.length }} 个模型</el-button>
          </template>
          <div v-if="!loaded.length" class="empty-loaded">暂无常驻模型，发送对话后会按需加载</div>
          <div v-for="w in loaded" :key="w.key" class="loaded-row">
            <span class="loaded-name" :title="w.label">{{ w.label }}</span>
            <el-button size="small" text type="danger" @click="unload(w.key)">卸载</el-button>
          </div>
        </el-popover>
      </template>
    </PageHeader>

    <el-card shadow="never" class="mb-16">
      <div class="ctrl-bar">
        <div class="ctrl-item">
          <span class="ctrl-label">模型 A</span>
          <el-select v-model="modelA" filterable placeholder="选择模型" style="width: 280px">
            <el-option v-for="m in models" :key="m.id" :label="m.label" :value="m.id" />
          </el-select>
        </div>
        <div class="ctrl-item">
          <span class="ctrl-label">模型 B</span>
          <el-select v-model="modelB" filterable clearable placeholder="（可选，留空为单模型）" style="width: 280px">
            <el-option v-for="m in models" :key="m.id" :label="m.label" :value="m.id" />
          </el-select>
        </div>
        <el-divider direction="vertical" />
        <div class="ctrl-item">
          <span class="ctrl-label">最大生成</span>
          <el-input-number v-model="maxTokens" :min="32" :max="4096" :step="64" size="small" controls-position="right" style="width: 110px" />
        </div>
        <div class="ctrl-item">
          <span class="ctrl-label">温度</span>
          <el-slider v-model="temperature" :min="0" :max="1.5" :step="0.1" style="width: 120px" />
        </div>
        <el-button :icon="'Delete'" @click="clearChat" :disabled="!turns.length">清空对话</el-button>
      </div>
    </el-card>

    <el-row :gutter="16">
      <el-col :md="modelB ? 12 : 24">
        <ChatPanel :title="labelOf(modelA)" :turns="turns" side="a" />
      </el-col>
      <el-col :md="12" v-if="modelB">
        <ChatPanel :title="labelOf(modelB)" :turns="turns" side="b" />
      </el-col>
    </el-row>

    <el-card shadow="never" class="mt-16 send-card">
      <el-input v-model="systemPrompt" placeholder="（可选）系统提示词 / System Prompt" size="small" class="mb-8" />
      <div class="send-row">
        <el-input
          v-model="input"
          type="textarea"
          :rows="2"
          resize="none"
          placeholder="输入消息，Ctrl+Enter 发送"
          @keydown.ctrl.enter.prevent="send"
        />
        <el-button type="primary" :icon="'Promotion'" :loading="busy" :disabled="!canSend" @click="send">发送</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onActivated, h } from 'vue'
import { ElMessage } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'
import { getInferModels, inferChat, getLoadedModels, unloadModel } from '@/api/modules/inference'

// 轻量子组件：渲染单侧对话气泡（同文件内联，避免新增文件）
const ChatPanel = {
  props: { title: String, turns: Array, side: String },
  setup(props) {
    return () => h('div', { class: 'el-card is-never-shadow chat-card' }, [
      h('div', { class: 'el-card__header chat-head' }, props.title || '未选择模型'),
      h('div', { class: 'el-card__body chat-body' },
        props.turns.length
          ? props.turns.map((t, i) => h('div', { key: i, class: 'turn' }, [
              h('div', { class: 'bubble user' }, t.user),
              h('div', { class: 'bubble bot' }, renderReply(t[props.side]))
            ]))
          : h('div', { class: 'chat-empty' }, '发送消息后在此显示回复')
      )
    ])
  }
}
function renderReply(cell) {
  if (!cell) return '—'
  if (cell.loading) return h('span', { class: 'loading-txt' }, '生成中…')
  if (cell.error) return h('span', { class: 'err-txt' }, cell.error)
  return h('div', {}, [
    h('div', { class: 'reply-text' }, cell.reply || '（空回复）'),
    cell.elapsed != null ? h('div', { class: 'reply-meta' }, `耗时 ${cell.elapsed}s`) : null
  ])
}

const models = ref([])
const loaded = ref([])
const modelA = ref('')
const modelB = ref('')
const maxTokens = ref(512)
const temperature = ref(0.7)
const systemPrompt = ref('')
const input = ref('')
const busy = ref(false)
const turns = reactive([])

const canSend = computed(() => modelA.value && input.value.trim() && !busy.value)

function labelOf(id) {
  return models.value.find((m) => m.id === id)?.label || ''
}

async function loadModels() {
  models.value = await getInferModels()
  if (!modelA.value && models.value.length) {
    const base = models.value.find((m) => m.kind === 'base')
    modelA.value = (base || models.value[0]).id
  }
  if (!modelB.value) {
    const ft = models.value.find((m) => m.kind === 'finetuned')
    if (ft) modelB.value = ft.id
  }
  await refreshLoaded()
}

async function refreshLoaded() {
  try { loaded.value = await getLoadedModels() } catch { /* ignore */ }
}

function buildMessages(side, userText) {
  const msgs = []
  if (systemPrompt.value.trim()) msgs.push({ role: 'system', content: systemPrompt.value.trim() })
  for (const t of turns) {
    msgs.push({ role: 'user', content: t.user })
    const cell = t[side]
    if (cell && cell.reply && !cell.error) msgs.push({ role: 'assistant', content: cell.reply })
  }
  msgs.push({ role: 'user', content: userText })
  return msgs
}

async function callSide(side, modelId, userText, cell) {
  if (!modelId) { cell.loading = false; cell.reply = ''; return }
  try {
    const res = await inferChat({
      modelId,
      messages: buildMessages(side, userText),
      maxTokens: maxTokens.value,
      temperature: temperature.value
    })
    cell.reply = res.reply
    cell.elapsed = res.elapsed
  } catch (e) {
    cell.error = e?.message || '推理失败'
  } finally {
    cell.loading = false
  }
}

async function send() {
  if (!canSend.value) return
  const userText = input.value.trim()
  const turn = reactive({
    user: userText,
    a: { loading: true, reply: '', error: '', elapsed: null },
    b: modelB.value ? { loading: true, reply: '', error: '', elapsed: null } : null
  })
  turns.push(turn)
  input.value = ''
  busy.value = true
  const jobs = [callSide('a', modelA.value, userText, turn.a)]
  if (modelB.value) jobs.push(callSide('b', modelB.value, userText, turn.b))
  await Promise.allSettled(jobs)
  busy.value = false
  refreshLoaded()
}

function clearChat() {
  turns.splice(0, turns.length)
}

async function unload(key) {
  await unloadModel(key)
  ElMessage.success('已卸载，显存已释放')
  refreshLoaded()
}

onActivated(loadModels)
</script>

<style lang="scss" scoped>
.ctrl-bar { display: flex; align-items: center; flex-wrap: wrap; gap: 16px; }
.ctrl-item { display: flex; align-items: center; gap: 8px; }
.ctrl-label { font-size: 13px; color: #606266; white-space: nowrap; }
.send-card { position: sticky; bottom: 0; z-index: 5; }
.send-row { display: flex; gap: 12px; align-items: stretch; }
.send-row .el-button { height: auto; }
.mb-8 { margin-bottom: 8px; }
.mt-16 { margin-top: 16px; }
.empty-loaded { color: #909399; font-size: 13px; padding: 4px 0; }
.loaded-row { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 4px 0; }
.loaded-name { font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>

<style lang="scss">
.chat-card { margin-bottom: 16px; }
.chat-head { font-weight: 600; color: #2f54eb; }
.chat-body { height: 440px; overflow-y: auto; background: #fafafa; }
.chat-empty { color: #c0c4cc; text-align: center; padding-top: 180px; }
.turn { margin-bottom: 16px; }
.bubble { padding: 8px 12px; border-radius: 8px; font-size: 14px; line-height: 1.6; white-space: pre-wrap; word-break: break-word; }
.bubble.user { background: #e6f0ff; color: #1d39c4; margin-bottom: 6px; }
.bubble.bot { background: #fff; border: 1px solid #ebeef5; }
.reply-text { white-space: pre-wrap; }
.reply-meta { margin-top: 6px; font-size: 12px; color: #909399; }
.loading-txt { color: #909399; }
.err-txt { color: #f5222d; }
</style>
