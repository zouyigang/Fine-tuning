<template>
  <div>
    <PageHeader title="多类型数据标注" description="逐条标注导入的数据集样本：OCR 文本校对、实体/关系三元组提供专用工具，其他类型提供结构化字段编辑；标注进度自动汇总，满额后数据集进入待脱敏" />

    <el-row :gutter="16">
      <el-col :md="12">
        <el-card shadow="never">
          <template #header><span>标注任务</span></template>
          <el-table v-loading="loading" :data="list" border highlight-current-row @row-click="selectTask">
            <el-table-column prop="title" label="任务名称" min-width="78" show-overflow-tooltip />
            <el-table-column prop="type" label="类型" width="120">
              <template #default="{ row }"><el-tag size="small" effect="plain">{{ row.type }}</el-tag></template>
            </el-table-column>
            <el-table-column label="进度" width="138">
              <template #default="{ row }"><el-progress :percentage="row.done" :stroke-width="10" /></template>
            </el-table-column>
            <el-table-column label="状态" width="86">
              <template #default="{ row }">
                <el-tag size="small" :type="row.status === '已完成' ? 'success' : row.status === '待审核' ? 'warning' : 'primary'">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="复核 / 操作" width="130" align="center">
              <template #default="{ row }">
                <el-button v-if="row.status === '待审核'" link type="success" size="small" @click.stop="review(row, true)">通过</el-button>
                <el-button v-if="row.status === '待审核'" link type="warning" size="small" @click.stop="review(row, false)">退回</el-button>
                <el-button link type="danger" size="small" @click.stop="removeTask(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination class="mt-16" background layout="total, prev, pager, next" :total="total" v-model:current-page="query.page" v-model:page-size="query.pageSize" @change="loadTasks" />
        </el-card>
      </el-col>

      <el-col :md="12">
        <el-card shadow="never">
          <template #header>
            <div class="flex-between">
              <span>标注工作台{{ active ? ` · ${active.title}` : '' }}</span>
              <span v-if="active && total2" class="text-muted">第 {{ cursor }} / {{ total2 }} 条</span>
            </div>
          </template>

          <el-empty v-if="!active" description="点击左侧任务开始标注" :image-size="90" />
          <el-empty v-else-if="!sample" :description="sampleEmptyText" :image-size="90" />

          <template v-else>
            <el-alert v-if="locked" type="info" :closable="false" show-icon class="mb-12"
              title="该任务已复核完成，标注已锁定，不可再修改（数据集已进入脱敏/发布阶段）。" />
            <div :class="{ 'locked-editor': locked }">
            <!-- OCR 文本校对 -->
            <div v-if="mode === 'ocr'">
              <div class="lbl">原文（OCR 识别）</div>
              <div class="raw-text">{{ rawText }}</div>
              <div class="lbl">校对后（修正错别字/漏字/格式）</div>
              <el-input v-model="corrected" type="textarea" :rows="5" placeholder="在此输入校对后的正确文本" />
            </div>

            <!-- 实体 / 关系三元组 -->
            <div v-else-if="mode === 'entity'">
              <div class="lbl">文本（选中文字后点「标为实体」）</div>
              <div class="raw-text" @mouseup="captureSelection">{{ rawText }}</div>

              <div class="lbl">实体</div>
              <div class="row-form">
                <el-input v-model="entForm.text" placeholder="实体文本（可在上方选词自动填入）" style="width: 220px" />
                <el-select v-model="entForm.type" placeholder="类型" style="width: 110px">
                  <el-option v-for="t in ENTITY_TYPES" :key="t" :label="t" :value="t" />
                </el-select>
                <el-button :icon="Plus" @click="addEntity">标为实体</el-button>
              </div>
              <div class="ent-tags">
                <el-tag v-for="(e, i) in entities" :key="i" closable size="small" class="ent-tag" @close="entities.splice(i, 1)">
                  {{ e.text }}<span class="ent-type">/{{ e.type }}</span>
                </el-tag>
                <span v-if="!entities.length" class="text-muted">暂无实体</span>
              </div>

              <div class="lbl">关系三元组（主体 — 关系 — 客体）</div>
              <div class="row-form">
                <el-select v-model="relForm.head" placeholder="主体" style="width: 130px">
                  <el-option v-for="(e, i) in entities" :key="i" :label="e.text" :value="e.text" />
                </el-select>
                <el-select v-model="relForm.relation" placeholder="关系" filterable allow-create style="width: 130px">
                  <el-option v-for="r in REL_TYPES" :key="r" :label="r" :value="r" />
                </el-select>
                <el-select v-model="relForm.tail" placeholder="客体" style="width: 130px">
                  <el-option v-for="(e, i) in entities" :key="i" :label="e.text" :value="e.text" />
                </el-select>
                <el-button :icon="Plus" @click="addRelation">添加</el-button>
              </div>
              <el-table v-if="relations.length" :data="relations" size="small" border class="mt-8">
                <el-table-column prop="head" label="主体" />
                <el-table-column prop="relation" label="关系" width="120">
                  <template #default="{ row }"><el-tag size="small" type="warning">{{ row.relation }}</el-tag></template>
                </el-table-column>
                <el-table-column prop="tail" label="客体" />
                <el-table-column label="" width="50">
                  <template #default="{ $index }"><el-button link type="danger" size="small" @click="relations.splice($index, 1)">删</el-button></template>
                </el-table-column>
              </el-table>
              <div v-else class="text-muted" style="margin-top: 6px">暂无三元组</div>
            </div>

            <!-- 事件要素 -->
            <div v-else-if="mode === 'event'">
              <div class="lbl">文本（选中文字自动填入下方聚焦的输入框：触发词 / 论元文本）</div>
              <div class="raw-text" @mouseup="captureEventSelection">{{ rawText }}</div>
              <div class="lbl">事件（类型 + 触发词 + 论元角色）</div>
              <div class="row-form">
                <el-select v-model="evtForm.type" placeholder="事件类型" filterable allow-create style="width: 150px">
                  <el-option v-for="t in EVENT_TYPES" :key="t" :label="t" :value="t" />
                </el-select>
                <el-input v-model="evtForm.trigger" placeholder="触发词（选中上方文字自动填入）" style="width: 200px" @focus="evtSelTarget = { type: 'trigger' }" />
                <el-button :icon="Plus" @click="addEvent">添加事件</el-button>
              </div>
              <div v-for="(ev, ei) in events" :key="ei" class="evt-card">
                <div class="evt-head">
                  <el-tag size="small" type="danger">{{ ev.type }}</el-tag>
                  <span class="evt-trigger">触发词：{{ ev.trigger || '—' }}</span>
                  <el-button link type="danger" size="small" @click="events.splice(ei, 1)">删除事件</el-button>
                </div>
                <div class="row-form">
                  <el-select v-model="ev._role" placeholder="论元角色" style="width: 120px">
                    <el-option v-for="r in ARG_ROLES" :key="r" :label="r" :value="r" />
                  </el-select>
                  <el-input v-model="ev._text" placeholder="论元文本（选中上方文字自动填入）" style="width: 200px" @focus="evtSelTarget = { type: 'arg', ev }" />
                  <el-button size="small" :icon="Plus" @click="addArg(ev)">加论元</el-button>
                </div>
                <div class="ent-tags">
                  <el-tag v-for="(a, ai) in ev.arguments" :key="ai" closable size="small" class="ent-tag" @close="ev.arguments.splice(ai, 1)">
                    {{ a.role }}：{{ a.text }}
                  </el-tag>
                </div>
              </div>
              <div v-if="!events.length" class="text-muted" style="margin-top: 6px">暂无事件</div>
            </div>

            <!-- 风险样本分类 -->
            <div v-else-if="mode === 'risk'">
              <div class="lbl">内容</div>
              <div class="raw-text">{{ rawText }}</div>
              <div class="lbl">风险标签（单选/可自定义）</div>
              <el-select v-model="riskLabel" placeholder="选择或输入风险类型" filterable allow-create style="width: 260px">
                <el-option v-for="r in RISK_LABELS" :key="r" :label="r" :value="r" />
              </el-select>
            </div>

            <!-- 路径分析：轨迹只读 + 研判结论 -->
            <div v-else-if="mode === 'path'">
              <div class="lbl">时空轨迹（时间-地点序列）</div>
              <div class="raw-text">{{ rawText }}</div>
              <div class="lbl">路径研判结论（还原活动路径、关键停留点、逃逸/接应方向等）</div>
              <el-input v-model="pathResult" type="textarea" :rows="5" placeholder="根据轨迹点还原嫌疑人活动路径并给出研判结论" />
            </div>

            <!-- 其他类型：结构化字段编辑 -->
            <div v-else>
              <div class="lbl">原始数据</div>
              <pre class="raw-json">{{ prettyRaw }}</pre>
              <div class="lbl">标注结果（JSON：事件/风险等结构化字段）</div>
              <el-input v-model="labeledText" type="textarea" :rows="6" placeholder='如：{"events": [...]} 或 {"label": "电信诈骗"}' />
              <div v-if="jsonError" class="json-err">JSON 格式错误：{{ jsonError }}</div>
            </div>
            </div>

            <div class="mt-16 flex-between">
              <el-button :icon="ArrowLeft" :disabled="cursor <= 1" @click="go(-1)">上一条</el-button>
              <el-tag v-if="sample.status === '已标注'" type="success" size="small">已标注</el-tag>
              <el-tag v-else type="info" size="small">待标注</el-tag>
              <el-button type="success" :icon="Check" :loading="saving" :disabled="locked" @click="saveAndNext">保存并下一条</el-button>
              <el-button :icon="ArrowRight" :disabled="cursor >= total2" @click="go(1)">下一条</el-button>
            </div>
          </template>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onActivated } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowLeft, ArrowRight, Check, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'
