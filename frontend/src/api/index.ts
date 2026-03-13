import axios from 'axios'
import { MessagePlugin } from 'tdesign-vue-next'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
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

// Rules
export const getRules = (params?: { category?: string; rule_type?: string }) =>
  api.get('/rules', { params })
export const createRule = (data: any) => api.post('/rules', data)
export const updateRule = (id: number, data: any) =>
  api.put(`/rules/${id}`, data)
export const toggleRule = (id: number) => api.patch(`/rules/${id}/toggle`)

// Trade Records
export const getTradeRecords = (params?: any) =>
  api.get('/trade-records', { params })
export const getTradeRecord = (id: number) =>
  api.get(`/trade-records/${id}`)
export const createTradeRecord = (data: any) =>
  api.post('/trade-records', data)
export const updateTradeRecord = (id: number, data: any) =>
  api.patch(`/trade-records/${id}`, data)
export const deleteTradeRecord = (id: number) =>
  api.delete(`/trade-records/${id}`)

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


