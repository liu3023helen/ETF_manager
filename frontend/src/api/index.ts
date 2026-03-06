import axios from 'axios'
import { MessagePlugin } from 'tdesign-vue-next'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

// 响应拦截器：统一错误处理
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const msg =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      '请求失败'
    MessagePlugin.error(msg)
    return Promise.reject(error)
  }
)

// Dashboard
export const getDashboardSummary = () => api.get('/dashboard/summary')

// Funds
export const getFunds = (category?: string) =>
  api.get('/funds', { params: category ? { category } : {} })
export const getFund = (code: string) => api.get(`/funds/${code}`)

// Holdings
export const getHoldings = (platform?: string) =>
  api.get('/holdings', { params: platform ? { platform } : {} })

// Quotes
export const getQuotes = (params?: {
  fund_code?: string
  date_from?: string
  date_to?: string
  page?: number
  page_size?: number
}) => api.get('/quotes', { params })

// DCA Plans
export const getDcaPlans = () => api.get('/dca-plans')
export const createDcaPlan = (data: any) => api.post('/dca-plans', data)
export const updateDcaPlan = (id: number, data: any) =>
  api.put(`/dca-plans/${id}`, data)
export const toggleDcaPlan = (id: number) =>
  api.patch(`/dca-plans/${id}/toggle`)

// Rules
export const getRules = (params?: { category?: string; rule_type?: string }) =>
  api.get('/rules', { params })
export const createRule = (data: any) => api.post('/rules', data)
export const updateRule = (id: number, data: any) =>
  api.put(`/rules/${id}`, data)
export const toggleRule = (id: number) => api.patch(`/rules/${id}/toggle`)

// Signals
export const getSignals = (status?: string) =>
  api.get('/signals', { params: status ? { status } : {} })
export const updateSignalStatus = (id: number, data: any) =>
  api.patch(`/signals/${id}`, data)

// Transactions
export const getTransactions = (params?: any) =>
  api.get('/transactions', { params })
export const createTransaction = (data: any) =>
  api.post('/transactions', data)

// Tables (数据明细)
export const getTableList = () => api.get('/tables')
export const getTableData = (tableName: string, params?: {
  page?: number
  page_size?: number
  sort_by?: string
  sort_order?: string
}) => api.get(`/tables/${tableName}`, { params })
export const executeTableSql = (sql: string) =>
  api.post('/tables/execute-sql', { sql })


