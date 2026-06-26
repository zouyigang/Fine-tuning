<template>
  <div>
    <PageHeader title="数据转换规则" description="维护「业务原始数据集 → alpaca 指令样本」的转换规则：按数据集类型注入指令、识别输入/输出字段。真实微调引擎对非标准数据集自动套用这些规则。">
      <template #extra><el-button type="primary" :icon="Plus" @click="openDialog()">新建规则</el-button></template>
    </PageHeader>

    <el-alert class="mb-16" type="info" :closable="false" show-icon
      title="规则如何生效：每条规则归属一个数据集「适用类型」；导入该类型的数据集训练时，按优先级从小到大依次尝试其规则，第一条字段都取到的生效；该类型无规则或都不适用时走内置通用兜底（问答键/两字段对）。类型在「数据集类型管理」维护。" />

    <el-card shadow="never">
      <el-table v-loading="loading" :data="list" border>
        <el-table-column prop="priority" label="优先级" width="80" align="center" />
        <el-table-column prop="name" label="规则名称" min-width="150" show-overflow-tooltip />
        <el-table-column label="适用类型" width="150">
          <template #default="{ row }">
            <el-tag v-if="row.datasetTypeLabel" size="small" type="primary">{{ row.datasetTypeLabel }}</el-tag>
            <el-tag v-else size="small" type="info">未关联</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="instruction" label="注入指令" min-width="240" show-overflow-tooltip />
        <el-table-column label="输出格式" width="90" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="row.outputFormat === 'json' ? 'warning' : 'info'">{{ row.outputFormat }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-switch :model-value="row.enabled" @change="(v) => toggle(row, v)" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="170" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openDialog(row)">编辑</el-button>
            <el-button link type="success" size="small" @click="openPreview(row)">试转换</el-button>
            <el-button link type="danger" size="small" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新建 / 编辑 -->
    <el-dialog v-model="dialog" :title="form.id ? '编辑转换规则' : '新建转换规则'" width="640px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="规则名称" prop="name"><el-input v-model="form.name" placeholder="如：OCR 校对" /></el-form-item>
        <el-form-item label="适用类型" prop="datasetTypeId">
          <el-select v-model="form.datasetTypeId" placeholder="选择该规则适用的数据集类型" style="width: 100%">
            <el-option v-for="t in datasetTypes" :key="t.id" :label="t.label" :value="t.id" />
          </el-select>
          <div class="tip">选项来自「数据集类型管理」中启用的类型。同一类型可建多条规则，用优先级排序。</div>
        </el-form-item>
        <el-form-item label="优先级" prop="priority">
          <el-input-number v-model="form.priority" :min="0" :max="999" />
          <div class="tip">数值越小越先尝试；同类型多条规则用它排序（如关系优先于实体）。</div>
        </el-form-item>
        <el-form-item label="注入指令" prop="instruction">
          <el-input v-model="form.instruction" type="textarea" :rows="2" placeholder="告诉模型要做什么，如：请校对并改正下面 OCR 文本中的错别字…" />
        </el-form-item>
        <el-form-item label="输入字段别名">
          <el-select v-model="form.inputAliases" multiple filterable allow-create default-first-option
            placeholder="回车添加，如 text 原文 ocr_text" style="width: 100%" :reserve-keyword="false" />
          <div class="tip">从原始数据按顺序取第一个存在的字段作为 input；留空表示无输入（指令式）。</div>
        </el-form-item>
        <el-form-item label="输出字段别名" prop="outputAliases">
          <el-select v-model="form.outputAliases" multiple filterable allow-create default-first-option
            placeholder="回车添加，如 corrected 校对后 target" style="width: 100%" :reserve-keyword="false" />
          <div class="tip">取到的字段作为 output（期望答案）；取不到则该规则对此行不适用。</div>
        </el-form-item>
        <el-form-item label="输出格式" prop="outputFormat">
          <el-radio-group v-model="form.outputFormat">
            <el-radio value="text">纯文本</el-radio>
            <el-radio value="json">JSON（把结构字段序列化为 JSON 字符串）</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="启用"><el-switch v-model="form.enabled" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialog = false">取消</el-button><el-button type="primary" @click="save">保存</el-button></template>
    </el-dialog>

    <!-- 试转换 -->
    <el-dialog v-model="previewDialog" title="试转换预览" width="720px">
      <el-form label-width="100px">
        <el-form-item label="数据集类型">
          <el-input v-model="pv.dsType" placeholder="如 OCR 校对结果（决定命中哪些规则）" />
        </el-form-item>
        <el-form-item label="原始样本">
          <el-input v-model="pv.sample" type="textarea" :rows="6"
            placeholder='粘贴一条或多条原始数据，支持 JSON 对象 / 数组 / JSONL，如：&#10;{"原文":"2O23年","校对后":"2023年"}' />
        </el-form-item>
      </el-form>
      <el-button type="primary" :icon="MagicStick" :loading="pv.loading" @click="runPreview">转换</el-button>
      <el-alert v-if="pv.error" class="mt-16" type="error" :closable="false" show-icon :title="pv.error" />
      <template v-if="pv.result.length">
        <div class="pv-note">{{ pv.note }}</div>
        <el-table :data="pv.result" border size="small" class="mt-16">
          <el-table-column type="index" label="#" width="50" />
          <el-table-column prop="instruction" label="instruction" min-width="180" show-overflow-tooltip />
          <el-table-column prop="input" label="input" min-width="120" show-overflow-tooltip />
          <el-table-column prop="output" label="output" min-width="160" show-overflow-tooltip />
        </el-table>
      </template>
      <el-empty v-else-if="pv.done && !pv.error" description="未识别出可训练字段，请检查字段别名是否匹配" :image-size="80" />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onActivated } from 'vue'
