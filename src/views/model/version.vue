<template>
  <div>
    <PageHeader title="模型版本列表" description="展示所有微调生成的模型版本，含版本号、训练时间、训练数据集、核心评估指标与状态" />

    <el-card shadow="never">
      <div class="flex-between mb-16">
        <el-form :inline="true">
          <el-form-item label="名称"><el-input v-model="query.keyword" placeholder="模型名称" clearable @keyup.enter="load" /></el-form-item>
          <el-form-item label="状态">
            <el-select v-model="query.status" placeholder="全部" clearable style="width: 130px" @change="load">
              <el-option v-for="(v, k) in MODEL_STATUS" :key="k" :label="v.label" :value="k" />
            </el-select>
          </el-form-item>
          <el-form-item label="类型">
            <el-select v-model="query.modelType" placeholder="全部" clearable style="width: 130px" @change="load">
              <el-option v-for="t in types" :key="t" :label="t" :value="t" />
            </el-select>
          </el-form-item>
          <el-form-item><el-button type="primary" :icon="Search" @click="load">查询</el-button></el-form-item>
        </el-form>
      </div>

      <el-table v-loading="loading" :data="list" border>
        <el-table-column prop="name" label="模型名称" min-width="140" />
        <el-table-column prop="version" label="版本" width="80" />
        <el-table-column prop="modelType" label="类型" width="110" />
        <el-table-column prop="dataset" label="训练数据集" min-width="150" show-overflow-tooltip />
        <el-table-column prop="f1" label="F1" width="90" sortable />
        <el-table-column prop="size" label="大小" width="90" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }"><el-tag :type="MODEL_STATUS[row.status].type" size="small">{{ MODEL_STATUS[row.status].label }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="trainAt" label="训练时间" width="150" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small">详情</el-button>
            <el-button link type="primary" size="small">评估</el-button>
            <el-button v-if="row.status === 'evaluated'" link type="success" size="small">上线</el-button>
            <el-button link type="info" size="small">下载</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination class="mt-16" background layout="total, sizes, prev, pager, next" :total="total" v-model:current-page="query.page" v-model:page-size="query.pageSize" @change="load" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Search } from '@element-plus/icons-vue'
import PageHeader from '@/components/PageHeader.vue'
import { MODEL_STATUS } from '@/utils/dict'
import { getModelList } from '@/api/modules/model'

const loading = ref(false)
const list = ref([])
const total = ref(0)
const query = reactive({ keyword: '', status: '', modelType: '', page: 1, pageSize: 10 })
const types = ['OCR 识别', '实体识别', '关系抽取', '事件构建', '风险预警']

async function load() {
  loading.value = true
  const res = await getModelList(query)
  list.value = res.list
  total.value = res.total
  loading.value = false
}
onMounted(load)
</script>
