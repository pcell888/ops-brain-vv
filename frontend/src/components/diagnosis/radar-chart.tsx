

import ReactECharts from 'echarts-for-react';
import { useMemo } from 'react';

export interface RadarDataItem {
  dimension: string;
  score: number;
}

interface RadarChartProps {
  data?: RadarDataItem[];
  benchmarkData?: RadarDataItem[];
  dimensionNameMap?: Record<string, string>; // 动态维度名称映射
}

// 默认维度名称映射（系统维度，仅作为 fallback）
// 优先使用传入的 dimensionNameMap prop（从 useDimensionConfig hook 获取）
const defaultDimensionNameMapping: Record<string, string> = {
  crm_sharing: 'CRM共享',
  crm: 'CRM共享',
  marketing: '营销效果',
  marketing_effect: '营销效果',
  retention: '客户留存',
  customer_retention: '客户留存',
  efficiency: '运营效率',
  operation_efficiency: '运营效率',
};

// 默认数据
const defaultData: RadarDataItem[] = [
  { dimension: 'crm', score: 65 },
  { dimension: 'efficiency', score: 67 },
  { dimension: 'retention', score: 82 },
  { dimension: 'marketing', score: 58 },
];

const defaultBenchmark: RadarDataItem[] = [
  { dimension: 'crm', score: 75 },
  { dimension: 'efficiency', score: 78 },
  { dimension: 'retention', score: 72 },
  { dimension: 'marketing', score: 70 },
];

// 维度不足时显示条形图
function BarChartFallback({ 
  data, 
  nameMapping 
}: { 
  data: RadarDataItem[]; 
  nameMapping: Record<string, string>;
}) {
  const option = useMemo(() => ({
    grid: {
      left: '3%',
      right: '10%',
      top: '15%',
      bottom: '15%',
      containLabel: true,
    },
    xAxis: {
      type: 'value',
      max: 100,
      axisLine: { lineStyle: { color: 'rgba(59, 130, 246, 0.3)' } },
      splitLine: { lineStyle: { color: 'rgba(59, 130, 246, 0.1)' } },
      axisLabel: { color: '#94a3b8', formatter: '{value}分' },
    },
    yAxis: {
      type: 'category',
      data: data.map(d => nameMapping[d.dimension] || d.dimension),
      axisLine: { lineStyle: { color: 'rgba(59, 130, 246, 0.3)' } },
      axisLabel: { color: '#94a3b8', fontSize: 13 },
    },
    series: [
      {
        name: '得分',
        type: 'bar',
        data: data.map(d => ({
          value: d.score,
          itemStyle: {
            color: {
              type: 'linear',
              x: 0, y: 0, x2: 1, y2: 0,
              colorStops: [
                { offset: 0, color: 'rgba(59, 130, 246, 0.8)' },
                { offset: 1, color: 'rgba(139, 92, 246, 0.6)' },
              ],
            },
            borderRadius: [0, 4, 4, 0],
          },
        })),
        barWidth: 24,
        label: {
          show: true,
          position: 'right',
          color: '#94a3b8',
          formatter: '{c}分',
        },
      },
      {
        name: '行业基准',
        type: 'scatter',
        symbol: 'diamond',
        symbolSize: 12,
        data: data.map(() => 70), // 默认基准 70
        itemStyle: { color: 'rgba(6, 182, 212, 0.8)' },
        label: {
          show: false,
        },
      },
    ],
    legend: {
      data: ['得分', '行业基准'],
      bottom: 0,
      textStyle: { color: '#94a3b8', fontSize: 12 },
      itemWidth: 16,
      itemHeight: 8,
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(26, 34, 52, 0.95)',
      borderColor: 'rgba(59, 130, 246, 0.3)',
      textStyle: { color: '#f1f5f9' },
    },
  }), [data, nameMapping]);

  return <ReactECharts option={option} style={{ height: '300px' }} />;
}

