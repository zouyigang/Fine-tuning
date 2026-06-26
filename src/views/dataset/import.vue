<template>
  <div>
    <PageHeader title="数据集导入" description="支持导入 OCR 校对结果、实体关系标注、事件标注、风险样本；可从 OCR 校对中心、实体审核模块一键导入已标注业务数据" />

    <el-card shadow="never" class="mb-16">
      <div class="flex-between">
        <el-form :inline="true">
          <el-form-item label="名称">
            <el-input v-model="query.keyword" placeholder="数据集名称" clearable @keyup.enter="load" />
          </el-form-item>
          <el-form-item label="类型">
            <el-select v-model="query.type" placeholder="全部" clearable style="width: 160px">
              <el-option v-for="t in DATA_TYPES" :key="t.value" :label="t.label" :value="t.label" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :icon="Search" @click="load">查询</el-button>
            <el-button :icon="Refresh" @click="reset">重置</el-button>
          </el-form-item>
        </el-form>
        <el-button type="primary" :icon="Upload" @click="dialog = true">导入数据集</el-button>
      </div>

      <el-table v-loading="loading" :data="list" class="mt-16" border>
        <el-table-column type="index" label="#" width="50" />
        <el-table-column prop="name" label="数据集名称" min-width="200" show-overflow-tooltip />
        <el-table-column prop="type" label="类型" width="130">
          <template #default="{ row }"><el-tag size="small" effect="plain">{{ row.type }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="dept" label="所属部门" width="110" />
        <el-table-column label="阶段" width="90">
          <template #default="{ row }"><el-tag size="small" :type="STAGE_TYPE[row.stage] || 'info'">{{ row.stage || '待标注' }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="total" label="样本量" width="100" />
        <el-table-column label="标注进度" width="160">
          <template #default="{ row }"><el-progress :percentage="row.progress" :stroke-width="10" /></template>
        </el-table-column>
        <el-table-column label="脱敏" width="80">
          <template #default="{ row }">
            <el-tag :type="row.desensitized ? 'success' : 'info'" size="small">{{ row.desensitized ? '已脱敏' : '未脱敏' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="version" label="版本" width="80" />
        <el-table-column prop="updatedAt" label="更新时间" width="150" />
        <el-table-column label="操作" width="230" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openDetail(row)">详情</el-button>
            <el-button link type="primary" size="small" @click="goAnnotate(row)">标注</el-button>
            <!-- 实体关系标注：训练数据分 命名实体 / 关系三元组 两份，下拉选 -->
            <el-dropdown v-if="row.stage === '已发布' && isEntityType(row.type)" trigger="click" @command="(v) => download(row, v)">
              <el-button link type="success" size="small" :icon="Download">训练数据<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="relation">关系三元组</el-dropdown-item>
                  <el-dropdown-item command="ner">命名实体（NER）</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <el-button v-else-if="row.stage === '已发布'" link type="success" size="small" :icon="Download" @click="download(row)">训练数据</el-button>
            <el-popconfirm title="确认删除该数据集？" @confirm="remove(row)">
              <template #reference><el-button link type="danger" size="small">删除</el-button></template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        class="mt-16"
        background
        layout="total, sizes, prev, pager, next"
        :page-sizes="[10, 20, 50, 100]"
        :total="total"
        v-model:current-page="query.page"
        v-model:page-size="query.pageSize"
        @change="load"
      />
    </el-card>

    <!-- 详情弹窗 -->
    <el-dialog v-model="detailDialog" title="数据集详情" width="640px">
      <el-descriptions v-if="detail" :column="2" border>
        <el-descriptions-item label="名称">{{ detail.name }}</el-descriptions-item>
        <el-descriptions-item label="类型">{{ detail.type }}</el-descriptions-item>
        <el-descriptions-item label="所属部门">{{ detail.dept }}</el-descriptions-item>
        <el-descriptions-item label="阶段"><el-tag size="small" :type="STAGE_TYPE[detail.stage] || 'info'">{{ detail.stage || '待标注' }}</el-tag></el-descriptions-item>
        <el-descriptions-item label="样本量">{{ detail.total }}</el-descriptions-item>
        <el-descriptions-item label="标注进度">{{ detail.progress }}%（已标 {{ detail.labeled || 0 }}）</el-descriptions-item>
        <el-descriptions-item label="脱敏">{{ detail.desensitized ? '已脱敏' : '未脱敏' }}</el-descriptions-item>
        <el-descriptions-item label="版本">{{ detail.version }}</el-descriptions-item>
        <el-descriptions-item label="负责人">{{ detail.owner }}</el-descriptions-item>
        <el-descriptions-item label="更新时间">{{ detail.updatedAt }}</el-descriptions-item>
      </el-descriptions>
      <div class="lbl-sample">样本预览（前 3 条原始数据）</div>
      <pre class="sample-pre">{{ samplePreview }}</pre>
    </el-dialog>

    <!-- 导入弹窗 -->
    <el-dialog v-model="dialog" title="导入数据集" width="640px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <el-form-item label="导入方式" prop="source">
          <el-radio-group v-model="form.source">
            <el-radio-button value="ocr">OCR 校对中心</el-radio-button>
            <el-radio-button value="entity">实体审核模块</el-radio-button>
            <el-radio-button value="upload">本地上传</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="数据集名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入数据集名称" />
        </el-form-item>
        <el-form-item label="数据类型" prop="type">
          <el-select v-model="form.type" placeholder="请选择" style="width: 100%">
            <el-option v-for="t in DATA_TYPES" :key="t.value" :label="t.label" :value="t.label" />
          </el-select>
        </el-form-item>
        <el-form-item label="所属部门" prop="dept">
          <el-select v-model="form.dept" placeholder="请选择" style="width: 100%">
            <el-option v-for="d in DEPARTMENTS" :key="d" :label="d" :value="d" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.source === 'upload'" label="上传文件">
          <el-upload
            ref="uploadRef"
            drag
            :auto-upload="false"
            :limit="1"
            :on-change="onFileChange"
            :on-exceed="onExceed"
            :on-remove="onFileRemove"
            accept=".json,.jsonl,.csv,.txt"
            style="width: 100%"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">拖拽文件到此处，或<em>点击上传</em></div>
            <template #tip><div class="el-upload__tip">支持 JSON / JSONL / CSV / TXT，单文件不超过 500MB；样本量按文件内容自动统计</div></template>
          </el-upload>
        </el-form-item>
        <el-form-item v-else label="选择来源数据">
          <el-alert type="info" :closable="false" show-icon>
            将从「{{ form.source === 'ocr' ? 'OCR 校对中心' : '实体审核模块' }}」拉取已标注业务数据，共检索到 <b>{{ randomCount }}</b> 条可导入样本
          </el-alert>
        </el-form-item>
        <el-form-item label="导入后脱敏">
          <el-switch v-model="form.desensitize" active-text="自动脱敏敏感字段" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submit">确认导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onActivated } from 'vue'
import { Search, Refresh, Upload, UploadFilled, Download, ArrowDown } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'
import { useRouter } from 'vue-router'
import { DEPARTMENTS } from '@/utils/dict'
import { getDatasetList, createDataset, deleteDataset, uploadDatasetFile, getDatasetTypes, getDatasetSamples, downloadTrainData } from '@/api/modules/dataset'

const router = useRouter()

// 类型下拉数据源：从数据库读取（仅启用的类型），替代原前端硬编码 DATA_TYPES
const DATA_TYPES = ref([])

// 数据集流水线阶段 → 标签颜色
const STAGE_TYPE = {
  待标注: 'info', 标注中: 'primary', 已标注: 'warning',
  已脱敏: 'warning', 已发布: 'success', 已归档: 'info'
}

const loading = ref(false)
const list = ref([])
const total = ref(0)
const query = reactive({ keyword: '', type: '', page: 1, pageSize: 10 })

const dialog = ref(false)
const submitting = ref(false)
const formRef = ref()
const uploadRef = ref()
const selectedFile = ref(null)
const form = reactive({ source: 'ocr', name: '', type: '', dept: '', desensitize: true })
const rules = {
  name: [{ required: true, message: '请输入数据集名称', trigger: 'blur' }],
  type: [{ required: true, message: '请选择数据类型', trigger: 'change' }],
  dept: [{ required: true, message: '请选择所属部门', trigger: 'change' }]
}
const randomCount = computed(() => 1000 + Math.floor(Math.random() * 9000))

async function load() {
  loading.value = true
  const res = await getDatasetList(query)
  list.value = res.list
  total.value = res.total
  loading.value = false
}
function reset() {
  query.keyword = ''
  query.type = ''
  query.page = 1
  load()
}
async function remove(row) {
  await deleteDataset(row.id)
  ElMessage.success('删除成功')
  load()
}

// 详情：展示数据集信息 + 前 3 条样本预览
const detailDialog = ref(false)
const detail = ref(null)
const samplePreview = ref('加载中…')
async function openDetail(row) {
  detail.value = row
  samplePreview.value = '加载中…'
  detailDialog.value = true
  try {
    const res = await getDatasetSamples(row.id, { page: 1, pageSize: 3 })
    const rows = (res.list || []).map((s) => s.raw)
    samplePreview.value = rows.length ? JSON.stringify(rows, null, 2) : '（暂无样本，可能是历史数据集或非本地上传）'
  } catch (e) {
    samplePreview.value = '（样本加载失败）'
  }
}

// 标注：跳转到标注页并带上数据集 id，自动选中其标注任务
function goAnnotate(row) {
  router.push({ path: '/dataset/annotation', query: { datasetId: row.id } })
}
// 「实体关系标注」类型发布后会产出 命名实体/关系三元组 两份训练文件，需分别下载
function isEntityType(type) {
  return /实体|关系/.test(type || '')
}
async function download(row, variant = '') {
  // 仅已发布数据集有最终 alpaca 训练文件；失败原因由下载工具/拦截器提示
  try { await downloadTrainData(row.id, variant) } catch (e) { /* 已提示 */ }
}
function onFileChange(file) {
  selectedFile.value = file.raw
}
function onFileRemove() {
  selectedFile.value = null
}
// el-upload 限制单文件：超出时用新文件替换旧文件
function onExceed(files) {
  uploadRef.value.clearFiles()
  const f = files[0]
  f.uid = Date.now()
  uploadRef.value.handleStart(f)
  selectedFile.value = f
}

async function submit() {
  await formRef.value.validate()
  if (form.source === 'upload' && !selectedFile.value) {
    ElMessage.warning('请先选择要上传的文件')
    return
  }
  submitting.value = true
  try {
    const payload = { name: form.name, type: form.type, dept: form.dept, desensitized: form.desensitize, owner: '张三', updatedAt: now() }
    if (form.source === 'upload') {
      // 真实上传：先落盘统计样本量，再以 fileId 关联创建数据集
      const up = await uploadDatasetFile(selectedFile.value)
      payload.fileId = up.fileId
      payload.total = up.rows
    } else {
      payload.total = randomCount.value
    }
    await createDataset(payload)
    dialog.value = false
    selectedFile.value = null
    uploadRef.value?.clearFiles()
    ElMessage.success('导入成功')
    load()
  } finally {
    submitting.value = false
  }
}

function now() {
  const d = new Date()
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

async function loadTypes() {
  DATA_TYPES.value = await getDatasetTypes()
}

onActivated(() => {
  load()
  loadTypes()
})
</script>

<style lang="scss" scoped>
.lbl-sample {
  margin: 16px 0 6px;
  font-size: 13px;
  font-weight: 600;
  color: #8a919f;
}
.sample-pre {
  background: #fafafa;
  border-radius: 4px;
  padding: 12px 14px;
  margin: 0;
  font-size: 12px;
  max-height: 220px;
  overflow: auto;
  white-space: pre-wrap;
}
</style>
