<template>
  <div>
    <PageHeader title="数据集权限控制" description="基于部门和角色配置数据集的查看、编辑、导出权限；涉密数据集仅授权人员可访问，所有操作全程留痕" />

    <el-card shadow="never">
      <template #header>
        <div class="flex-between">
          <span>数据集权限矩阵</span>
          <el-button type="primary" size="small" @click="save">保存权限变更</el-button>
        </div>
      </template>

      <el-table v-loading="loading" :data="list" border>
        <el-table-column prop="name" label="数据集名称" min-width="200" show-overflow-tooltip />
        <el-table-column label="密级" width="90">
          <template #default="{ row }">
            <el-tag :type="row.secret === '涉密' ? 'danger' : 'info'" size="small">{{ row.secret }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="dept" label="所属部门" width="110" />
        <el-table-column label="授权角色" min-width="180">
          <template #default="{ row }">
            <el-select v-model="row.roles" multiple size="small" style="width: 100%">
              <el-option v-for="r in ROLES" :key="r" :label="r" :value="r" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="查看" width="70" align="center">
          <template #default="{ row }"><el-switch v-model="row.canView" size="small" /></template>
        </el-table-column>
        <el-table-column label="编辑" width="70" align="center">
          <template #default="{ row }"><el-switch v-model="row.canEdit" size="small" /></template>
        </el-table-column>
        <el-table-column label="导出" width="70" align="center">
          <template #default="{ row }"><el-switch v-model="row.canExport" size="small" /></template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }"><el-button link type="primary" size="small" @click="showAudit(row)">操作留痕</el-button></template>
        </el-table-column>
      </el-table>

      <el-pagination class="mt-16" background layout="total, sizes, prev, pager, next" :page-sizes="[10, 20, 50, 100]" :total="total" v-model:current-page="query.page" v-model:page-size="query.pageSize" @change="load" />
    </el-card>

    <el-drawer v-model="auditDrawer" title="操作留痕" size="460px">
      <el-timeline>
        <el-timeline-item v-for="(a, i) in audits" :key="i" :timestamp="a.time" placement="top">
          <b>{{ a.user }}</b> {{ a.action }}
          <div class="text-muted" style="font-size: 12px">IP：{{ a.ip }}</div>
        </el-timeline-item>
      </el-timeline>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'
import { ROLES } from '@/utils/dict'
import { getDatasetPermissions, saveDatasetPermissions } from '@/api/modules/dataset'

const loading = ref(false)
const list = ref([])
const total = ref(0)
const query = reactive({ page: 1, pageSize: 10 })
const auditDrawer = ref(false)
const audits = ref([])

async function load() {
  loading.value = true
  const res = await getDatasetPermissions(query)
  list.value = res.list
  total.value = res.total
  loading.value = false
}
async function save() {
  await saveDatasetPermissions(
    list.value.map((r) => ({
      id: r.id, roles: r.roles, canView: r.canView, canEdit: r.canEdit, canExport: r.canExport
    }))
  )
  ElMessage.success('权限变更已保存')
}
function showAudit(row) {
  audits.value = [
    { user: '张三', action: `查看了「${row.name}」`, time: '2026-06-09 09:12', ip: '10.21.3.45' },
    { user: '李四', action: '导出 2,000 条样本', time: '2026-06-08 16:40', ip: '10.21.3.88' },
    { user: '系统管理员', action: '修改授权角色', time: '2026-06-07 11:05', ip: '10.21.3.10' }
  ]
  auditDrawer.value = true
}
onMounted(load)
</script>
