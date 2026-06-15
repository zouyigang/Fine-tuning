<template>
  <div>
    <PageHeader title="基础模型库管理" description="管理可用于微调的基础模型：系统原生模型、开源大模型（Qwen、Llama 等）、第三方预训练模型，记录来源与授权信息">
      <template #extra><el-button type="primary" :icon="Plus" @click="openDialog()">注册基础模型</el-button></template>
    </PageHeader>

    <el-card shadow="never">
      <el-radio-group v-model="query.source" class="mb-16" @change="load">
        <el-radio-button value="">全部</el-radio-button>
        <el-radio-button value="原生">系统原生</el-radio-button>
        <el-radio-button value="开源">开源大模型</el-radio-button>
        <el-radio-button value="第三方">第三方</el-radio-button>
      </el-radio-group>

      <el-table v-loading="loading" :data="list" border>
        <el-table-column prop="name" label="模型名称" min-width="150" />
        <el-table-column label="来源" width="100">
          <template #default="{ row }"><el-tag :type="row.source === '原生' ? 'success' : row.source === '开源' ? 'primary' : 'warning'" size="small">{{ row.source }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="vendor" label="提供方" width="120" />
        <el-table-column prop="params" label="参数量" width="90" />
        <el-table-column prop="license" label="授权许可" width="130" />
        <el-table-column prop="useCount" label="被使用次数" width="110" sortable />
        <el-table-column prop="addedAt" label="入库时间" width="120" />
        <el-table-column label="启用" width="80">
          <template #default="{ row }"><el-switch v-model="row.enabled" /></template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openDialog(row)">编辑</el-button>
            <el-button link type="danger" size="small">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination class="mt-16" background layout="total, prev, pager, next" :total="total" v-model:current-page="query.page" @change="load" />
    </el-card>

    <el-dialog v-model="dialog" :title="form.id ? '编辑基础模型' : '注册基础模型'" width="560px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="模型名称" prop="name"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="来源" prop="source">
          <el-radio-group v-model="form.source"><el-radio value="原生">原生</el-radio><el-radio value="开源">开源</el-radio><el-radio value="第三方">第三方</el-radio></el-radio-group>
        </el-form-item>
        <el-form-item label="提供方"><el-input v-model="form.vendor" /></el-form-item>
        <el-form-item label="参数量"><el-input v-model="form.params" placeholder="如 7B" /></el-form-item>
        <el-form-item label="授权许可"><el-input v-model="form.license" /></el-form-item>
        <el-form-item label="模型路径"><el-input v-model="form.path" placeholder="如 /models/qwen2-7b 或 HuggingFace 仓库" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialog = false">取消</el-button><el-button type="primary" @click="save">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'
import { getBaseModels, saveBaseModel } from '@/api/modules/config'

const loading = ref(false)
const list = ref([])
const total = ref(0)
const query = reactive({ source: '', page: 1, pageSize: 10 })
const dialog = ref(false)
const formRef = ref()
const form = reactive({ id: null, name: '', source: '开源', vendor: '', params: '', license: '', path: '' })
const rules = {
  name: [{ required: true, message: '请输入模型名称', trigger: 'blur' }],
  source: [{ required: true, message: '请选择来源', trigger: 'change' }]
}

async function load() {
  loading.value = true
  const res = await getBaseModels(query)
  list.value = res.list
  total.value = res.total
  loading.value = false
}
function openDialog(row) {
  Object.assign(form, { id: null, name: '', source: '开源', vendor: '', params: '', license: '', path: '' }, row || {})
  dialog.value = true
}
async function save() {
  await formRef.value.validate()
  await saveBaseModel({ ...form })
  dialog.value = false
  ElMessage.success('保存成功')
  load()
}
onMounted(load)
</script>
