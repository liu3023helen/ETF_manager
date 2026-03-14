/**
 * 数字格式化工具函数
 */

/** 格式化数字，保留指定小数位 */
export const formatNum = (n: number | null | undefined, decimals = 2): string =>
  (n ?? 0).toFixed(decimals)