import { getAnnotationTasks, getDatasetSamples, saveSampleLabel, reviewAnnotation, deleteAnnotationTask } from '@/api/modules/dataset'

const route = useRoute()

const ENTITY_TYPES = ['人名', '地点', '机构', '时间', '金额', '案由', '物品', '组织']
const REL_TYPES = ['作案地', '转账', '涉嫌', '隶属', '联系', '所有', '参与']
const EVENT_TYPES = ['盗窃', '诈骗', '故意伤害', '聚众斗殴', '走私', '贩毒', '非法集资', '寻衅滋事']
const ARG_ROLES = ['时间', '地点', '主体', '对象', '工具', '金额', '后果']
const RISK_LABELS = ['电信诈骗', '涉黑涉恶', '毒品犯罪', '赌博', '非法集资', '暴恐', '低风险', '无风险']

const loading = ref(false)
const list = ref([])
const total = ref(0)
const query = reactive({ page: 1, pageSize: 10 })

async function loadTasks() {
  loading.value = true
  try {
    const res = await getAnnotationTasks(query)
    list.value = res.list
    total.value = res.total
  } finally {
    loading.value = false
  }
}

// ---- 当前任务 / 当前样本 ----
const active = ref(null)
const cursor = ref(1)
const total2 = ref(0)
const sample = ref(null)
const saving = ref(false)

