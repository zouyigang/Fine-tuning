<template>
  <div>
    <PageHeader title="数据集类型管理" description="维护数据集类型字典：导入数据集时的「类型」下拉、以及数据转换规则的「适用类型」都来自这里。停用的类型不在导入下拉出现。">
      <template #extra><el-button type="primary" :icon="Plus" @click="openDialog()">新建类型</el-button></template>
    </PageHeader>

    <el-card shadow="never">
      <el-table v-loading="loading" :data="list" border>
        <el-table-column prop="seq" label="排序" width="80" align="center" />
        <el-table-column prop="label" label="类型名称" min-width="180" show-overflow-tooltip />
        <el-table-column prop="value" label="类型标识" min-width="140">
          <template #default="{ row }"><el-tag size="small" effect="plain">{{ row.value }}</el-tag></template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-switch :model-value="row.enabled" @change="(v) => toggle(row, v)" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openDialog(row)">编辑</el-button>
            <el-button link type="danger" size="small" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialog" :title="form.id ? '编辑类型' : '新建类型'" width="480px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="类型名称" prop="label">
          <el-input v-model="form.label" placeholder="展示名，也是写入数据集的类型值，如 OCR 校对结果" />
        </el-form-item>
        <el-form-item label="类型标识" prop="value">
          <el-input v-model="form.value" placeholder="英文唯一标识，如 ocr / entity" :disabled="!!form.id" />
          <div class="tip">唯一标识，转换规则与类型靠它关联；创建后不可修改。</div>
        </el-form-item>
        <el-form-item label="排序" prop="seq">
          <el-input-number v-model="form.seq" :min="0" :max="999" />
          <div class="tip">数值越小越靠前（下拉与列表顺序）。</div>
        </el-form-item>
        <el-form-item label="启用"><el-switch v-model="form.enabled" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialog = false">取消</el-button><el-button type="primary" @click="save">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onActivated } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'
import { getDatasetTypes, saveDatasetType, setDatasetTypeStatus, deleteDatasetType } from '@/api/modules/dataset'

const loading = ref(false)
const list = ref([])

async function load() {
  loading.value = true
  try {
    list.value = await getDatasetTypes(false)  // 管理页取全部（含停用）
  } finally {
    loading.value = false
  }
}

const dialog = ref(false)
const formRef = ref()
const DEFAULT_FORM = { id: null, label: '', value: '', seq: 0, enabled: true }
const form = reactive({ ...DEFAULT_FORM })
const rules = {
  label: [{ required: true, message: '请输入类型名称', trigger: 'blur' }],
  value: [
    { required: true, message: '请输入类型标识', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_]+$/, message: '只能是字母/数字/下划线', trigger: 'blur' }
  ]
}

function openDialog(row) {
  Object.assign(form, DEFAULT_FORM, row ? { ...row } : { seq: list.value.length })
  dialog.value = true
}
async function save() {
  await formRef.value.validate()
  await saveDatasetType({ ...form })
  dialog.value = false
  ElMessage.success('保存成功')
  load()
}
async function toggle(row, val) {
  await setDatasetTypeStatus(row.id, val)
  row.enabled = val
  ElMessage.success(val ? '类型已启用' : '类型已停用')
}
async function remove(row) {
  await ElMessageBox.confirm(`确认删除类型「${row.label}」？`, '删除类型', { type: 'warning' })
  await deleteDatasetType(row.id)
  ElMessage.success('类型已删除')
  load()
}

// 用 onActivated（而非顶层调用/onMounted）：被 keep-alive 缓存的页面每次重新进入都刷新
onActivated(load)
</script>

<style lang="scss" scoped>
.tip {
  font-size: 12px;
  color: #a3a8b3;
  line-height: 1.5;
  margin-top: 2px;
}
</style>
