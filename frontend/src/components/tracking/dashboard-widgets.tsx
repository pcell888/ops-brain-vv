import { Empty, Tag } from 'antd';
import { FilterOutlined, TeamOutlined, CrownOutlined } from '@ant-design/icons';

// 转化漏斗组件
interface FunnelStage {
  name: string;
  count: number;
  conversion_rate?: number;
  overall_rate?: number;
}

interface ConversionFunnelProps {
  data: FunnelStage[];
  title?: string;
  showIcon?: boolean;
  compact?: boolean;
}

export function ConversionFunnel({ 
  data, 
  title = '线索转化漏斗', 
  showIcon = true,
  compact = false 
}: ConversionFunnelProps) {
  if (!data || data.length === 0) {
    return (
      <div className="bg-gray-800/30 rounded-lg p-3">
        {showIcon && (
          <h4 className="text-sm font-medium text-white mb-3 flex items-center gap-2">
            <FilterOutlined className="text-blue-400" />
            {title}
          </h4>
        )}
        <Empty description="暂无漏斗数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      </div>
    );
  }

  return (
    <div className="bg-gray-800/30 rounded-lg p-3" id="funnel-card">
      {showIcon && (
        <h4 className="text-sm font-medium text-white mb-3 flex items-center gap-2">
          <FilterOutlined className="text-blue-400" />
          {title}
        </h4>
      )}
      <div className={compact ? "space-y-2" : "space-y-3"}>
        {data.map((stage, index) => (
          <div key={index} className="relative">
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm text-gray-300">{stage.name}</span>
              <div className="flex items-center gap-2">
                <span className="text-white font-medium">{stage.count}</span>
                {(stage.conversion_rate || 0) > 0 && (
                        <Tag 
                    color={stage.conversion_rate! >= 70 ? 'success' : stage.conversion_rate! >= 40 ? 'warning' : 'error'}
                  >
                    {stage.conversion_rate!.toFixed(1)}%
                  </Tag>
                )}
              </div>
            </div>
            {/* 漏斗条 */}
            <div className={`bg-gray-700/50 rounded-lg overflow-hidden relative ${compact ? 'h-6' : 'h-8'}`}>
              <div
                className="h-full bg-gradient-to-r from-blue-500 to-blue-400 transition-all duration-500"
                style={{ width: `${Math.max(10, stage.overall_rate || 0)}%` }}
              />
              <span className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-gray-400">
                {(stage.overall_rate || 0).toFixed(1)}%
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

import { useEffect, useRef, useState } from 'react';

// 团队对比组件
interface TeamData {
  team_id?: string;
  team_name: string;
  leads_count: number;
  converted_count: number;
  conversion_rate: number;
  avg_response_time: number;
}

interface TeamComparisonProps {
  data: TeamData[];
  title?: string;
  showIcon?: boolean;
  compact?: boolean;
  syncHeight?: boolean;
}

export function TeamComparison({ 
  data, 
  title = '团队转化率对比', 
  showIcon = true,
  compact = false,
  syncHeight = false 
}: TeamComparisonProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerHeight, setContainerHeight] = useState<number | undefined>(undefined);

  useEffect(() => {
    if (syncHeight) {
      // 获取漏斗卡片高度
      const funnelCard = document.getElementById('funnel-card');
      if (funnelCard && containerRef.current) {
        const height = funnelCard.getBoundingClientRect().height;
        setContainerHeight(height);
      }
    }
  }, [syncHeight, data]);

  if (!data || data.length === 0) {
    return (
      <div className="bg-gray-800/30 rounded-lg p-3 h-full flex flex-col">
        {showIcon && (
          <h4 className="text-sm font-medium text-white mb-3 flex items-center gap-2">
            <TeamOutlined className="text-green-400" />
            {title}
          </h4>
        )}
        <Empty description="暂无团队数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      </div>
    );
  }

  return (
    <div 
      ref={containerRef}
      className="bg-gray-800/30 rounded-lg p-3 flex flex-col"
      style={containerHeight ? { height: containerHeight } : undefined}
    >
      {showIcon && (
        <h4 className="text-sm font-medium text-white mb-3 flex items-center gap-2">
          <TeamOutlined className="text-green-400" />
          {title}
        </h4>
      )}
      <div className={`space-y-2 overflow-y-auto flex-1 ${compact ? 'max-h-none' : ''}`}>
        {data.map((team, index) => (
          <div key={index} className="bg-gray-700/50 rounded-lg p-2">
            <div className="flex items-center justify-between mb-1">
              <span className="text-white font-medium text-sm">{team.team_name}</span>
              <Tag 
                color={team.conversion_rate >= 20 ? 'success' : team.conversion_rate >= 15 ? 'warning' : 'error'}
              >
                {team.conversion_rate.toFixed(1)}%
              </Tag>
            </div>
            <div className={`grid gap-1 text-center text-xs ${compact ? 'grid-cols-2' : 'grid-cols-3'}`}>
              <div>
                <div className="text-gray-400">线索数</div>
                <div className="text-white">{team.leads_count}</div>
              </div>
              <div>
                <div className="text-gray-400">转化数</div>
                <div className="text-white">{team.converted_count}</div>
              </div>
              {!compact && (
                <div>
                  <div className="text-gray-400">响应时间</div>
                  <div className={`font-medium ${team.avg_response_time <= 2 ? 'text-green-400' : team.avg_response_time <= 4 ? 'text-yellow-400' : 'text-red-400'}`}>
                    {team.avg_response_time.toFixed(1)}h
                  </div>
                </div>
              )}
            </div>
            {/* 转化率进度条 */}
            <div className="mt-2 h-2 bg-gray-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-green-500 to-green-400 rounded-full transition-all duration-500"
                style={{ width: `${Math.min(100, team.conversion_rate * 3)}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// 销售排名组件
interface SalesRankingItem {
  rank: number;
  sales_name: string;
  team_name: string;
  leads_count: number;
  converted_count: number;
  conversion_rate: number;
  avg_response_time: number;
  follow_up_count?: number;
  score?: number;
}

interface SalesRankingProps {
  data: SalesRankingItem[];
  title?: string;
  showIcon?: boolean;
  showCount?: boolean;
  compact?: boolean;
  syncHeight?: boolean;
}

export function SalesRanking({ 
  data, 
  title = '销售排行榜', 
  showIcon = true,
  showCount = true,
  compact = false,
  syncHeight = false 
}: SalesRankingProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerHeight, setContainerHeight] = useState<number | undefined>(undefined);

  useEffect(() => {
    if (syncHeight) {
      // 获取漏斗卡片高度
      const funnelCard = document.getElementById('funnel-card');
      if (funnelCard && containerRef.current) {
        const height = funnelCard.getBoundingClientRect().height;
        setContainerHeight(height);
      }
    }
  }, [syncHeight, data]);

  if (!data || data.length === 0) {
    return (
      <div className="bg-gray-800/30 rounded-lg p-3 h-full flex flex-col">
        {showIcon && (
          <h4 className="text-sm font-medium text-white mb-3 flex items-center gap-2">
            <CrownOutlined className="text-yellow-400" />
            {title}
          </h4>
        )}
        <Empty description="暂无排名数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      </div>
    );
  }

  return (
    <div 
      ref={containerRef}
      className="bg-gray-800/30 rounded-lg p-3 flex flex-col"
      style={containerHeight ? { height: containerHeight } : undefined}
    >
      {showIcon && (
        <h4 className="text-sm font-medium text-white mb-3 flex items-center gap-2">
          <CrownOutlined className="text-yellow-400" />
          <span>{title}</span>
          {showCount && (
            <Tag className="ml-1 text-xs">{data.length}人</Tag>
          )}
        </h4>
      )}
      <div className={`space-y-1 overflow-y-auto flex-1 ${compact ? 'max-h-none' : ''}`}>
        {data.map((sales, index) => (
          <div
            key={index}
            className={`flex items-center gap-2 p-2 rounded-lg ${
              index === 0 ? 'bg-yellow-500/10 border border-yellow-500/30' :
              index === 1 ? 'bg-gray-400/10 border border-gray-400/30' :
              index === 2 ? 'bg-orange-600/10 border border-orange-600/30' :
              'bg-gray-700/30'
            }`}
          >
            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
              index === 0 ? 'bg-yellow-500 text-black' :
              index === 1 ? 'bg-gray-400 text-black' :
              index === 2 ? 'bg-orange-600 text-white' :
              'bg-gray-600 text-white'
            }`}>
              {sales.rank}
            </div>
            
            {/* 信息 */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-white font-medium truncate">{sales.sales_name}</span>
                <span className="text-xs text-gray-400">{sales.team_name}</span>
              </div>
              <div className="flex items-center gap-3 text-xs text-gray-400 mt-0.5">
                <span>{sales.leads_count}线索</span>
                <span>{sales.converted_count}转化</span>
                {sales.follow_up_count !== undefined && (
                  <span>{sales.follow_up_count}跟进</span>
                )}
              </div>
            </div>
            
            {/* 转化率 */}
            <div className="text-right">
              <div className={`text-lg font-bold ${
                sales.conversion_rate >= 25 ? 'text-green-400' :
                sales.conversion_rate >= 18 ? 'text-yellow-400' :
                'text-gray-400'
              }`}>
                {sales.conversion_rate.toFixed(1)}%
              </div>
              {!compact && (
                <div className="text-xs text-gray-500">{sales.avg_response_time.toFixed(1)}h</div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