// 标注模式：按任务类型选编辑器
const mode = computed(() => {
  const t = active.value?.type || ''
  if (/ocr|校对/i.test(t)) return 'ocr'
  if (/实体|关系/i.test(t)) return 'entity'
  if (/事件/i.test(t)) return 'event'
  if (/风险/i.test(t)) return 'risk'
  if (/路径|轨迹|path/i.test(t)) return 'path'
  return 'generic'
})

// 已复核通过（已完成）的任务：标注锁定，不可再改（数据集已进入下游脱敏/发布）
const locked = computed(() => active.value?.status === '已完成')

const RAW_KEYS = ['原文', 'text', 'ocr_text', 'ocr', 'raw', 'source', '识别文本', 'content', 'sentence', '句子', '轨迹', 'trajectory', '时空轨迹']
const rawText = computed(() => {
  const r = sample.value?.raw || {}
  for (const k of RAW_KEYS) if (r[k] != null && String(r[k]).trim()) return String(r[k])
  for (const v of Object.values(r)) if (typeof v === 'string' && v.trim()) return v
  return JSON.stringify(r)
})
const prettyRaw = computed(() => JSON.stringify(sample.value?.raw || {}, null, 2))

// OCR
const corrected = ref('')
// 实体
const entities = ref([])
const entForm = reactive({ text: '', type: '人名' })
const relations = ref([])
const relForm = reactive({ head: '', relation: '', tail: '' })
// 事件
const events = ref([])
const evtForm = reactive({ type: '盗窃', trigger: '' })
// 风险
const riskLabel = ref('')
// 路径分析
const pathResult = ref('')
// 通用
const labeledText = ref('')
const jsonError = ref('')
const sampleEmptyText = ref('该任务暂无逐样本数据')

