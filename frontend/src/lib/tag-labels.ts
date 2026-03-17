/**
 * 标签中文映射配置
 * 用于将系统内部的英文标签转换为用户友好的中文显示
 */

// 方案标签中文映射
export const solutionTagLabelMap: Record<string, string> = {
  // CRM相关
  crm_sharing: 'CRM共享',
  crm_usage: 'CRM使用',
  crm_optimization: 'CRM优化',
  lead_conversion: '线索转化',
  customer_management: '客户管理',
  sales_process: '销售流程',
  
  // 营销相关
  marketing_roi: '营销ROI',
  marketing_effect: '营销效果',
  marketing_enhancement: '营销提升',
  audience_targeting: '受众定向',
  targeting: '定向投放',
  conversion_optimization: '转化优化',
  channel_optimization: '渠道优化',
  channel_analysis: '渠道分析',
  roi_optimization: 'ROI优化',
  content_optimization: '内容优化',
  send_time_optimization: '发送时间优化',
  
  // 留存相关
  churn_prevention: '流失预防',
  customer_retention: '客户留存',
  retention_improvement: '留存改善',
  loyalty_program: '忠诚度计划',
  customer_satisfaction: '客户满意度',
  satisfaction: '满意度提升',
  repurchase_promotion: '复购促进',
  
  // 效率相关
  task_management: '任务管理',
  task_optimization: '任务优化',
  workload_optimization: '负载优化',
  workload_balance: '负载均衡',
  process_automation: '流程自动化',
  process_improvement: '流程改进',
  process_streamline: '流程精简',
  automation: '自动化',
  resource_allocation: '资源分配',
  efficiency_improvement: '效率提升',
  efficiency_optimization: '效率优化',
  
  // 响应优化
  response_optimization: '响应优化',
  response_time: '响应时效',
  
  // 质量相关
  quality_improvement: '质量改进',
  quality_system: '质量体系',
  defect_reduction: '缺陷减少',
  complaint_reduction: '投诉减少',
};

/**
 * 获取标签的中文显示名称
 * @param tag 英文标签
 * @returns 中文显示名称，若无映射则返回原标签
 */
export function getTagLabel(tag: string): string {
  return solutionTagLabelMap[tag] || tag;
}

/**
 * 批量获取标签的中文显示名称
 * @param tags 英文标签数组
 * @returns 中文显示名称数组
 */
export function getTagLabels(tags: string[]): string[] {
  return tags.map(tag => getTagLabel(tag));
}

