import type { ReactNode } from 'react';

type Props = {
  /** 常驻语境（业务阶段），偏灰小字；省略时仅展示 transient */
  persistent?: ReactNode;
  /** 临时任务（完成追踪/复盘轮询），与 tracking 页现有样式一致 */
  transient?: ReactNode;
  /** 根节点 class，如与侧栏按钮并排时传入 `!mt-0` */
  className?: string;
};

/**
 * 标题区状态：有临时进度时只显示临时条（覆盖常驻）；否则显示常驻条。
 */
export function TrackingHeaderStatus({ persistent, transient, className }: Props) {
  const hasP = persistent != null && persistent !== '';
  const hasT = transient != null && transient !== false && transient !== undefined;
  if (!hasP && !hasT) return null;
  return (
    <div className={['mt-2', className].filter(Boolean).join(' ')}>
      {hasT ? (
        <div className="text-left">{transient}</div>
      ) : (
        <div className="text-left text-sm leading-relaxed text-[#909399]">{persistent}</div>
      )}
    </div>
  );
}