export function RadarChart({ data, benchmarkData, dimensionNameMap }: RadarChartProps) {
  // 合并默认映射和传入的动态映射
  const nameMapping = useMemo(() => ({
    ...defaultDimensionNameMapping,
    ...dimensionNameMap,
  }), [dimensionNameMap]);

  // 使用传入数据或默认数据
  const chartData = data && data.length > 0 ? data : defaultData;
  const benchmark = benchmarkData && benchmarkData.length > 0 ? benchmarkData : defaultBenchmark;

  // 维度数量少于 3 个时，使用条形图替代
  if (chartData.length < 3) {
    return (
      <div className="relative">
        <div className="absolute top-0 right-0 text-xs text-gray-500 bg-gray-800/50 px-2 py-1 rounded">
          维度少于3个，使用条形图展示
        </div>
        <BarChartFallback data={chartData} nameMapping={nameMapping} />
      </div>
    );
  }

  // 构建图表配置
  const option = useMemo(() => {
    // 构建指标配置
    const indicators = chartData.map(item => ({
      name: nameMapping[item.dimension] || item.dimension,
      min: 0,
      max: 100,
    }));

    // 确保维度顺序一致
    const myValues = chartData.map(item => item.score);
    const benchmarkValues = chartData.map(item => {
      const benchItem = benchmark.find(b => b.dimension === item.dimension);
      return benchItem?.score || 70;
    });

    return {
      radar: {
        center: ['50%', '48%'],
        radius: '65%',
        indicator: indicators,
        shape: 'polygon',
        splitNumber: 5,
        scale: false,
        axisName: {
          color: '#94a3b8',
          fontSize: 13,
          fontWeight: 500,
          padding: [0, 0, 0, 0],
        },
        splitLine: {
          lineStyle: {
            color: ['rgba(59, 130, 246, 0.1)', 'rgba(59, 130, 246, 0.13)', 'rgba(59, 130, 246, 0.16)', 'rgba(59, 130, 246, 0.2)', 'rgba(59, 130, 246, 0.25)'],
            width: 1,
          },
        },
        splitArea: {
          show: true,
          areaStyle: {
            color: ['rgba(59, 130, 246, 0.02)', 'rgba(59, 130, 246, 0.03)', 'rgba(59, 130, 246, 0.05)', 'rgba(59, 130, 246, 0.07)', 'rgba(59, 130, 246, 0.09)'],
          },
        },
        axisLine: {
          lineStyle: {
            color: 'rgba(59, 130, 246, 0.2)',
          },
        },
      },
      series: [
        {
          type: 'radar',
          symbol: 'circle',
          symbolSize: 6,
          data: [
            {
              value: myValues,
              name: '我的企业',
              areaStyle: {
                color: {
                  type: 'linear',
                  x: 0, y: 0, x2: 0, y2: 1,
                  colorStops: [
                    { offset: 0, color: 'rgba(59, 130, 246, 0.4)' },
                    { offset: 1, color: 'rgba(139, 92, 246, 0.1)' },
                  ],
                },
              },
              lineStyle: {
                color: '#3b82f6',
                width: 2,
                shadowColor: 'rgba(59, 130, 246, 0.5)',
                shadowBlur: 10,
              },
              itemStyle: {
                color: '#3b82f6',
                borderColor: '#fff',
                borderWidth: 2,
                shadowColor: 'rgba(59, 130, 246, 0.5)',
                shadowBlur: 8,
              },
            },
            {
              value: benchmarkValues,
              name: '行业基准',
              areaStyle: {
                color: 'rgba(6, 182, 212, 0.08)',
              },
              lineStyle: {
                color: 'rgba(6, 182, 212, 0.6)',
                width: 2,
                type: 'dashed',
              },
              itemStyle: {
                color: 'rgba(6, 182, 212, 0.8)',
                borderColor: 'rgba(6, 182, 212, 0.3)',
                borderWidth: 2,
              },
            },
          ],
        },
      ],
      legend: {
        data: [
          {
            name: '我的企业',
            icon: 'roundRect',
          },
          {
            name: '行业基准',
            icon: 'roundRect',
          },
        ],
        bottom: 10,
        itemWidth: 16,
        itemHeight: 8,
        itemGap: 24,
        textStyle: {
          color: '#94a3b8',
          fontSize: 12,
        },
      },
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(26, 34, 52, 0.95)',
        borderColor: 'rgba(59, 130, 246, 0.3)',
        borderWidth: 1,
        textStyle: {
          color: '#f1f5f9',
        },
        formatter: (params: { name: string; value: number[] }) => {
          const lines = indicators.map((ind, i) => 
            `${ind.name}: ${Math.round(params.value[i])}分`
          );
          return `<strong>${params.name}</strong><br/>${lines.join('<br/>')}`;
        },
      },
    };
  }, [chartData, benchmark, nameMapping]);

  return <ReactECharts option={option} style={{ height: '300px' }} />;
}
