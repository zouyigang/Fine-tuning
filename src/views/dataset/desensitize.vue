<template>
  <div>
    <PageHeader title="数据集脱敏处理" description="自动脱敏身份证号、手机号、银行卡号、涉案人员隐私等敏感信息，支持自定义脱敏规则，确保涉密数据安全" />

    <el-row :gutter="16">
      <el-col :md="14">
        <el-card shadow="never">
          <template #header>
            <div class="flex-between">
              <span>脱敏规则配置</span>
              <el-button type="primary" size="small" :icon="Plus" @click="openRuleDialog">新增规则</el-button>
            </div>
          </template>
          <el-table :data="pagedRules" border>
            <el-table-column prop="field" label="敏感字段" width="110" />
            <el-table-column label="掩码类型" width="110">
              <template #default="{ row }"><el-tag size="small" effect="plain">{{ maskLabel(row.maskType) }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="rule" label="脱敏规则" min-width="150" show-overflow-tooltip />
            <el-table-column prop="sample" label="脱敏示例" min-width="160">
              <template #default="{ row }"><span class="mono">{{ row.sample }}</span></template>
            </el-table-column>
            <el-table-column label="启用" width="70">
              <template #default="{ row }"><el-switch v-model="row.enabled" @change="(val) => toggleRule(row, val)" /></template>
            </el-table-column>
            <el-table-column label="操作" width="70">
              <template #default="{ row }">
                <el-button link type="danger" size="small" :icon="Delete" @click="removeRule(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination class="mt-16" background layout="total, sizes, prev, pager, next" :page-sizes="[10, 20, 50, 100]" :total="rules.length" v-model:current-page="page" v-model:page-size="pageSize" />
        </el-card>
      </el-col>

      <el-col :md="10">
        <el-card shadow="never">
          <template #header>脱敏执行</template>
          <el-form label-width="90px">
            <el-form-item label="目标数据集">
              <el-select v-model="targetDataset" placeholder="请选择待脱敏数据集" style="width: 100%" filterable @change="onTargetChange">
                <el-option v-for="d in datasets" :key="d.id" :label="d.name" :value="d.id" />
              </el-select>
              <div class="hint">仅列出已完成标注（待脱敏）的数据集</div>
            </el-form-item>
            <el-form-item label="应用规则">
              <el-tag v-for="r in rules.filter((x) => x.enabled)" :key="r.id" size="small" class="tag-gap">{{ r.field }}</el-tag>
            </el-form-item>
            <el-form-item v-if="desensitized" label="数据集切分">
              <div class="split-row">
                <span class="split-tag">训练</span>
                <el-input-number v-model="split.train" :min="0" :max="100" :step="5" size="small" controls-position="right" style="width: 92px" />
                <span class="split-tag">验证</span>
                <el-input-number v-model="split.val" :min="0" :max="100" :step="5" size="small" controls-position="right" style="width: 92px" />
                <span class="split-tag">测试</span>
                <el-input-number v-model="split.test" :min="0" :max="100" :step="5" size="small" controls-position="right" style="width: 92px" />
                <span :class="['split-sum', splitSum === 100 ? '' : 'split-bad']">合计 {{ splitSum }}%</span>
              </div>
              <div class="hint">训练集用于训练、验证集产出验证曲线、测试集供模型效果评估；三者比例须合计 100%。</div>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :icon="Lock" :loading="running" :disabled="!targetDataset || desensitized" @click="run">
                {{ desensitized ? '已脱敏' : '开始脱敏' }}
              </el-button>
              <el-button v-if="desensitized" type="success" :icon="Upload" :loading="publishing" :disabled="splitSum !== 100" @click="publish">
                发布为可训练
              </el-button>
            </el-form-item>
            <el-alert v-if="published" type="success" :closable="false" show-icon
              title="已发布：数据已转成最终 alpaca 训练样本并落地，训练时直读、无需再转换；可在「微调任务创建」中选用">
              <template #default>
                <div>已发布：数据已转成最终 alpaca 训练样本并落地，训练时直读、无需再转换。</div>
                <el-button class="mt-8" size="small" type="primary" link :icon="Download" @click="downloadTrainData">
                  下载最终训练数据（alpaca jsonl）
                </el-button>
              </template>
            </el-alert>
          </el-form>

          <el-divider>脱敏对比预览</el-divider>
          <div class="hint" style="margin-bottom: 8px">用当前启用规则实时试脱敏；可编辑原文，或选目标数据集逐条预览真实样本。</div>
          <div v-if="previewTotal > 0" class="prev-nav">
            <el-button size="small" :disabled="previewCursor <= 1" @click="stepPreview(-1)">上一条</el-button>
            <span class="text-muted">样本 {{ previewCursor }} / {{ previewTotal }}</span>
            <el-button size="small" :disabled="previewCursor >= previewTotal" @click="stepPreview(1)">下一条</el-button>
          </div>
          <div class="preview">
            <div class="preview-col">
              <div class="preview-title">原文（可编辑）</div>
              <el-input v-model="previewText" type="textarea" :rows="3" @input="onPreviewInput" placeholder="输入或粘贴含敏感信息的文本试脱敏" />
            </div>
            <div class="preview-col masked">
              <div class="preview-title">脱敏后</div>
              <p>{{ previewMasked || '（输入文本后自动显示脱敏结果）' }}</p>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="ruleDialog" title="新增脱敏规则" width="460px">
      <el-form ref="ruleFormRef" :model="ruleForm" :rules="ruleRules" label-width="90px">
        <el-form-item label="敏感字段" prop="field">
          <el-input v-model="ruleForm.field" placeholder="如：身份证号 / 姓名（也用于匹配数据字段名）" />
        </el-form-item>
        <el-form-item label="掩码类型" prop="maskType">
          <el-select v-model="ruleForm.maskType" style="width: 100%">
            <el-option v-for="m in MASK_TYPES" :key="m.value" :label="m.label" :value="m.value" />
          </el-select>
          <div class="hint">{{ MASK_TYPES.find((m) => m.value === ruleForm.maskType)?.desc }}</div>
        </el-form-item>
        <el-form-item v-if="ruleForm.maskType === 'custom'" label="正则">
          <el-input v-model="ruleForm.pattern" placeholder="匹配到的内容替换为 ***，留空则整字段值替换" />
        </el-form-item>
      </el-form>
      <template #footer><el-button @click="ruleDialog = false">取消</el-button><el-button type="primary" @click="saveRule">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onActivated } from 'vue'