async function selectTask(row) {
  if (!row?.datasetId) {
    active.value = row
    sample.value = null
    total2.value = 0
    sampleEmptyText.value = '该任务无逐样本数据（可能是历史演示任务）'
    return
  }
  active.value = row
  cursor.value = 1
  await loadSample()
}

async function loadSample() {
  if (!active.value?.datasetId) return
  const res = await getDatasetSamples(active.value.datasetId, { page: cursor.value, pageSize: 1 })
  total2.value = res.total
  sample.value = (res.list && res.list[0]) || null
  jsonError.value = ''
  if (!sample.value) return
  const lab = sample.value.labeled || {}
  if (mode.value === 'ocr') {
    corrected.value = lab['校对后'] ?? rawText.value
  } else if (mode.value === 'entity') {
    entities.value = Array.isArray(lab.entities) ? lab.entities.map((e) => ({ ...e })) : []
    relations.value = (Array.isArray(lab.relations) ? lab.relations : []).map(toRelObj)
    entForm.text = ''
    relForm.head = relForm.relation = relForm.tail = ''
  } else if (mode.value === 'event') {
    events.value = (Array.isArray(lab.events) ? lab.events : []).map((e) => ({
      type: e.type, trigger: e.trigger, arguments: (e.arguments || []).map((a) => ({ ...a })), _role: '', _text: ''
    }))
    evtForm.trigger = ''
  } else if (mode.value === 'risk') {
    riskLabel.value = lab.label || ''
  } else if (mode.value === 'path') {
    pathResult.value = lab['路径分析'] ?? ''
  } else {
    labeledText.value = JSON.stringify(sample.value.labeled || sample.value.raw || {}, null, 2)
  }
}

function toRelObj(r) {
  if (Array.isArray(r)) return { head: r[0], relation: r[1], tail: r[2] }
  return { head: r.head, relation: r.relation, tail: r.tail }
}

function captureSelection() {
  const s = (window.getSelection?.().toString() || '').trim()
  if (s) entForm.text = s
}

// 事件标注：划词自动填入「当前聚焦的输入框」（触发词 / 某事件的论元文本）
// 默认目标为新事件的触发词；点进某个论元文本框后，划词即填入该论元。
const evtSelTarget = ref({ type: 'trigger' })
function captureEventSelection() {
  const s = (window.getSelection?.().toString() || '').trim()
  if (!s) return
  const t = evtSelTarget.value
  if (t?.type === 'arg' && t.ev) t.ev._text = s
  else evtForm.trigger = s
}
function addEntity() {
  if (!entForm.text.trim()) return ElMessage.warning('请先选词或输入实体文本')
  entities.value.push({ text: entForm.text.trim(), type: entForm.type })
  entForm.text = ''
}
function addRelation() {
  if (!relForm.head || !relForm.relation || !relForm.tail) return ElMessage.warning('请补全 主体/关系/客体')
  relations.value.push({ head: relForm.head, relation: relForm.relation, tail: relForm.tail })
  relForm.head = relForm.relation = relForm.tail = ''
}
function addEvent() {
  if (!evtForm.type) return ElMessage.warning('请选择事件类型')
  events.value.push({ type: evtForm.type, trigger: evtForm.trigger.trim(), arguments: [], _role: '', _text: '' })
  evtForm.trigger = ''
}
function addArg(ev) {
  if (!ev._role || !ev._text.trim()) return ElMessage.warning('请补全 论元角色/文本')
  ev.arguments.push({ role: ev._role, text: ev._text.trim() })
  ev._role = ''
  ev._text = ''
}

