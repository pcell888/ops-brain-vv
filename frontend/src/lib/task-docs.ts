/**
 * 方案库任务说明：每个任务的作用与工作原理（用于模板详情页展示）
 */
export interface TaskDoc {
  /** 任务在方案中的作用 */
  role: string;
  /** 工作原理（执行时具体做什么） */
  howItWorks: string;
}

export const TASK_DOCS: Record<string, TaskDoc> = {
  // ========== 线索转化率优化方案 ==========
  t1_data_sync_check: {
    role: '为后续任务提供可靠数据基础，避免因数据延迟导致分配与统计失真。',
    howItWorks: '系统会按配置检查线索、联系人、商机等实体的 CRM 同步状态；若发现某实体同步延迟，会自动触发该实体的重新同步，并记录问题清单供排查。',
  },
  t2_lead_assignment_rules: {
    role: '让线索按能力与负载均衡分配，减少争抢或闲置，提高首响与跟进质量。',
    howItWorks: '调用 CRM 接口创建「智能分配规则」，按容量、专长、在岗等因子采用负载均衡算法；创建后自动激活该规则，新线索将按规则自动分配。',
  },
  t3_response_alert: {
    role: '缩短线索首响时间，避免超时未联系导致流失。',
    howItWorks: '在 CRM 中创建「响应超时」预警规则：超过设定小时数未联系则触发告警，通过邮件/IM 等渠道通知销售经理，并可回调 Ops Brain 做记录。',
  },
  t4_follow_up_workflow: {
    role: '统一跟进节奏与节点，配合自动提醒减少漏跟、提升转化。',
    howItWorks: '在 CRM 中创建标准跟进工作流，包含多阶段（如首次接触、需求了解、方案演示、报价谈判、签约跟进）及每阶段建议动作与时长；支持到期自动提醒。',
  },
  t5_performance_dashboard: {
    role: '集中展示转化、响应、跟进等核心指标，并在完成后自动启动效果追踪。',
    howItWorks: '部署销售效能看板：配置线索转化率、平均响应时间、跟进次数等组件及转化漏斗、团队对比、销售排名；配置阈值预警（如转化率<12%、响应>4h）；注册 CRM 变更 webhook 以刷新数据。T5 完成后系统会自动为该执行计划创建效果追踪。',
  },

  // ========== 营销 ROI 提升方案 ==========
  m1_audience_analysis: {
    role: '找出高转化人群特征，为定向、内容和发送时间优化提供依据。',
    howItWorks: '从 CRM、营销、网站等数据源分析受众画像，识别高转化人群的特征与分布，输出受众洞察报告。',
  },
  m2_channel_audit: {
    role: '识别低效渠道，为预算重分配提供依据。',
    howItWorks: '按 CPC、CPA、ROAS 等指标审计各投放渠道效果，输出渠道效果报告与优化建议。',
  },
  m3_audience_optimization: {
    role: '基于分析结果收紧或扩展定向，提高触达质量。',
    howItWorks: '根据受众分析结果在营销平台调整定向策略（如相似人群扩展阈值），需人工确认后生效。',
  },
  m4_budget_reallocation: {
    role: '把预算从低效渠道挪到高效渠道，提升整体 ROI。',
    howItWorks: '根据渠道审计结果，按绩效规则给出预算调整建议；需人工在投放端执行实际预算调整。',
  },
  m5_content_optimization: {
    role: '提升打开率与点击率，进而提升转化与 ROI。',
    howItWorks: '基于历史数据筛选高效内容模板，对标题、正文、CTA 等做优化建议；部分由系统自动应用，部分需人工确认。',
  },
  m6_send_time_optimization: {
    role: '在用户活跃时段触达，提高打开与转化。',
    howItWorks: '分析用户活跃时段并生成发送时间策略，支持多时段分批发送；在营销平台配置并启用。',
  },
  m7_ab_testing: {
    role: '用数据验证创意与落地页优劣，持续优化。',
    howItWorks: '配置创意与落地页的 A/B 测试（时长与置信度可配置），系统分配流量并汇总结果，供人工决策采用哪一版。',
  },
  m8_roi_monitoring: {
    role: '实时监控 ROI 与异常，便于及时调整。',
    howItWorks: '部署 ROI 监控看板与预警（如环比下降超过阈值告警），对接营销与 CRM 数据做实时刷新。',
  },

  // ========== 客户流失预防方案 ==========
  c1_churn_model: {
    role: '提前识别可能流失的客户，为干预争取时间。',
    howItWorks: '使用近因、频次、金额、互动等特征训练流失预测模型，输出客户流失概率。',
  },
  c2_risk_scoring: {
    role: '将流失概率转化为风险等级与名单，便于分层干预。',
    howItWorks: '对客户进行流失风险评分并划分等级，按日更新并生成高风险预警名单。',
  },
  c3_intervention_workflow: {
    role: '对不同风险等级配置标准化干预动作，避免遗漏或过度打扰。',
    howItWorks: '按风险等级配置干预流程（如外呼、邮件、优惠、VIP 服务等），需人工确认规则与触达内容。',
  },
  c4_retention_campaign: {
    role: '通过定向挽留活动提升留存与复购。',
    howItWorks: '配置折扣、专属权益、会员计划等挽留活动，与干预流程联动，部分自动化执行、部分需人工审批。',
  },
  c5_satisfaction_survey: {
    role: '持续收集满意度与 NPS，发现服务短板并驱动改进。',
    howItWorks: '配置定期满意度调研（如月度）及触发时机（如购买后、工单关闭后），自动下发问卷并汇总结果。',
  },

  // ========== 任务效率提升方案 ==========
  e1_workload_analysis: {
    role: '掌握各成员/团队负载，为分配与调优提供依据。',
    howItWorks: '从任务系统拉取任务数、完成率、加班时长等指标，分析负载分布与瓶颈。',
  },
  e2_smart_assignment: {
    role: '按能力与负载智能分配任务，提高完成率与公平性。',
    howItWorks: '根据技能匹配、当前负载、优先级、截止时间等因子配置智能分配规则，新任务按规则推荐或自动分配，需根据系统支持情况人工确认。',
  },
  e3_automation_rules: {
    role: '减少重复人工操作，缩短流程耗时。',
    howItWorks: '配置审批、通知、状态更新等自动化规则，满足条件时由系统自动执行。',
  },
  e4_bottleneck_alert: {
    role: '及时发现卡点与超时，避免任务堆积。',
    howItWorks: '配置任务卡点与超时阈值（如超 24 小时未推进），自动预警并升级至指定角色（如主管）。',
  },
  e5_efficiency_dashboard: {
    role: '集中展示完成率、耗时、自动化率等，支撑持续优化。',
    howItWorks: '部署效率看板，展示完成率、平均处理时长、自动化率等指标，并支持简单预警与下钻。',
  },
};

export function getTaskDoc(taskId: string): TaskDoc | undefined {
  return TASK_DOCS[taskId];
}
