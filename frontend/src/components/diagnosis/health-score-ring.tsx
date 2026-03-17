

import { Progress } from 'antd';

interface HealthScoreRingProps {
  score: number;
}

export function HealthScoreRing({ score }: HealthScoreRingProps) {
  const getScoreLevel = () => {
    if (score >= 80) return { color: 'from-emerald-400 to-teal-500', glow: 'rgba(16, 185, 129, 0.4)' };
    if (score >= 60) return { color: 'from-blue-400 to-purple-500', glow: 'rgba(59, 130, 246, 0.4)' };
    if (score >= 40) return { color: 'from-amber-400 to-orange-500', glow: 'rgba(245, 158, 11, 0.4)' };
    return { color: 'from-rose-400 to-red-500', glow: 'rgba(244, 63, 94, 0.4)' };
  };

  const level = getScoreLevel();

  return (
    <div className="relative inline-block">
      {/* 外发光效果 */}
      <div 
        className="absolute inset-0 rounded-full blur-2xl opacity-50 scale-90"
        style={{ 
          background: `radial-gradient(circle, ${level.glow} 0%, transparent 70%)`,
        }}
      />
      
      {/* 装饰性外圈 */}
      <div className="absolute inset-[-8px] rounded-full border border-white/5" />
      <div className="absolute inset-[-16px] rounded-full border border-white/[0.02]" />
      
      <Progress
        type="circle"
        percent={score}
        size={200}
        strokeColor={{
          '0%': '#3b82f6',
          '50%': '#8b5cf6',
          '100%': '#a855f7',
        }}
        trailColor="rgba(45, 58, 82, 0.5)"
        strokeWidth={10}
        format={() => (
          <div className="text-center">
            <div className={`text-5xl font-bold bg-gradient-to-r ${level.color} bg-clip-text text-transparent drop-shadow-lg`}>
              {Number.isInteger(score) ? score : score.toFixed(1)}
            </div>
            <div className="text-gray-400 text-sm mt-1 tracking-wide">健康评分</div>
          </div>
        )}
      />
      
      {/* 内部装饰圆点 */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[140px] h-[140px] rounded-full border border-dashed border-white/5" />
    </div>
  );
}
