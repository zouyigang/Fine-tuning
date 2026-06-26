<template>
  <div>
    <PageHeader title="操作权限配置" description="配置不同角色的微调操作权限，如普通用户仅可创建任务、管理员可审批模型上线、算法工程师可配置超参数">
      <template #extra><el-button type="primary" :icon="Check" @click="save">保存权限配置</el-button></template>
    </PageHeader>

    <el-card shadow="never">
      <template #header>角色权限矩阵</template>
      <el-table :data="rows" border>
        <el-table-column prop="perm" label="操作权限 \ 角色" width="180" fixed>
          <template #default="{ row }"><span class="perm-name">{{ row.perm }}</span></template>
        </el-table-column>
        <el-table-column v-for="role in data.roles" :key="role.role" :label="role.role" align="center" min-width="130">
          <template #header>
            <div class="role-head">
              <el-icon><UserFilled /></el-icon>
              <span>{{ role.role }}</span>
            </div>
          </template>
          <template #default="{ row }">
            <el-checkbox v-model="matrix[role.role][row.perm]" :disabled="role.role === '系统管理员'" />
          </template>
        </el-table-column>
      </el-table>

      <el-alert class="mt-16" title="系统管理员默认拥有全部权限，不可修改" type="info" :closable="false" show-icon />
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onActivated } from 'vue'
import { Check } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'
import { getRolePermissions, saveRolePermissions } from '@/api/modules/config'

const data = reactive({ perms: [], roles: [] })
const matrix = reactive({})
const rows = computed(() => data.perms.map((p) => ({ perm: p })))

onActivated(async () => {
  Object.assign(data, await getRolePermissions())
  data.roles.forEach((role) => {
    matrix[role.role] = {}
    data.perms.forEach((p) => {
      matrix[role.role][p] = role.granted.includes(p)
    })
  })
})

async function save() {
  await saveRolePermissions(matrix)
  ElMessage.success('权限配置已保存')
}
</script>

<style lang="scss" scoped>
.perm-name { font-weight: 500; }
.role-head {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}
</style>
