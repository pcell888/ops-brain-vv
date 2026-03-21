import type { ExecutionTask } from '@/lib/types';

/** 列表主列只保留标题；说明与实施步骤放在展开区，贴近业务待办列表习惯 */
export function ExecutionTaskExpandedRow({ record }: { record: ExecutionTask }) {
  const desc = (record.description || '').trim();
  const name = (record.name || '').trim();
  const showDesc = Boolean(desc && desc !== name);
  const steps = record.implementation_steps?.filter(Boolean) || [];

  return (
    <div className="bg-gray-900/40 border border-gray-700/50 rounded-lg p-3 text-sm max-w-4xl">
      {showDesc && (
        <p className="text-gray-400 mb-2 whitespace-pre-wrap break-words">{desc}</p>
      )}
      {steps.length > 0 && (
        <>
          <div className="text-gray-500 text-xs mb-1">实施步骤</div>
          <ol className="list-decimal pl-4 text-gray-300 space-y-1">
            {steps.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ol>
        </>
      )}
    </div>
  );
}
