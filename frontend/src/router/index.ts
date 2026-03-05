import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/dashboard',
    },
    {
      path: '/dashboard',
      name: 'Dashboard',
      component: () => import('../views/DashboardView.vue'),
      meta: { title: '持仓总览' },
    },
    {
      path: '/charts',
      name: 'Charts',
      component: () => import('../views/ChartsView.vue'),
      meta: { title: '收益曲线' },
    },
    {
      path: '/dca-plans',
      name: 'DcaPlans',
      component: () => import('../views/DcaPlansView.vue'),
      meta: { title: '定投管理' },
    },
    {
      path: '/signals',
      name: 'Signals',
      component: () => import('../views/SignalsView.vue'),
      meta: { title: '交易信号' },
    },
    {
      path: '/rules',
      name: 'Rules',
      component: () => import('../views/RulesView.vue'),
      meta: { title: '交易规则' },
    },
    {
      path: '/transactions',
      name: 'Transactions',
      component: () => import('../views/TransactionsView.vue'),
      meta: { title: '交易记录' },
    },
    {
      path: '/data-explorer',
      name: 'DataExplorer',
      component: () => import('../views/DataExplorerView.vue'),
      meta: { title: '数据明细' },
    },
  ],
})

export default router