function go(delta) {
  const next = cursor.value + delta
  if (next < 1 || next > total2.value) return
  cursor.value = next
  loadSample()
}

async function saveAndNext() {
  let labeled
  if (mode.value === 'ocr') {
    labeled = { 原文: rawText.value, 校对后: corrected.value }
  } else if (mode.value === 'entity') {
    labeled = {
      text: rawText.value,
      entities: entities.value,
      relations: relations.value.map((r) => [r.head, r.relation, r.tail])
    }
  } else if (mode.value === 'event') {
    labeled = {
      text: rawText.value,
      events: events.value.map((e) => ({ type: e.type, trigger: e.trigger, arguments: e.arguments }))
    }
  } else if (mode.value === 'risk') {
    if (!riskLabel.value) { jsonError.value = ''; return ElMessage.warning('请选择风险标签') }
    labeled = { text: rawText.value, label: riskLabel.value }
  } else if (mode.value === 'path') {
    if (!pathResult.value.trim()) { jsonError.value = ''; return ElMessage.warning('请填写路径研判结论') }
    labeled = { 轨迹: rawText.value, 路径分析: pathResult.value.trim() }
  } else {
    try {
      labeled = JSON.parse(labeledText.value)
      jsonError.value = ''
    } catch (e) {
      jsonError.value = e.message
      return
    }
  }
  saving.value = true
  try {
    await saveSampleLabel(sample.value.id, labeled)
    ElMessage.success('已保存')
    await loadTasks()
    const fresh = list.value.find((t) => t.id === active.value.id)
    if (fresh) active.value = fresh
    if (cursor.value < total2.value) cursor.value += 1
    await loadSample()
  } finally {
    saving.value = false
  }
}

async function review(row, approved) {
  await reviewAnnotation(row.id, approved)
  ElMessage.success(approved ? '复核通过，数据集可进入脱敏' : '已退回重标')
  await loadTasks()
}

async function removeTask(row) {
  await ElMessageBox.confirm(
    `确认删除标注任务「${row.title}」？仅移除该标注任务，数据集及其样本不受影响。`,
    '删除标注任务', { type: 'warning' }
  )
  await deleteAnnotationTask(row.id)
  ElMessage.success('标注任务已删除')
  // 删除的是当前正在标注的任务时，清空右侧工作台
  if (active.value && active.value.id === row.id) {
    active.value = null
    sample.value = null
  }
  await loadTasks()
}

onActivated(async () => {
  await loadTasks()
  // 从导入页「标注」跳转而来：自动选中该数据集的标注任务
  const dsId = Number(route.query.datasetId)
  if (dsId) {
    const hit = list.value.find((t) => t.datasetId === dsId)
    if (hit) selectTask(hit)
  }
})
</script>

<style lang="scss" scoped>
.mb-12 {
  margin-bottom: 12px;
}
// 任务已复核完成：编辑区整体置灰且不可交互（保存按钮另行禁用，后端也会拒绝）
.locked-editor {
  pointer-events: none;
  opacity: 0.6;
}
.lbl {
  font-size: 13px;
  color: #8a919f;
  font-weight: 600;
  margin: 12px 0 6px;
}
.raw-text {
  background: #fafafa;
  border-radius: 4px;
  padding: 12px 14px;
  line-height: 1.9;
  font-size: 14px;
  color: #1f2329;
  user-select: text;
}
.raw-json {
  background: #fafafa;
  border-radius: 4px;
  padding: 12px 14px;
  margin: 0;
  font-size: 12px;
  max-height: 160px;
  overflow: auto;
  white-space: pre-wrap;
}
.row-form {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.ent-tags {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.ent-tag .ent-type {
  opacity: 0.7;
  margin-left: 2px;
}
.evt-card {
  border: 1px solid #f0f0f0;
  border-radius: 4px;
  padding: 10px 12px;
  margin-top: 8px;
}
.evt-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}
.evt-trigger {
  font-size: 13px;
  color: #1f2329;
  flex: 1;
}
.json-err {
  color: #f5222d;
  font-size: 12px;
  margin-top: 6px;
}
.text-muted {
  color: #8a919f;
  font-size: 13px;
}
.mt-8 {
  margin-top: 8px;
}
</style>
