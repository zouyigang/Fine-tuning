<template>
  <div>
    <PageHeader title="微调任务创建" description="选择业务模型类型、基础模型与训练数据集，配置超参数后创建微调任务" />

    <el-card shadow="never">
      <el-steps :active="step" finish-status="success" align-center class="mb-16">
        <el-step title="选择业务模型" />
        <el-step title="选择基础模型与数据" />
        <el-step title="超参配置" />
        <el-step title="确认提交" />
      </el-steps>

      <div class="step-body">
        <!-- step 0 -->
        <div v-show="step === 0">
          <el-radio-group v-model="form.modelType" class="model-grid">
            <el-radio v-for="m in MODEL_TYPES" :key="m.value" :value="m.value" border class="model-item">
              <el-icon><component :is="iconOf(m.value)" /></el-icon> {{ m.label }}
            </el-radio>
          </el-radio-group>
        </div>

        <!-- step 1 -->
        <el-form v-show="step === 1" label-width="120px" style="max-width: 600px; margin: 0 auto">
          <el-form-item label="任务名称">
            <el-input v-model="form.name" placeholder="请输入任务名称" />
          </el-form-item>
          <el-form-item label="基础模型">
            <el-select v-model="form.baseModel" placeholder="请选择基础模型" style="width: 100%">
              <el-option v-for="b in BASE_MODELS" :key="b.value" :label="b.label" :value="b.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="训练数据集">
            <el-select v-model="form.dataset" placeholder="请选择已发布数据集" style="width: 100%" filterable
              :no-data-text="`暂无与「${labelOf(MODEL_TYPES, form.modelType)}」匹配的已发布数据集，请先在「数据集管理」完成 标注→脱敏→发布`">
              <el-option v-for="d in filteredDatasets" :key="d.id" :label="`${d.name}（${(d.total || 0).toLocaleString()} 条）`" :value="String(d.id)" />
            </el-select>
            <div class="ds-tip">仅列出与业务模型「{{ labelOf(MODEL_TYPES, form.modelType) }}」匹配类型、且已发布的数据集</div>
          </el-form-item>
          <el-form-item label="微调方式">
            <el-radio-group v-model="form.method">
              <el-radio value="lora">LoRA</el-radio>
              <el-radio value="qlora">QLoRA</el-radio>
              <el-radio value="full">全参微调</el-radio>
            </el-radio-group>
          </el-form-item>
        </el-form>

        <!-- step 2 -->
        <el-form v-show="step === 2" label-width="140px" style="max-width: 600px; margin: 0 auto">
          <el-form-item label="超参模板">
            <el-select v-model="form.template" placeholder="可选择模板快速填充" style="width: 100%" clearable>
              <el-option label="审讯笔录实体识别模板" value="t1" />
              <el-option label="OCR 校对微调模板" value="t2" />
            </el-select>
          </el-form-item>
          <el-form-item label="学习率"><el-input-number v-model="form.lr" :step="0.00001" :precision="5" controls-position="right" /></el-form-item>
          <el-form-item label="批次大小"><el-select v-model="form.batchSize" style="width: 160px"><el-option v-for="b in [8, 16, 32, 64]" :key="b" :label="b" :value="b" /></el-select></el-form-item>
          <el-form-item label="训练轮数"><el-input-number v-model="form.epochs" :min="1" :max="50" /></el-form-item>
          <el-form-item label="优化器"><el-select v-model="form.optimizer" style="width: 160px"><el-option label="AdamW" value="AdamW" /><el-option label="Adam" value="Adam" /><el-option label="SGD" value="SGD" /></el-select></el-form-item>
        </el-form>

        <!-- step 3 -->
        <el-descriptions v-show="step === 3" :column="2" border style="max-width: 760px; margin: 0 auto">
          <el-descriptions-item label="任务名称">{{ form.name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="业务模型">{{ labelOf(MODEL_TYPES, form.modelType) }}</el-descriptions-item>
          <el-descriptions-item label="基础模型">{{ labelOf(BASE_MODELS, form.baseModel) }}</el-descriptions-item>
          <el-descriptions-item label="数据集">{{ datasetLabel }}</el-descriptions-item>
          <el-descriptions-item label="微调方式">{{ form.method }}</el-descriptions-item>
          <el-descriptions-item label="学习率">{{ form.lr }}</el-descriptions-item>
          <el-descriptions-item label="批次大小 / 轮数">{{ form.batchSize }} / {{ form.epochs }}</el-descriptions-item>
          <el-descriptions-item label="优化器">{{ form.optimizer }}</el-descriptions-item>
        </el-descriptions>
      </div>

      <div class="step-footer">
        <el-button v-if="step > 0" @click="step--">上一步</el-button>
        <el-button v-if="step < 3" type="primary" @click="next">下一步</el-button>
        <el-button v-else type="success" :loading="submitting" @click="submit">提交并启动任务</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onActivated } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'
import { MODEL_TYPES, BASE_MODELS, dictLabel } from '@/utils/dict'
import { createTask } from '@/api/modules/task'
import { getDatasetList, getDatasetTypes } from '@/api/modules/dataset'

const router = useRouter()
const step = ref(0)
const submitting = ref(false)
const form = reactive({
  modelType: 'ner', name: '', baseModel: '', dataset: '', method: 'lora',
  template: '', lr: 0.00002, batchSize: 16, epochs: 8, optimizer: 'AdamW'
})

// 业务模型类型 → 数据集类型(value)：实体识别/关系抽取共用「实体关系标注」
const MODEL_TO_DS_TYPE = { ocr: 'ocr', ner: 'entity', relation: 'entity', event: 'event', risk: 'risk', path: 'path' }

// 训练数据集只列「已发布」（已脱敏并转成训练样本，闭环要求）
const datasets = ref([])
const dsTypes = ref([]) // [{ value, label }] 数据集类型字典，用于把模型类型映射到 dataset.type 标签
onActivated(async () => {
  const res = await getDatasetList({ stage: '已发布', pageSize: 100 })
  datasets.value = res.list || []
  dsTypes.value = await getDatasetTypes()
})

// 当前业务模型类型对应的数据集类型标签（dataset.type 存的是 label）
const expectedDsLabel = computed(() => {
  const v = MODEL_TO_DS_TYPE[form.modelType]
  return dsTypes.value.find((t) => t.value === v)?.label || ''
})
// 仅列出与所选业务模型类型匹配的已发布数据集
const filteredDatasets = computed(() => {
  const lbl = expectedDsLabel.value
  return lbl ? datasets.value.filter((d) => d.type === lbl) : datasets.value
})
// 切换业务模型类型后，若已选数据集不再匹配则清空，避免提交到错配数据集
watch(() => form.modelType, () => {
  if (form.dataset && !filteredDatasets.value.some((d) => String(d.id) === String(form.dataset))) {
    form.dataset = ''
  }
})

const datasetLabel = computed(() => {
  const d = datasets.value.find((x) => String(x.id) === String(form.dataset))
  return d ? d.name : form.dataset || '-'
})

const labelOf = dictLabel
const iconMap = { ocr: 'Document', ner: 'CollectionTag', relation: 'Share', event: 'Calendar', risk: 'WarnTriangleFilled', path: 'Guide' }
const iconOf = (v) => iconMap[v] || 'Cpu'

function next() {
  if (step.value === 1 && !form.name) return ElMessage.warning('请输入任务名称')
  if (step.value === 1 && (!form.baseModel || !form.dataset)) return ElMessage.warning('请选择基础模型与数据集')
  step.value++
}
async function submit() {
  submitting.value = true
  await createTask({
    name: form.name,
    modelType: labelOf(MODEL_TYPES, form.modelType),
    baseModel: labelOf(BASE_MODELS, form.baseModel),
    dataset: form.dataset,
    priority: '中',
    gpu: '2 × A100',
    epoch: `0/${form.epochs}`,
    creator: '张三',
    createdAt: '2026-06-09 10:30',
    duration: '0m',
    // 真实引擎：透传微调方式与超参（替代过去被丢弃的配置）
    method: form.method,
    hyperparams: { lr: form.lr, batchSize: form.batchSize, epochs: form.epochs, optimizer: form.optimizer }
  })
  submitting.value = false
  ElMessage.success('任务已创建并进入训练队列')
  resetWizard()   // 复位向导，避免 keep-alive 下次进入仍停在「确认提交」并带旧数据
  router.push('/task/monitor')
}

// 复位到第 1 步并清空表单（保留默认超参）
function resetWizard() {
  step.value = 0
  Object.assign(form, {
    modelType: 'ner', name: '', baseModel: '', dataset: '', method: 'lora',
    template: '', lr: 0.00002, batchSize: 16, epochs: 8, optimizer: 'AdamW'
  })
}
</script>

<style lang="scss" scoped>
.step-body {
  min-height: 280px;
  padding: 24px 0;
}
.ds-tip {
  font-size: 12px;
  color: #a3a8b3;
  margin-top: 4px;
}
.model-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  max-width: 720px;
  margin: 0 auto;
}
.model-item {
  height: 64px;
  margin: 0 !important;
  display: flex;
  align-items: center;
  justify-content: center;
}
.step-footer {
  text-align: center;
  border-top: 1px solid #f0f0f0;
  padding-top: 20px;
}
</style>
