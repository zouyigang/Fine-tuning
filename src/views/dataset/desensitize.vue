<template>
  <div>
    <PageHeader title="数据集脱敏处理" description="自动脱敏身份证号、手机号、银行卡号、涉案人员隐私等敏感信息，支持自定义脱敏规则，确保涉密数据安全" />

    <el-row :gutter="16">
      <el-col :md="14">
        <el-card shadow="never">
          <template #header>
            <div class="flex-between">
              <span>脱敏规则配置</span>
              <el-button type="primary" size="small" :icon="Plus" @click="addRule">新增规则</el-button>
            </div>
          </template>
          <el-table :data="pagedRules" border>
            <el-table-column prop="field" label="敏感字段" width="120" />
            <el-table-column prop="rule" label="脱敏规则" min-width="160" />
            <el-table-column prop="sample" label="脱敏示例" min-width="170">
              <template #default="{ row }"><span class="mono">{{ row.sample }}</span></template>
            </el-table-column>
            <el-table-column label="启用" width="80">
              <template #default="{ row }"><el-switch v-model="row.enabled" @change="(val) => toggleRule(row, val)" /></template>
            </el-table-column>
          </el-table>
          <el-pagination class="mt-16" background layout="total, sizes, prev, pager, next" :page-sizes="[10, 20, 50, 100]" :total="rules.length" v-model:current-page="page" v-model:page-size="pageSize" />
        </el-card>
      </el-col>

      <el-col :md="10">
        <el-card shadow="never">
          <template #header>脱敏执行</template>
          <el-form label-width="90px">
            <el-form-item label="目标数据集">
              <el-select v-model="targetDataset" placeholder="请选择数据集" style="width: 100%" filterable>
                <el-option v-for="d in datasets" :key="d.id" :label="d.name" :value="d.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="应用规则">
              <el-tag v-for="r in rules.filter((x) => x.enabled)" :key="r.id" size="small" class="tag-gap">{{ r.field }}</el-tag>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :icon="Lock" :loading="running" :disabled="!targetDataset" @click="run">
                开始脱敏
              </el-button>
            </el-form-item>
          </el-form>

          <el-divider>脱敏对比预览</el-divider>
          <div class="preview">
            <div class="preview-col">
              <div class="preview-title">原文</div>
              <p>犯罪嫌疑人张伟（身份证 110101199003074567，手机 13812348888）名下银行卡 6217000812345678 存在异常交易。</p>
            </div>
            <div class="preview-col masked">
              <div class="preview-title">脱敏后</div>
              <p>犯罪嫌疑人张**（身份证 110101********4567，手机 138****8888）名下银行卡 **** **** **** 5678 存在异常交易。</p>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Plus, Lock } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'
import {
  getDesensitizeRules, createDesensitizeRule, toggleDesensitizeRule, runDesensitize, getDatasetList
} from '@/api/modules/dataset'

const rules = ref([])
const datasets = ref([])
const targetDataset = ref('')
const running = ref(false)

// 前端分页（本地数据），与各列表页分页控件保持统一，默认每页 10 条
const page = ref(1)
const pageSize = ref(10)
const pagedRules = computed(() => rules.value.slice((page.value - 1) * pageSize.value, page.value * pageSize.value))

onMounted(async () => {
  rules.value = await getDesensitizeRules()
  const res = await getDatasetList({ pageSize: 100 })
  datasets.value = res.list || []
})

async function addRule() {
  const { value } = await ElMessageBox.prompt('请输入敏感字段名称', '新增脱敏规则', { inputPlaceholder: '如：电子邮箱' }).catch(() => ({}))
  if (value) {
    const rule = await createDesensitizeRule({ field: value, rule: '自定义掩码', sample: '****', enabled: true })
    rules.value.push(rule)
    ElMessage.success('已新增规则')
  }
}

async function toggleRule(row, val) {
  try {
    await toggleDesensitizeRule(row.id, val)
  } catch (e) {
    row.enabled = !val // 失败回滚开关状态
  }
}

async function run() {
  running.value = true
  try {
    const res = await runDesensitize(targetDataset.value)
    ElMessage.success(`脱敏完成，共处理 ${(res.count || 0).toLocaleString()} 条样本`)
  } finally {
    running.value = false
  }
}
</script>

<style lang="scss" scoped>
.mono {
  font-family: Consolas, monospace;
  color: #d4380d;
}
.tag-gap {
  margin: 0 6px 6px 0;
}
.preview {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.preview-col {
  padding: 12px;
  border-radius: 4px;
  background: #fafafa;
  font-size: 13px;
  line-height: 1.7;
  &.masked {
    background: #f6ffed;
    border: 1px solid #b7eb8f;
  }
  .preview-title {
    font-weight: 600;
    margin-bottom: 6px;
    color: #8a919f;
  }
}
</style>
