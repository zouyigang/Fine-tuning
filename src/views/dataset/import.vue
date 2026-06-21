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
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small">详情</el-button>
            <el-button link type="primary" size="small">标注</el-button>
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
          <el-upload drag :auto-upload="false" multiple style="width: 100%">
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">拖拽文件到此处，或<em>点击上传</em></div>
            <template #tip><div class="el-upload__tip">支持 JSON / JSONL / CSV / TXT，单文件不超过 500MB</div></template>
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
import { ref, reactive, computed, onMounted } from 'vue'
import { Search, Refresh, Upload, UploadFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'
import { DATA_TYPES, DEPARTMENTS } from '@/utils/dict'
import { getDatasetList, createDataset, deleteDataset } from '@/api/modules/dataset'

const loading = ref(false)
const list = ref([])
const total = ref(0)
const query = reactive({ keyword: '', type: '', page: 1, pageSize: 10 })

const dialog = ref(false)
const submitting = ref(false)
const formRef = ref()
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
async function submit() {
  await formRef.value.validate()
  submitting.value = true
  await createDataset({ name: form.name, type: form.type, dept: form.dept, total: randomCount.value, desensitized: form.desensitize, owner: '张三', updatedAt: '2026-06-09 10:00' })
  submitting.value = false
  dialog.value = false
  ElMessage.success('导入成功')
  load()
}

onMounted(load)
</script>
