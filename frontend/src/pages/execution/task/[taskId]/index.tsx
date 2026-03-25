import { useNavigate, useParams } from 'react-router-dom';
import {
  Card, Button, Empty, Spin, Descriptions, Tag, App,
} from 'antd';
import {
  ArrowLeftOutlined, LoadingOutlined, RocketOutlined,
} from '@ant-design/icons';
import { useTaskDetail } from '@/lib/hooks';
import dayjs from 'dayjs';
import { formatTaskDeadlineDisplay } from '@/lib/execution-task-utils';
import { DispatchStatusTag } from '@/lib/dispatch-status';

export default function ExecutionTaskDetailPage() {
  const { taskId } = useParams();
  const navigate = useNavigate();
  const { message } = App.useApp();
  const id = taskId ? decodeURIComponent(taskId) : null;
  const { data, isLoading, error } = useTaskDetail(id);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <Spin indicator={<LoadingOutlined style={{ fontSize: 48 }} spin />} />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="space-y-4">
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)}>返回</Button>
        <Empty description="任务不存在或加载失败" />
      </div>
    );
  }

  const steps = data.implementation_steps?.filter(Boolean) || [];
  const copy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      message.success('已复制');
    } catch {
      message.error('复制失败');
    }
  };

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex flex-wrap items-center gap-2 justify-between">
        <div className="flex items-center gap-3">
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)} style={{ backgroundColor: '#fff', color: '#000', border: '1px solid #d9d9d9' }}>返回</Button>
          <h1 className="text-xl font-bold text-[#303133] flex items-center gap-2">
            <span className="w-9 h-9 text-[#fff] rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center">
              <RocketOutlined />
            </span>
            任务详情
          </h1>
        </div>
      </div>

      <Card title="派发信息" className="border-gray-700">
        <Descriptions column={1} size="small" labelStyle={{ color: '#9ca3af', width: 120 }}>
          <Descriptions.Item label="任务名称">
            <span className="text-[#303133] font-medium">{data.name || '—'}</span>
          </Descriptions.Item>
          <Descriptions.Item label="接收者">
            {data.recipient || data.assigned_to || '—'}
          </Descriptions.Item>
          <Descriptions.Item label="派发时间">
            {data.dispatch_time || data.scheduled_start
              ? dayjs(data.dispatch_time || data.scheduled_start).format('YYYY-MM-DD HH:mm:ss')
              : '—'}
          </Descriptions.Item>
          <Descriptions.Item label="派发状态">
            <DispatchStatusTag status={data.dispatch_status} />
          </Descriptions.Item>
          <Descriptions.Item label="期限说明">
            {data.scheduled_end ? formatTaskDeadlineDisplay(data.scheduled_end) : '—'}
          </Descriptions.Item>
          <Descriptions.Item label="执行方式">
            <Tag>{data.execution_type || '—'}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="诊断 ID">
            {data.thread_id || '—'}
            {data.thread_id && (
              <Button type="link" size="small" className="!ml-2" onClick={() => copy(data.thread_id!)}>
                复制
              </Button>
            )}
          </Descriptions.Item>
          <Descriptions.Item label="计划 ID">
            {data.plan_id || '—'}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title="业务内容" className="border-gray-700">
        <div className="text-[#303133] whitespace-pre-wrap break-words leading-relaxed">
          {data.description?.trim() || '—'}
        </div>
      </Card>

      {steps.length > 0 && (
        <Card title="实施步骤" className="border-gray-700">
          <ol className="list-decimal pl-5 space-y-2 text-[#303133]">
            {steps.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ol>
        </Card>
      )}
    </div>
  );
}
