<template>
  <div>
    <PageHeader title="用户与角色管理" description="管理平台账号：创建/编辑用户、分配角色与部门、重置密码、启用或禁用账号；写操作需「权限分配」权限（系统管理员默认拥有）">
      <template #extra><el-button type="primary" :icon="Plus" @click="openDialog()">新建用户</el-button></template>
    </PageHeader>

    <el-card shadow="never">
      <el-form :inline="true" class="mb-16">
        <el-form-item label="关键字">
          <el-input v-model="query.keyword" placeholder="账号 / 姓名" clearable style="width: 180px" @keyup.enter="reload" @clear="reload" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="query.role" placeholder="全部" clearable style="width: 150px" @change="reload">
            <el-option v-for="r in ROLES" :key="r" :label="r" :value="r" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 120px" @change="reload">
            <el-option label="启用" value="active" />
            <el-option label="禁用" value="disabled" />
          </el-select>
        </el-form-item>
        <el-form-item><el-button type="primary" @click="reload">查询</el-button></el-form-item>
      </el-form>

      <el-table v-loading="loading" :data="list" border>
        <el-table-column prop="username" label="账号" width="140" />
        <el-table-column prop="realName" label="姓名" width="120" />
        <el-table-column prop="dept" label="部门" min-width="160" show-overflow-tooltip />
        <el-table-column label="角色" width="130">
          <template #default="{ row }"><el-tag size="small" :type="row.role === '系统管理员' ? 'danger' : 'primary'">{{ row.role }}</el-tag></template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="row.status === 'active' ? 'success' : 'info'">{{ row.status === 'active' ? '启用' : '禁用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openDialog(row)">编辑</el-button>
            <el-button link type="primary" size="small" @click="resetPwd(row)">重置密码</el-button>
            <el-button link :type="row.status === 'active' ? 'warning' : 'success'" size="small" @click="toggleStatus(row)">
              {{ row.status === 'active' ? '禁用' : '启用' }}
            </el-button>
            <el-button link type="danger" size="small" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination class="mt-16" background layout="total, sizes, prev, pager, next" :page-sizes="[10, 20, 50, 100]" :total="total" v-model:current-page="query.page" v-model:page-size="query.pageSize" @change="load" />
    </el-card>

    <el-dialog v-model="dialog" :title="form.id ? '编辑用户' : '新建用户'" width="520px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="账号" prop="username">
          <el-input v-model="form.username" :disabled="!!form.id" placeholder="登录账号" />
        </el-form-item>
        <el-form-item v-if="!form.id" label="初始密码" prop="password">
          <el-input v-model="form.password" type="password" show-password placeholder="登录密码" />
        </el-form-item>
        <el-form-item label="姓名" prop="realName"><el-input v-model="form.realName" /></el-form-item>
        <el-form-item label="部门">
          <el-select v-model="form.dept" placeholder="请选择" filterable allow-create style="width: 100%">
            <el-option v-for="d in DEPARTMENTS" :key="d" :label="d" :value="d" />
          </el-select>
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="form.role" placeholder="请选择" style="width: 100%">
            <el-option v-for="r in ROLES" :key="r" :label="r" :value="r" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer><el-button @click="dialog = false">取消</el-button><el-button type="primary" @click="save">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'
import { ROLES, DEPARTMENTS } from '@/utils/dict'
import {
  getUserList, createUser, updateUser, deleteUser, resetPassword, setUserStatus
} from '@/api/modules/user'

const loading = ref(false)
const list = ref([])
const total = ref(0)
const query = reactive({ keyword: '', role: '', status: '', page: 1, pageSize: 10 })

const dialog = ref(false)
const formRef = ref()
const DEFAULT_FORM = { id: null, username: '', password: '', realName: '', dept: '', role: '普通用户' }
const form = reactive({ ...DEFAULT_FORM })
const rules = {
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入初始密码', trigger: 'blur' }],
  realName: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }]
}

async function load() {
  loading.value = true
  try {
    const res = await getUserList(query)
    list.value = res.list
    total.value = res.total
  } finally {
    loading.value = false
  }
}
function reload() {
  query.page = 1
  load()
}
function openDialog(row) {
  Object.assign(form, DEFAULT_FORM, row ? { ...row, password: '' } : {})
  dialog.value = true
}
async function save() {
  await formRef.value.validate()
  if (form.id) {
    await updateUser(form.id, { realName: form.realName, dept: form.dept, role: form.role })
  } else {
    await createUser({ username: form.username, password: form.password, realName: form.realName, dept: form.dept, role: form.role })
  }
  dialog.value = false
  ElMessage.success('保存成功')
  load()
}
async function resetPwd(row) {
  const { value } = await ElMessageBox.prompt(`为「${row.realName || row.username}」设置新密码`, '重置密码', {
    inputType: 'password', inputPlaceholder: '新密码（至少 6 位）',
    inputValidator: (v) => (v && v.length >= 6 ? true : '密码至少 6 位')
  }).catch(() => ({}))
  if (value) {
    await resetPassword(row.id, value)
    ElMessage.success('密码已重置')
  }
}
async function toggleStatus(row) {
  const next = row.status === 'active' ? 'disabled' : 'active'
  await setUserStatus(row.id, next)
  ElMessage.success(next === 'active' ? '账号已启用' : '账号已禁用')
  load()
}
async function remove(row) {
  await ElMessageBox.confirm(`确认删除用户「${row.realName || row.username}」？此操作不可恢复。`, '删除用户', { type: 'warning' })
  await deleteUser(row.id)
  ElMessage.success('用户已删除')
  load()
}
onMounted(load)
</script>
