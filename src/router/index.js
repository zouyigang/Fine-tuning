import { createRouter, createWebHashHistory } from 'vue-router'
import Layout from '@/layout/index.vue'
import { useUserStore } from '@/store/user'

/**
 * 路由即菜单：侧边栏根据本配置自动渲染。
 * meta.title 菜单名称 / meta.icon 图标(Element Plus 图标组件名)
 *
 * 五大二级模块对应业务清单：
 *  - 数据集管理 / 微调任务管理 / 模型效果评估 / 模型版本管理 / 微调配置管理
 */
export const asyncRoutes = [
  {
    path: '/dashboard',
    component: Layout,
    redirect: '/dashboard/index',
    meta: { title: '工作台', icon: 'Odometer', single: true },
    children: [
      {
        path: 'index',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/index.vue'),
        meta: { title: '工作台', icon: 'Odometer' }
      }
    ]
  },
  {
    path: '/dataset',
    component: Layout,
    redirect: '/dataset/import',
    meta: { title: '数据集管理', icon: 'Coin' },
    children: [
      { path: 'import', name: 'DatasetImport', component: () => import('@/views/dataset/import.vue'), meta: { title: '数据集导入', icon: 'Upload' } },
      { path: 'annotation', name: 'DatasetAnnotation', component: () => import('@/views/dataset/annotation.vue'), meta: { title: '多类型数据标注', icon: 'EditPen' } },
      { path: 'desensitize', name: 'DatasetDesensitize', component: () => import('@/views/dataset/desensitize.vue'), meta: { title: '数据集脱敏处理', icon: 'Lock' } },
      { path: 'version', name: 'DatasetVersion', component: () => import('@/views/dataset/version.vue'), meta: { title: '数据集版本管理', icon: 'Files' } },
      { path: 'statistics', name: 'DatasetStatistics', component: () => import('@/views/dataset/statistics.vue'), meta: { title: '数据集统计分析', icon: 'DataAnalysis' } },
      { path: 'permission', name: 'DatasetPermission', component: () => import('@/views/dataset/permission.vue'), meta: { title: '数据集权限控制', icon: 'Key' } }
    ]
  },
  {
    path: '/task',
    component: Layout,
    redirect: '/task/create',
    meta: { title: '微调任务管理', icon: 'SetUp' },
    children: [
      { path: 'create', name: 'TaskCreate', component: () => import('@/views/task/create.vue'), meta: { title: '微调任务创建', icon: 'Plus' } },
      { path: 'hyperparams', name: 'TaskHyperparams', component: () => import('@/views/task/hyperparams.vue'), meta: { title: '超参数可视化配置', icon: 'Operation' } },
      { path: 'monitor', name: 'TaskMonitor', component: () => import('@/views/task/monitor.vue'), meta: { title: '训练任务实时监控', icon: 'Monitor' } },
      { path: 'control', name: 'TaskControl', component: () => import('@/views/task/control.vue'), meta: { title: '任务启停与重试', icon: 'VideoPause' } },
      { path: 'schedule', name: 'TaskSchedule', component: () => import('@/views/task/schedule.vue'), meta: { title: '批量微调任务调度', icon: 'Calendar' } },
      { path: 'logs', name: 'TaskLogs', component: () => import('@/views/task/logs.vue'), meta: { title: '训练日志管理', icon: 'Document' } }
    ]
  },
  {
    path: '/evaluation',
    component: Layout,
    redirect: '/evaluation/metrics',
    meta: { title: '模型效果评估', icon: 'TrendCharts' },
    children: [
      { path: 'metrics', name: 'EvalMetrics', component: () => import('@/views/evaluation/metrics.vue'), meta: { title: '自动化指标评估', icon: 'DataLine' } },
      { path: 'benchmark', name: 'EvalBenchmark', component: () => import('@/views/evaluation/benchmark.vue'), meta: { title: '基准模型对比', icon: 'Histogram' } },
      { path: 'scene', name: 'EvalScene', component: () => import('@/views/evaluation/scene.vue'), meta: { title: '真实业务场景验证', icon: 'Aim' } },
      { path: 'review', name: 'EvalReview', component: () => import('@/views/evaluation/review.vue'), meta: { title: '人工复核评估', icon: 'View' } },
      { path: 'errors', name: 'EvalErrors', component: () => import('@/views/evaluation/errors.vue'), meta: { title: '错误案例分析', icon: 'WarningFilled' } },
      { path: 'playground', name: 'EvalPlayground', component: () => import('@/views/evaluation/playground.vue'), meta: { title: '模型对话对比', icon: 'ChatDotRound' } },
      { path: 'report', name: 'EvalReport', component: () => import('@/views/evaluation/report.vue'), meta: { title: '评估报告生成', icon: 'Tickets' } }
    ]
  },
  {
    path: '/model',
    component: Layout,
    redirect: '/model/version',
    meta: { title: '模型版本管理', icon: 'Box' },
    children: [
      { path: 'version', name: 'ModelVersion', component: () => import('@/views/model/version.vue'), meta: { title: '模型版本列表', icon: 'List' } },
      { path: 'gray', name: 'ModelGray', component: () => import('@/views/model/gray.vue'), meta: { title: '模型灰度上线', icon: 'Promotion' } },
      { path: 'release', name: 'ModelRelease', component: () => import('@/views/model/release.vue'), meta: { title: '模型全量上线', icon: 'Upload' } },
      { path: 'rollback', name: 'ModelRollback', component: () => import('@/views/model/rollback.vue'), meta: { title: '模型快速回滚', icon: 'RefreshLeft' } },
      { path: 'deploy', name: 'ModelDeploy', component: () => import('@/views/model/deploy.vue'), meta: { title: '模型导出与部署', icon: 'Connection' } },
      { path: 'archive', name: 'ModelArchive', component: () => import('@/views/model/archive.vue'), meta: { title: '模型归档与清理', icon: 'FolderOpened' } }
    ]
  },
  {
    path: '/config',
    component: Layout,
    redirect: '/config/base-model',
    meta: { title: '微调配置管理', icon: 'Setting' },
    children: [
      { path: 'base-model', name: 'ConfigBaseModel', component: () => import('@/views/config/baseModel.vue'), meta: { title: '基础模型库管理', icon: 'Cpu' } },
      { path: 'hyper-template', name: 'ConfigHyperTemplate', component: () => import('@/views/config/hyperTemplate.vue'), meta: { title: '超参模板管理', icon: 'Collection' } },
      { path: 'resource', name: 'ConfigResource', component: () => import('@/views/config/resource.vue'), meta: { title: '训练资源配置', icon: 'Platform' } },
      { path: 'auto-tune', name: 'ConfigAutoTune', component: () => import('@/views/config/autoTune.vue'), meta: { title: '自动调优配置', icon: 'MagicStick' } },
      { path: 'dataset-type', name: 'ConfigDatasetType', component: () => import('@/views/config/datasetType.vue'), meta: { title: '数据集类型管理', icon: 'CollectionTag' } },
      { path: 'convert-rule', name: 'ConfigConvertRule', component: () => import('@/views/config/convertRule.vue'), meta: { title: '数据转换规则', icon: 'Switch' } },
      { path: 'permission', name: 'ConfigPermission', component: () => import('@/views/config/permission.vue'), meta: { title: '操作权限配置', icon: 'UserFilled' } },
      { path: 'user-manage', name: 'ConfigUserManage', component: () => import('@/views/config/userManage.vue'), meta: { title: '用户与角色管理', icon: 'User' } },
      { path: 'operation-log', name: 'ConfigOperationLog', component: () => import('@/views/config/operationLog.vue'), meta: { title: '操作日志审计', icon: 'Document' } }
    ]
  }
]

const constantRoutes = [
  {
    path: '/login',
    component: () => import('@/views/login/index.vue'),
    meta: { hidden: true }
  },
  {
    path: '/screen',
    name: 'DataScreen',
    component: () => import('@/views/screen/index.vue'),
    meta: { hidden: true }
  },
  { path: '/', redirect: '/dashboard/index' },
  {
    path: '/:pathMatch(.*)*',
    component: () => import('@/views/error/404.vue'),
    meta: { hidden: true }
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes: [...asyncRoutes, ...constantRoutes],
  scrollBehavior: () => ({ top: 0 })
})

// 全局路由守卫：未登录跳登录页；已登录访问登录页跳工作台；并按需拉取用户信息
router.beforeEach(async (to) => {
  const token = localStorage.getItem('token')

  if (to.path === '/login') {
    return token ? '/dashboard/index' : true
  }

  if (!token) {
    return { path: '/login', query: to.fullPath !== '/' ? { redirect: to.fullPath } : {} }
  }

  const userStore = useUserStore()
  if (!userStore.userInfo.name) {
    try {
      await userStore.getInfo()
    } catch (e) {
      await userStore.logout()
      return '/login'
    }
  }
  return true
})

export default router
