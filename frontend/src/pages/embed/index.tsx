import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Spin, Result } from 'antd';
import { LoadingOutlined } from '@ant-design/icons';
import { enterpriseApi } from '@/lib/api';
import { applyEmbedSession } from '@/lib/session';
import { useAppStore } from '@/stores/app-store';

function mapEnterprise(raw: Record<string, unknown>) {
  return {
    id: String(raw.id ?? ''),
    name: String(raw.name ?? ''),
    industry: (raw.industry as string) ?? null,
    scale: (raw.scale as string) ?? null,
  };
}

export default function EmbedPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const setCurrentEnterprise = useAppStore((s) => s.setCurrentEnterprise);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const projectId =
      searchParams.get('project_id')?.trim() ||
      searchParams.get('projectId')?.trim() ||
      '';
    const userToken =
      searchParams.get('user_token')?.trim() || searchParams.get('userToken')?.trim() || '';
    const platformToken =
      searchParams.get('platform_token')?.trim() ||
      searchParams.get('platfrom_token')?.trim() ||
      searchParams.get('platformToken')?.trim() ||
      '';

    if (!projectId || !userToken || !platformToken) {
      setError('缺少必要参数：project_id、user_token、platform_token');
      return;
    }

    let cancelled = false;

    (async () => {
      try {
        applyEmbedSession({ projectId, userToken, platformToken });
        const res = await enterpriseApi.sync(projectId, { name: projectId });
        if (cancelled) return;
        const ent = res.enterprise as Record<string, unknown>;
        setCurrentEnterprise(mapEnterprise(ent));
        navigate('/dashboard', { replace: true });
      } catch (e) {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : '同步企业失败');
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [searchParams, navigate, setCurrentEnterprise]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#F0F1F9] p-6">
        <Result status="error" title="无法进入应用" subTitle={error} />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#F0F1F9]">
      <Spin indicator={<LoadingOutlined style={{ fontSize: 40 }} spin />} tip="正在同步企业…" />
    </div>
  );
}