import { Plus, Lock, Upload, Download, Delete } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'
import { downloadFile } from '@/utils/download'
import {
  getDesensitizeRules, createDesensitizeRule, toggleDesensitizeRule, deleteDesensitizeRule,
  runDesensitize, publishDataset, getDatasetList, previewDesensitize, getDatasetSamples
} from '@/api/modules/dataset'

const MASK_TYPES = [
  { value: 'idcard', label: '身份证', desc: '18 位身份证号，保留前 6 后 4' },
  { value: 'phone', label: '手机号', desc: '11 位手机号，保留前 3 后 4' },
  { value: 'bankcard', label: '银行卡', desc: '12-19 位卡号，仅保留后 4 位' },
  { value: 'name', label: '姓名', desc: '按字段名匹配，保留姓氏' },
  { value: 'email', label: '邮箱', desc: '保留首字符与域名' },
  { value: 'custom', label: '自定义正则', desc: '按字段名匹配，正则命中处替换为 ***' }
]
const maskLabel = (v) => MASK_TYPES.find((m) => m.value === v)?.label || v || '自定义'

const rules = ref([])
const datasets = ref([])
const targetDataset = ref('')
const running = ref(false)
const desensitized = ref(false)   // 当前目标是否已完成脱敏（显示发布按钮）
const publishing = ref(false)
const published = ref(false)
const publishedId = ref(null)     // 已发布数据集 id（供下载训练数据）

// 发布时的训练/验证/测试切分比例（默认 80/10/10，可调，须合计 100）
const split = ref({ train: 80, val: 10, test: 10 })
const splitSum = computed(() => (split.value.train || 0) + (split.value.val || 0) + (split.value.test || 0))

// 脱敏对比预览（真实：调后端用当前启用规则试脱敏）
const previewText = ref('犯罪嫌疑人张伟，身份证110101199003074567，手机13812348888，名下银行卡6217000812345678存在异常交易。')
const previewMasked = ref('')
let previewTimer = null
function onPreviewInput() {
  clearTimeout(previewTimer)
  previewTimer = setTimeout(runPreview, 400)
}
async function runPreview() {
  const res = await previewDesensitize(previewText.value)
  previewMasked.value = res.masked
}

// 前端分页（本地数据），与各列表页分页控件保持统一，默认每页 10 条
const page = ref(1)
const pageSize = ref(10)
const pagedRules = computed(() => rules.value.slice((page.value - 1) * pageSize.value, page.value * pageSize.value))

async function loadDatasets() {
  // 仅列出已完成标注（待脱敏）的数据集
  const res = await getDatasetList({ stage: '已标注', pageSize: 100 })
  datasets.value = res.list || []
}
onActivated(async () => {
  rules.value = await getDesensitizeRules()
  await loadDatasets()
  runPreview()
})

