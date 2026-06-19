<template>
  <div>
    <PageHeader title="操作日志审计" description="自动记录平台关键操作（登录、任务创建、状态变更、模型上线/回滚、配置变更等），用于安全审计与责任追溯" />

    <el-card shadow="never">
      <!-- 筛选栏 -->
      <el-form :inline="true" :model="query" class="filter-bar">
        <el-form-item label="操作账号">
          <el-input v-model="query.username" placeholder="用户名" clearable style="width: 140px" @keyup.enter="search" />
        </el-form-item>
        <el-form-item label="模块">
          <el-select v-model="query.module" placeholder="全部" clearable style="width: 150px" @change="search">
            <el-option v-for="m in modules" :key="m" :label="m" :value="m" />
          </el-select>
        </el-form-item>
        <el-form-item label="结果">
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 110px" @change="search">
            <el-option label="成功" value="成功" />
            <el-option label="失败" value="失败" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键字">
          <el-input v-model="query.keyword" placeholder="操作 / 路径 / 姓名" clearable style="width: 180px" @keyup.enter="search" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="search">查询</el-button>
          <el-button :icon="RefreshRight" @click="reset">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table v-loading="loading" :data="list" border>
        <el-table-column prop="time" label="操作时间" width="170" />
        <el-table-column label="操作人" width="150">
          <template #default="{ row }">
            <span>{{ row.realName }}</span>
            <span class="text-muted">（{{ row.username }}）</span>
          </template>
        </el-table-column>
        <el-table-column label="模块" width="110">
          <template #default="{ row }"><el-tag size="small" effect="plain">{{ row.module }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="action" label="操作" min-width="150" show-overflow-tooltip />
        <el-table-column label="方法" width="80">
          <template #default="{ row }"><el-tag size="small" :type="METHOD_TYPE[row.method] || 'info'" effect="light">{{ row.method }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="path" label="路径" min-width="200" show-overflow-tooltip />
        <el-table-column prop="ip" label="来源 IP" width="130" />
        <el-table-column label="结果" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="row.status === '成功' ? 'success' : 'danger'">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="detail" label="备注" min-width="140" show-overflow-tooltip />
      </el-table>

      <el-pagination
        class="mt-16"
        background
        layout="total, prev, pager, next, jumper"
        :total="total"
        :page-size="query.pageSize"
        v-model:current-page="query.page"
        @change="load"
      />
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Search, RefreshRight } from '@element-plus/icons-vue'
import PageHeader from '@/components/PageHeader.vue'
import { getOperationLogs, getLogModules } from '@/api/modules/log'

const METHOD_TYPE = { POST: 'success', PUT: 'warning', DELETE: 'danger', PATCH: 'warning', GET: 'info' }

const loading = ref(false)
const list = ref([])
const total = ref(0)
const modules = ref([])
const query = reactive({ username: '', module: '', status: '', keyword: '', page: 1, pageSize: 10 })

async function load() {
  loading.value = true
  try {
    const res = await getOperationLogs(query)
    list.value = res.list
    total.value = res.total
  } finally {
    loading.value = false
  }
}
function search() {
  query.page = 1
  load()
}
function reset() {
  Object.assign(query, { username: '', module: '', status: '', keyword: '', page: 1 })
  load()
}
onMounted(async () => {
  modules.value = await getLogModules()
  load()
})
</script>

<style lang="scss" scoped>
.filter-bar { margin-bottom: 4px; }
.text-muted { color: #909399; font-size: 12px; }
</style>
