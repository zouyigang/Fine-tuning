<template>
  <div>
    <PageHeader title="多类型数据标注" description="提供 OCR 文本校对、实体/关系三元组、事件要素、风险行为等业务专用标注工具，支持多人协作与结果审核" />

    <el-row :gutter="16">
      <el-col :md="13">
        <el-card shadow="never">
          <template #header>
            <div class="flex-between">
              <span>标注任务</span>
              <el-button type="primary" size="small" :icon="Plus">新建标注任务</el-button>
            </div>
          </template>
          <el-table v-loading="loading" :data="list" border @row-click="(r) => (active = r)">
            <el-table-column prop="title" label="任务名称" min-width="160" show-overflow-tooltip />
            <el-table-column prop="type" label="标注类型" width="140">
              <template #default="{ row }"><el-tag size="small" effect="plain">{{ row.type }}</el-tag></template>
            </el-table-column>
            <el-table-column label="进度" width="90">
              <template #default="{ row }">{{ row.done }}%</template>
            </el-table-column>
            <el-table-column prop="annotators" label="标注人" width="80" />
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag size="small" :type="row.status === '已完成' ? 'success' : row.status === '待审核' ? 'warning' : 'primary'">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination class="mt-16" background layout="total, sizes, prev, pager, next" :page-sizes="[10, 20, 50, 100]" :total="total" v-model:current-page="query.page" v-model:page-size="query.pageSize" @change="load" />
        </el-card>
      </el-col>

      <el-col :md="11">
        <el-card shadow="never">
          <template #header>标注工作台 · 实体/关系三元组</template>
          <div class="anno-toolbar">
            <el-tag v-for="t in entityTypes" :key="t.label" :color="t.color" effect="dark" class="entity-tag" @click="curType = t">
              {{ t.label }}
            </el-tag>
            <span class="text-muted">（选中文本后点击实体类型完成标注）</span>
          </div>
          <div class="anno-text">
            2026年3月12日，<mark class="m-person">犯罪嫌疑人李某</mark>在<mark class="m-loc">朝阳区建国路某银行</mark>，
            将<mark class="m-money">人民币50万元</mark>转账至<mark class="m-person">王某</mark>名下账户，涉嫌<mark class="m-case">洗钱犯罪</mark>。
          </div>
          <el-divider>已标注三元组</el-divider>
          <el-table :data="triples" size="small" border>
            <el-table-column prop="head" label="头实体" />
            <el-table-column prop="relation" label="关系">
              <template #default="{ row }"><el-tag size="small" type="warning">{{ row.relation }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="tail" label="尾实体" />
          </el-table>
          <div class="mt-16 flex-between">
            <el-button :icon="ArrowLeft">上一条</el-button>
            <el-button type="success" :icon="Check" @click="submit">提交标注</el-button>
            <el-button :icon="ArrowRight">下一条</el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Plus, ArrowLeft, ArrowRight, Check } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'
import { getAnnotationTasks } from '@/api/modules/dataset'

const submit = () => ElMessage.success('已提交，进入下一条')

const loading = ref(false)
const list = ref([])
const total = ref(0)
const active = ref(null)
const query = reactive({ page: 1, pageSize: 10 })

const entityTypes = [
  { label: '人名', color: '#2f54eb' },
  { label: '地点', color: '#13c2c2' },
  { label: '金额', color: '#fa8c16' },
  { label: '案由', color: '#722ed1' }
]
const curType = ref(entityTypes[0])

const triples = [
  { head: '李某', relation: '转账', tail: '王某' },
  { head: '李某', relation: '涉嫌', tail: '洗钱犯罪' },
  { head: '转账行为', relation: '发生地点', tail: '朝阳区建国路某银行' }
]

async function load() {
  loading.value = true
  const res = await getAnnotationTasks(query)
  list.value = res.list
  total.value = res.total
  loading.value = false
}
onMounted(load)
</script>

<style lang="scss" scoped>
.anno-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}
.entity-tag {
  cursor: pointer;
  border: none;
}
.anno-text {
  background: #fafafa;
  padding: 16px;
  border-radius: 4px;
  line-height: 2.2;
  font-size: 14px;
  mark {
    padding: 2px 4px;
    border-radius: 3px;
    color: #fff;
  }
  .m-person { background: #2f54eb; }
  .m-loc { background: #13c2c2; }
  .m-money { background: #fa8c16; }
  .m-case { background: #722ed1; }
}
</style>
