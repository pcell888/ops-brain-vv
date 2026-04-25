import { Button } from 'antd';

/** 与轮询类标题区进度条一致：progress / completed / error */
export type HeaderAsyncProgressLine = { message: string; type: string };

type Props = {
  line: HeaderAsyncProgressLine;
  /** type 为 progress 且无 message 时的占位文案 */
  progressPlaceholder?: string;
  /** type 为 completed 且无 message 时的默认主文案 */
  completedFallback?: string;
  /** 完成后显示的链接文案，不传则不显示链接 */
  completedLinkLabel?: string;
  onCompletedLink?: () => void;
  /** 为 false 时错误态仅一行文案，不展示关闭/重试（采纳场景） */
  showErrorActions?: boolean;
  onDismissError?: () => void;
  onRetryError?: () => void;
  retryLoading?: boolean;
};

/**
 * 标题区异步任务进度：主文案 + 完成后的链接 + 失败时的关闭/重试。
 */
export function HeaderAsyncProgress({
  line,
  progressPlaceholder = '正在处理中，请稍候…',
  completedFallback = '已完成',
  completedLinkLabel,
  onCompletedLink,
  showErrorActions = true,
  onDismissError,
  onRetryError,
  retryLoading,
}: Props) {
  const { message, type } = line;
  const mainText =
    type === 'completed'
      ? message || completedFallback
      : message || (type === 'progress' ? progressPlaceholder : '');

  const errorPlain = type === 'error' && showErrorActions === false;

  return (
    <div className="text-left">
      <p
        className={`text-sm ${type === 'error' ? 'text-red-600' : 'text-[#606266]'} ${
          errorPlain ? 'block max-w-full truncate' : ''
        }`}
      >
        {mainText}
      </p>
      {type === 'completed' && completedLinkLabel && onCompletedLink && (
        <Button type="link" size="small" className="mt-1 h-auto p-0" onClick={onCompletedLink}>
          {completedLinkLabel}
        </Button>
      )}
      {type === 'error' && showErrorActions && onDismissError && onRetryError && (
        <div className="mt-1 flex flex-wrap gap-x-3">
          <Button type="link" size="small" className="h-auto p-0" onClick={onDismissError}>
            关闭提示
          </Button>
          <Button
            type="link"
            size="small"
            className="h-auto p-0"
            loading={retryLoading}
            onClick={onRetryError}
          >
            重试
          </Button>
        </div>
      )}
    </div>
  );
}
