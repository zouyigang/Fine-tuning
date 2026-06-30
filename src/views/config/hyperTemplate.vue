<template>
  <div>
    <PageHeader title="超参模板管理" description="保存常用超参数配置为模板，按业务场景分类（如审讯笔录实体识别、资金流关系抽取），支持模板导入导出">
      <template #extra>
        <el-button :icon="Download" @click="exportAll" :disabled="!list.length">导出全部</el-button>
        <el-button :icon="Upload" @click="triggerImport">导入模板</el-button>
        <el-button type="primary" :icon="Plus" @click="openDialog()">新建模板</el-button>
        <input ref="fileInput" type="file" accept=".json,application/json" style="display: none" @change="onImportFile" />
      </template>
    </PageHeader>

    <el-row :gutter="16">
      <el-col v-for="t in list" :key="t.id" :md="8">
        <el-card shadow="hover" class="tpl-card">
          <div class="flex-between">
            <span class="tpl-name">{{ t.name }}</span>
            <el-tag size="small" type="primary" effect="plain">{{ t.scene }}</el-tag>
          </div>
          <el-descriptions :column="1" size="small" class="mt-16">
            <el-descriptions-item label="学习率">{{ t.lr }}</el-descriptions-item>
            <el-descriptions-item label="批次大小">{{ t.batchSize }}</el-descriptions-item>
            <el-descriptions-item label="训练轮数">{{ t.epochs }}</el-descriptions-item>
            <el-descriptions-item label="优化器">{{ t.optimizer }}</el-descriptions-item>
          </el-descriptions>
          <div class="tpl-footer">
            <span class="text-muted">已使用 {{ t.useCount }} 次</span>
            <div>
              <el-button link type="primary" size="small" @click="openDialog(t)">编辑</el-button>
              <el-button link type="primary" size="small" @click="exportOne(t)">导出</el-button>
              <el-button link type="danger" size="small" @click="remove(t)">删除</el-button>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="dialog" :title="form.id ? '编辑模板' : '新建模板'" width="520px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="模板名称" prop="name"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="业务场景" prop="scene">
          <el-select v-model="form.scene" style="width: 100%"><el-option v-for="s in scenes" :key="s" :label="s" :value="s" /></el-select>
        </el-form-item>
        <el-form-item label="学习率"><el-input v-model="form.lr" placeholder="如 2e-5" /></el-form-item>
        <el-form-item label="批次大小"><el-select v-model="form.batchSize" style="width: 100%"><el-option v-for="b in [8, 16, 32, 64]" :key="b" :label="b" :value="b" /></el-select></el-form-item>
        <el-form-item label="训练轮数"><el-input-number v-model="form.epochs" :min="1" :max="30" /></el-form-item>
        <el-form-item label="优化器"><el-select v-model="form.optimizer" style="width: 100%"><el-option v-for="o in ['AdamW', 'Adam', 'SGD']" :key="o" :label="o" :value="o" /></el-select></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialog = false">取消</el-button><el-button type="primary" @click="save">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onActivated } from 'vue'
import { Plus, Upload, Download } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'
import { getHyperTemplates, saveHyperTemplate, deleteHyperTemplate } from '@/api/modules/config'

const list = ref([])
const dialog = ref(false)
const formRef = ref()
const scenes = ['实体识别', '关系抽取', 'OCR 识别', '事件构建', '风险预警']
const form = reactive({ id: null, name: '', scene: '实体识别', lr: '2e-5', batchSize: 16, epochs: 8, optimizer: 'AdamW' })
const rules = { name: [{ required: true, message: '请输入模板名称', trigger: 'blur' }] }

async function load() {
  const res = await getHyperTemplates({ pageSize: 50 })
  list.value = res.list
}
function openDialog(row) {
  Object.assign(form, { id: null, name: '', scene: '实体识别', lr: '2e-5', batchSize: 16, epochs: 8, optimizer: 'AdamW' }, row || {})
  dialog.value = true
}
async function save() {
  await formRef.value.validate()
  await saveHyperTemplate({ ...form })
  dialog.value = false
  ElMessage.success('保存成功')
  load()
}
async function remove(t) {
  await ElMessageBox.confirm(`确认删除模板「${t.name}」？`, '提示', { type: 'warning' })
  await deleteHyperTemplate(t.id)
  ElMessage.success('已删除')
  load()
}

// 模板可移植字段（剔除 id/useCount 等运行态字段）
function pick(t) {
  return { name: t.name, scene: t.scene, lr: t.lr, batchSize: t.batchSize, epochs: t.epochs, optimizer: t.optimizer }
}
function downloadJson(data, filename) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
function exportOne(t) {
  downloadJson(pick(t), `超参模板_${t.name || t.id}.json`)
}
function exportAll() {
  downloadJson(list.value.map(pick), `超参模板_全部_${new Date().toISOString().slice(0, 10)}.json`)
}

// ---- 导入 ----
const fileInput = ref()
function triggerImport() {
  fileInput.value?.click()
}
async function onImportFile(e) {
  const file = e.target.files?.[0]
  e.target.value = '' // 允许重复选同一文件
  if (!file) return
  let parsed
  try {
    parsed = JSON.parse(await file.text())
  } catch {
    ElMessage.error('文件不是合法的 JSON')
    return
  }
  const items = (Array.isArray(parsed) ? parsed : [parsed]).filter((x) => x && x.name)
  if (!items.length) {
    ElMessage.error('未解析到有效模板（需含 name 字段）')
    return
  }
  let ok = 0
  for (const it of items) {
    try {
      // 不带 id → 一律新建，避免覆盖现有模板
      await saveHyperTemplate(pick(it))
      ok++
    } catch { /* 单条失败跳过，继续导入其余 */ }
  }
  ElMessage.success(`导入完成：成功 ${ok} / ${items.length} 条`)
  load()
}

onActivated(load)
</script>

<style lang="scss" scoped>
.tpl-card { margin-bottom: 16px; }
.tpl-name { font-weight: 600; font-size: 15px; }
.tpl-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-top: 1px solid #f0f0f0;
  padding-top: 10px;
  margin-top: 6px;
}
</style>