import { Plus, MagicStick } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'
import {
  getConvertRules, saveConvertRule, setConvertRuleStatus, deleteConvertRule, previewConvert
} from '@/api/modules/config'
import { getDatasetTypes } from '@/api/modules/dataset'

const loading = ref(false)
const list = ref([])
const datasetTypes = ref([])   // 「适用类型」下拉数据源（仅启用类型）

async function load() {
  loading.value = true
  try {
    list.value = await getConvertRules()
  } finally {
    loading.value = false
  }
}
async function loadTypes() {
  datasetTypes.value = await getDatasetTypes()  // 默认仅启用项
}

const dialog = ref(false)
const formRef = ref()
const DEFAULT_FORM = {
  id: null, name: '', datasetTypeId: null, priority: 10, instruction: '',
  inputAliases: [], outputAliases: [], outputFormat: 'text', enabled: true
}
const form = reactive({ ...DEFAULT_FORM })
const rules = {
  name: [{ required: true, message: '请输入规则名称', trigger: 'blur' }],
  datasetTypeId: [{ required: true, message: '请选择适用类型', trigger: 'change' }],
  outputAliases: [{ required: true, type: 'array', min: 1, message: '至少配置一个输出字段别名', trigger: 'change' }],
  outputFormat: [{ required: true, message: '请选择输出格式', trigger: 'change' }]
}

function openDialog(row) {
  Object.assign(form, DEFAULT_FORM, row ? JSON.parse(JSON.stringify(row)) : {})
  dialog.value = true
}
async function save() {
  await formRef.value.validate()
  await saveConvertRule({ ...form })
  dialog.value = false
  ElMessage.success('保存成功')
  load()
}
async function toggle(row, val) {
  await setConvertRuleStatus(row.id, val)
  row.enabled = val
  ElMessage.success(val ? '规则已启用' : '规则已停用')
}
async function remove(row) {
  await ElMessageBox.confirm(`确认删除规则「${row.name}」？`, '删除规则', { type: 'warning' })
  await deleteConvertRule(row.id)
  ElMessage.success('规则已删除')
  load()
}

// 试转换
const previewDialog = ref(false)
const pv = reactive({ dsType: '', sample: '', result: [], note: '', error: '', loading: false, done: false })
function openPreview(row) {
  pv.dsType = row.datasetTypeLabel || ''
  pv.sample = ''
  pv.result = []
  pv.note = ''
  pv.error = ''
  pv.done = false
  previewDialog.value = true
}
async function runPreview() {
  pv.loading = true
  try {
    const res = await previewConvert(pv.sample, pv.dsType)
    pv.result = res.samples || []
    pv.note = res.note || ''
    pv.error = res.error || ''
    pv.done = true
  } finally {
    pv.loading = false
  }
}

// 用 onActivated（而非顶层调用/onMounted）：被 keep-alive 缓存的页面每次重新进入都刷新
onActivated(() => {
  load()
  loadTypes()
})
</script>

<style lang="scss" scoped>
.tip {
  font-size: 12px;
  color: #a3a8b3;
  line-height: 1.5;
  margin-top: 2px;
}
.kw-tag {
  margin: 0 4px 2px 0;
}
.pv-note {
  margin-top: 16px;
  font-size: 13px;
  color: #52c41a;
}
.mb-16 {
  margin-bottom: 16px;
}
.mt-16 {
  margin-top: 16px;
}
</style>
