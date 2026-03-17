/**
 * 流程图画板布局配置
 * 模板库 (TemplateTaskFlow) 与执行计划 (TaskFlowChart) 共用，保证生成流程与模板展示一致
 */
export const FLOW_LAYOUT = {
  startX: 140,
  startNodeX: 30,
  mainY: 100,
  horizontalGap: 200,
  verticalGap: 90,
  endNodeOffset: 60,
} as const;

/**
 * 模板预设布局（手动调整后固定）
 * 当模板有预设时优先使用，保证节点位置与设计一致
 */
export const FLOW_LAYOUT_PRESETS: Record<string, Record<string, { x: number; y: number }>> = {
  // 线索转化率：start/t1 水平对齐 y=120；end 与 t5 水平对齐 y=170，且更远
  tpl_lead_conversion_optimization: {
    start: { x: 40, y: 120 },
    t1_data_sync_check: { x: 200, y: 120 },
    t2_lead_assignment_rules: { x: 440, y: 40 },
    t3_response_alert: { x: 440, y: 170 },
    t4_follow_up_workflow: { x: 680, y: 40 },
    t5_performance_dashboard: { x: 920, y: 170 },
    end: { x: 1180, y: 170 },
  },

  // 客户流失预防：c1->c2->(c3,c5) 分支，c3->c4，c4/c5 汇聚 end；水平 240、垂直 110
  tpl_churn_prevention: {
    start: { x: 40, y: 150 },
    c1_churn_model: { x: 200, y: 150 },
    c2_risk_scoring: { x: 440, y: 150 },
    c3_intervention_workflow: { x: 680, y: 95 },
    c4_retention_campaign: { x: 920, y: 95 },
    c5_satisfaction_survey: { x: 680, y: 205 },
    end: { x: 1160, y: 150 },
  },

  // 任务效率提升：e1->(e2,e3) 分支，e2->e4，e3/e4 汇聚 e5；水平 240、垂直 110
  tpl_task_efficiency: {
    start: { x: 40, y: 150 },
    e1_workload_analysis: { x: 200, y: 150 },
    e2_smart_assignment: { x: 440, y: 95 },
    e3_automation_rules: { x: 440, y: 205 },
    e4_bottleneck_alert: { x: 680, y: 95 },
    e5_efficiency_dashboard: { x: 920, y: 150 },
    end: { x: 1160, y: 150 },
  },

  // 营销ROI：m7/m8 拉开间距避免压线，end 与 m8 对齐且更远
  tpl_marketing_roi_optimization: {
    start: { x: 40, y: 200 },
    m1_audience_analysis: { x: 200, y: 135 },
    m2_channel_audit: { x: 200, y: 265 },
    m3_audience_optimization: { x: 440, y: 5 },
    m4_budget_reallocation: { x: 440, y: 135 },
    m5_content_optimization: { x: 440, y: 265 },
    m6_send_time_optimization: { x: 440, y: 395 },
    m7_ab_testing: { x: 700, y: 80 },
    m8_roi_monitoring: { x: 1000, y: 200 },
    end: { x: 1260, y: 200 },
  },
};
