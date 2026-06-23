<template>
  <div>
    <PageHeader title="超参数可视化配置" description="可视化配置学习率、批次大小、训练轮数、优化器、正则化等超参数，并提供公安业务场景专用默认模板" />

    <el-row :gutter="16">
      <el-col :md="15">
        <el-card shadow="never">
          <template #header>
            <div class="flex-between">
              <span>超参数配置</span>
              <el-select v-model="template" placeholder="加载默认模板" size="small" style="width: 220px" @change="applyTemplate">
                <el-option label="审讯笔录实体识别模板" value="ner" />
                <el-option label="OCR 校对微调模板" value="ocr" />
                <el-option label="资金流关系抽取模板" value="relation" />
              </el-select>
            </div>
          </template>

          <div class="param-row">
            <div class="param-label">学习率 (learning rate)</div>
            <el-slider v-model="lrExp" :min="-6" :max="-3" :step="0.1" :format-tooltip="(v) => `1e${v.toFixed(1)}`" style="flex: 1" />
            <el-tag class="param-val">{{ lrText }}</el-tag>
          </div>
          <div class="param-row">
            <div class="param-label">批次大小 (batch size)</div>
            <el-radio-group v-model="form.batchSize"><el-radio-button v-for="b in [8, 16, 32, 64]" :key="b" :value="b">{{ b }}</el-radio-button></el-radio-group>
          </div>
          <div class="param-row">
            <div class="param-label">训练轮数 (epochs)</div>
            <el-slider v-model="form.epochs" :min="1" :max="30" style="flex: 1" />
            <el-tag class="param-val">{{ form.epochs }}</el-tag>
          </div>
          <div class="param-row">
            <div class="param-label">优化器 (optimizer)</div>
            <el-select v-model="form.optimizer" style="width: 200px"><el-option v-for="o in ['AdamW', 'Adam', 'SGD', 'Adafactor']" :key="o" :label="o" :value="o" /></el-select>
          </div>
          <div class="param-row">
            <div class="param-label">权重衰减 (weight decay)</div>
            <el-slider v-model="form.weightDecay" :min="0" :max="0.1" :step="0.001" style="flex: 1" />
            <el-tag class="param-val">{{ form.weightDecay }}</el-tag>
          </div>
          <div class="param-row">
            <div class="param-label">Warmup 比例</div>
            <el-slider v-model="form.warmup" :min="0" :max="0.2" :step="0.01" style="flex: 1" />
            <el-tag class="param-val">{{ form.warmup }}</el-tag>
          </div>
          <div class="param-row">
            <div class="param-label">最大序列长度</div>
            <el-select v-model="form.maxLen" style="width: 200px"><el-option v-for="l in [512, 1024, 2048, 4096]" :key="l" :label="l" :value="l" /></el-select>
          </div>
          <div class="param-row">
            <div class="param-label">梯度裁剪 / 混合精度</div>
            <el-switch v-model="form.gradClip" active-text="梯度裁剪" /><el-switch v-model="form.fp16" active-text="FP16" style="margin-left: 16px" />
          </div>

          <div class="flex" style="justify-content: flex-end; gap: 8px; margin-top: 16px">
            <el-button @click="saveAsTemplate">保存为模板</el-button>
            <el-button type="primary" @click="openApply">应用到任务</el-button>
          </div>
        </el-card>
      </el-col>

      <el-col :md="9">
        <el-card shadow="never">
          <template #header>配置预览 (JSON)</template>
          <pre class="json-preview">{{ jsonPreview }}</pre>
        </el-card>
        <el-card shadow="never" class="mt-16">
          <template #header>配置建议</template>
          <el-alert title="LoRA 微调推荐学习率 1e-4 ~ 5e-5" type="info" :closable="false" class="mb-16" />
          <el-alert title="样本量 < 1万 时建议 epochs 8~12，避免欠拟合" type="info" :closable="false" class="mb-16" />
          <el-alert title="显存紧张时开启 FP16 + 梯度累积" type="warning" :closable="false" />
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="applyDialog" title="应用超参到任务" width="480px">
      <el-form label-width="90px">
        <el-form-item label="目标任务">
          <el-select v-model="applyTaskId" placeholder="选择待训练/可修改的任务" style="width: 100%" filterable>
            <el-option v-for="t in applyTasks" :key="t.id" :label="`#${t.id} ${t.name}（${t.status}）`" :value="t.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="将写入">
          <pre class="json-preview" style="margin:0">{{ jsonPreview }}</pre>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="applyDialog = false">取消</el-button>
        <el-button type="primary" :loading="applying" :disabled="!applyTaskId" @click="doApply">应用</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'
