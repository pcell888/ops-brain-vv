

import ReactECharts from 'echarts-for-react';
import { useMemo } from 'react';

interface PieChartData {
  name: string;
  value: number;
}

interface PieChartProps {
  data: PieChartData[];
  title?: string;
  height?: number | string;
  colors?: string[];
}

// 默认颜色方案（深色主题）
const defaultColors = [
  '#8b5cf6', // purple-500
  '#3b82f6', // blue-500
  '#06b6d4', // cyan-500
  '#10b981', // emerald-500
  '#f59e0b', // amber-500
  '#ef4444', // red-500
  '#ec4899', // pink-500
  '#6366f1', // indigo-500
];

export function PieChart({ 
  data, 
  title, 
  height = 300,
  colors = defaultColors 
}: PieChartProps) {
  const option = useMemo(() => {
    // 计算总数用于显示百分比
    const total = data.reduce((sum, item) => sum + item.value, 0);

    return {
      title: title ? {
        text: title,
        left: 'center',
        top: 10,
        textStyle: {
          color: '#f1f5f9',
          fontSize: 16,
          fontWeight: 600,
        },
      } : undefined,
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(26, 34, 52, 0.95)',
        borderColor: 'rgba(139, 92, 246, 0.3)',
        borderWidth: 1,
        textStyle: {
          color: '#f1f5f9',
        },
        formatter: (params: { name: string; value: number; percent: number }) => {
          return `
            <div style="padding: 4px 0;">
              <div style="font-weight: 600; margin-bottom: 4px;">${params.name}</div>
              <div style="color: #94a3b8;">
                数量: <span style="color: #8b5cf6; font-weight: 600;">${params.value}</span>
              </div>
              <div style="color: #94a3b8;">
                占比: <span style="color: #8b5cf6; font-weight: 600;">${params.percent}%</span>
              </div>
            </div>
          `;
        },
      },
      legend: {
        orient: 'vertical',
        left: 'left',
        top: 'middle',
        textStyle: {
          color: '#94a3b8',
          fontSize: 12,
        },
        itemWidth: 12,
        itemHeight: 12,
        itemGap: 12,
        formatter: (name: string) => {
          const item = data.find(d => d.name === name);
          if (!item) return name;
          const percent = ((item.value / total) * 100).toFixed(1);
          return `${name} (${percent}%)`;
        },
      },
      series: [
        {
          name: title || '分布',
          type: 'pie',
          radius: ['40%', '70%'], // 环形图
          center: ['60%', '50%'],
          avoidLabelOverlap: false,
          itemStyle: {
            borderRadius: 8,
            borderColor: 'rgba(15, 23, 42, 0.8)',
            borderWidth: 2,
          },
          label: {
            show: true,
            position: 'outside',
            formatter: (params: { name: string; percent: number }) => {
              return `${params.name}\n${params.percent}%`;
            },
            color: '#f1f5f9',
            fontSize: 12,
            fontWeight: 500,
          },
          labelLine: {
            show: true,
            length: 15,
            length2: 10,
            lineStyle: {
              color: 'rgba(139, 92, 246, 0.3)',
            },
          },
          emphasis: {
            itemStyle: {
              shadowBlur: 20,
              shadowOffsetX: 0,
              shadowColor: 'rgba(139, 92, 246, 0.5)',
            },
            label: {
              fontSize: 14,
              fontWeight: 600,
            },
          },
          data: data.map((item, index) => ({
            ...item,
            itemStyle: {
              color: colors[index % colors.length],
            },
          })),
        },
      ],
    };
  }, [data, title, colors]);

  return <ReactECharts option={option} style={{ height }} />;
}