// 选目标数据集：重置发布态 + 逐条预览该数据集样本
const previewCursor = ref(0)   // 0=手动文本；>=1 绑定到样本序号
const previewTotal = ref(0)
async function onTargetChange() {
  published.value = false
  previewCursor.value = 0
  previewTotal.value = 0
  if (!targetDataset.value) return
  previewCursor.value = 1
  await loadPreviewSample()
}
// 从样本字段对象中挑出最具代表性的正文字符串：
// 优先标注后的正文键（OCR 的「校对后」、实体/事件/风险的 text 等），否则取首个非空字符串。
function pickText(obj) {
  if (!obj || typeof obj !== 'object') return ''
  const order = ['校对后', 'corrected', 'text', '文本', '内容', 'content', '原文']
  for (const key of order) {
    const hit = Object.keys(obj).find((k) => k.toLowerCase() === key.toLowerCase())
    if (hit && typeof obj[hit] === 'string' && obj[hit].trim()) return obj[hit]
  }
  const s = Object.values(obj).find((v) => typeof v === 'string' && v.trim())
  return s || ''
}
async function loadPreviewSample() {
  try {
    const res = await getDatasetSamples(targetDataset.value, { page: previewCursor.value, pageSize: 1 })
    previewTotal.value = res.total || 0
    const sample = res.list?.[0] || {}
    // 与 run_desensitize 一致：脱敏作用于 labeled（标注/校对后的内容），无标注才回退 raw
    const src = sample.labeled && Object.keys(sample.labeled).length ? sample.labeled : (sample.raw || {})
    previewText.value = pickText(src) || JSON.stringify(src)
    runPreview()
  } catch (e) { /* 取样失败保留当前文本 */ }
}
function stepPreview(d) {
  const n = previewCursor.value + d
  if (n < 1 || n > previewTotal.value) return
  previewCursor.value = n
  loadPreviewSample()
}

// 新增规则弹窗
const ruleDialog = ref(false)
const ruleFormRef = ref()
const ruleForm = ref({ field: '', maskType: 'idcard', pattern: '' })
const ruleRules = {
  field: [{ required: true, message: '请输入敏感字段名称', trigger: 'blur' }],
  maskType: [{ required: true, message: '请选择掩码类型', trigger: 'change' }]
}
function openRuleDialog() {
  ruleForm.value = { field: '', maskType: 'idcard', pattern: '' }
  ruleDialog.value = true
}
async function saveRule() {
  await ruleFormRef.value.validate()
  const desc = MASK_TYPES.find((m) => m.value === ruleForm.value.maskType)?.desc || '自定义掩码'
  const rule = await createDesensitizeRule({
    field: ruleForm.value.field, rule: desc, sample: '****', enabled: true,
    maskType: ruleForm.value.maskType, pattern: ruleForm.value.pattern || null
  })
  rules.value.push(rule)
  ruleDialog.value = false
  ElMessage.success('已新增规则')
}

async function toggleRule(row, val) {
  try {
    await toggleDesensitizeRule(row.id, val)
  } catch (e) {
    row.enabled = !val // 失败回滚开关状态
  }
}

async function removeRule(row) {
  await ElMessageBox.confirm(`确认删除脱敏规则「${row.field}」？`, '删除规则', { type: 'warning' })
  await deleteDesensitizeRule(row.id)
  rules.value = rules.value.filter((r) => r.id !== row.id)
  // 删除末页最后一条后回退页码，避免停留在空页
  const maxPage = Math.max(1, Math.ceil(rules.value.length / pageSize.value))
  if (page.value > maxPage) page.value = maxPage
  ElMessage.success('规则已删除')
}

async function run() {
  running.value = true
  try {
    const res = await runDesensitize(targetDataset.value)
    desensitized.value = true
    ElMessage.success(`脱敏完成，共处理 ${(res.count || 0).toLocaleString()} 条样本`)
  } finally {
    running.value = false
  }
}

async function publish() {
  if (splitSum.value !== 100) {
    ElMessage.warning('训练/验证/测试比例须合计 100%')
    return
  }
  publishing.value = true
  try {
    await publishDataset(targetDataset.value, {
      trainRatio: split.value.train, valRatio: split.value.val, testRatio: split.value.test
    })
    publishedId.value = targetDataset.value
    published.value = true
    desensitized.value = false
    targetDataset.value = ''
    ElMessage.success('已发布为可训练数据集')
    await loadDatasets()
  } finally {
    publishing.value = false
  }
}

async function downloadTrainData() {
  await downloadFile(`/dataset/${publishedId.value}/train-data/download`, { fallback: 'train-data.jsonl' })
}
</script>

<style lang="scss" scoped>
.mono {
  font-family: Consolas, monospace;
  color: #d4380d;
}
.hint {
  font-size: 12px;
  color: #a3a8b3;
  margin-top: 2px;
}
.split-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.split-tag { font-size: 13px; color: #606266; }
.split-sum { font-size: 13px; color: #67c23a; margin-left: 4px; }
.split-bad { color: #f56c6c; font-weight: 600; }
.prev-nav {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
  .text-muted {
    font-size: 13px;
    color: #8a919f;
  }
}
.mt-8 {
  margin-top: 8px;
}
.tag-gap {
  margin: 0 6px 6px 0;
}
.preview {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.preview-col {
  padding: 12px;
  border-radius: 4px;
  background: #fafafa;
  font-size: 13px;
  line-height: 1.7;
  &.masked {
    background: #f6ffed;
    border: 1px solid #b7eb8f;
  }
  .preview-title {
    font-weight: 600;
    margin-bottom: 6px;
    color: #8a919f;
  }
}
</style>