import { saveHyperTemplate } from '@/api/modules/config'
import { getTaskList, applyHyperparams } from '@/api/modules/task'

const template = ref('')
const lrExp = ref(-4.7)
const form = reactive({ batchSize: 16, epochs: 8, optimizer: 'AdamW', weightDecay: 0.01, warmup: 0.06, maxLen: 1024, gradClip: true, fp16: true })

const lrText = computed(() => `${Math.pow(10, lrExp.value).toExponential(1)}`)
const jsonPreview = computed(() =>
  JSON.stringify({ learning_rate: lrText.value, batch_size: form.batchSize, epochs: form.epochs, optimizer: form.optimizer, weight_decay: form.weightDecay, warmup_ratio: form.warmup, max_seq_len: form.maxLen, grad_clip: form.gradClip, fp16: form.fp16 }, null, 2)
)

const presets = {
  ner: { lrExp: -4.7, batchSize: 16, epochs: 8, optimizer: 'AdamW' },
  ocr: { lrExp: -4, batchSize: 32, epochs: 5, optimizer: 'Adam' },
  relation: { lrExp: -4.5, batchSize: 8, epochs: 10, optimizer: 'AdamW' }
}
function applyTemplate(v) {
  const p = presets[v]
  if (!p) return
  lrExp.value = p.lrExp
  Object.assign(form, { batchSize: p.batchSize, epochs: p.epochs, optimizer: p.optimizer })
  ElMessage.success('已加载模板')
}
const applyDialog = ref(false)
const applying = ref(false)
const applyTaskId = ref(null)
const applyTasks = ref([])

async function openApply() {
  // 拉取可修改的任务（非运行/已完成），供选择应用
  const res = await getTaskList({ page: 1, pageSize: 100 })
  applyTasks.value = (res.list || []).filter((t) => !['running', 'success'].includes(t.status))
  applyTaskId.value = null
  applyDialog.value = true
}
async function doApply() {
  applying.value = true
  try {
    await applyHyperparams(applyTaskId.value, {
      hyperparams: { lr: lrText.value, batchSize: form.batchSize, epochs: form.epochs, optimizer: form.optimizer, maxLen: form.maxLen, warmup: form.warmup }
    })
    applyDialog.value = false
    ElMessage.success('超参已应用到任务')
  } finally {
    applying.value = false
  }
}
async function saveAsTemplate() {
  try {
    const { value: name } = await ElMessageBox.prompt('请输入模板名称', '保存为超参模板', {
      confirmButtonText: '保存',
      cancelButtonText: '取消',
      inputPattern: /\S+/,
      inputErrorMessage: '模板名称不能为空'
    })
    await saveHyperTemplate({
      name,
      scene: '自定义',
      lr: lrText.value,
      batchSize: form.batchSize,
      epochs: form.epochs,
      optimizer: form.optimizer
    })
    ElMessage.success('已保存为超参模板，可在「配置管理 → 超参模板」中查看')
  } catch (e) {
    /* 用户取消 prompt 时静默 */
  }
}
</script>

<style lang="scss" scoped>
.param-row {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 11px 0;
  border-bottom: 1px dashed #eee;
}
.param-label {
  width: 160px;
  font-size: 13px;
  flex-shrink: 0;
  color: #5e6470;
}
.param-val {
  width: 80px;
  text-align: center;
}
.json-preview {
  background: #1e1e1e;
  color: #9cdcfe;
  padding: 16px;
  border-radius: 4px;
  font-size: 12px;
  line-height: 1.6;
  margin: 0;
  font-family: Consolas, monospace;
}
</style>
