import { Routes, Route, Navigate } from 'react-router-dom';
import { lazy, Suspense } from 'react';
import { Spin } from 'antd';
import { LoadingOutlined } from '@ant-design/icons';
import MainLayout from '@/layouts/MainLayout';

// 懒加载页面组件
const DashboardPage = lazy(() => import('@/pages/dashboard'));
const DiagnosisReportsPage = lazy(() => import('@/pages/diagnosis/reports'));
const DiagnosisDetailPage = lazy(() => import('@/pages/diagnosis/[diagnosisId]'));
const AnomalyDetailPage = lazy(() => import('@/pages/diagnosis/[diagnosisId]/anomaly/[anomalyId]'));
const DrillDownPage = lazy(() => import('@/pages/diagnosis/[diagnosisId]/drill-down/[metricName]'));
const SolutionsPage = lazy(() => import('@/pages/solutions'));
const SolutionDiagnosisPage = lazy(() => import('@/pages/solutions/[diagnosisId]'));
const ExecutionPage = lazy(() => import('@/pages/execution'));
const ExecutionDetailPage = lazy(() => import('@/pages/execution/[planId]'));
const TrackingPage = lazy(() => import('@/pages/tracking'));
const TrackingDetailPage = lazy(() => import('@/pages/tracking/[trackingId]'));
const TrackingReportPage = lazy(() => import('@/pages/tracking/[trackingId]/report'));
const TrackingCasesPage = lazy(() => import('@/pages/tracking/cases'));
const TrackingCaseDetailPage = lazy(() => import('@/pages/tracking/cases/[caseId]'));
const SettingsPage = lazy(() => import('@/pages/settings'));

const PageLoading = () => (
  <div className="flex items-center justify-center h-[60vh]">
    <Spin indicator={<LoadingOutlined style={{ fontSize: 48 }} spin />} />
  </div>
);

export default function App() {
  return (
    <Suspense fallback={<PageLoading />}>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route element={<MainLayout />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/diagnosis/reports" element={<DiagnosisReportsPage />} />
          <Route path="/diagnosis/:diagnosisId" element={<DiagnosisDetailPage />} />
          <Route path="/diagnosis/:diagnosisId/anomaly/:anomalyId" element={<AnomalyDetailPage />} />
          <Route path="/diagnosis/:diagnosisId/drill-down/:metricName" element={<DrillDownPage />} />
          <Route path="/solutions" element={<SolutionsPage />} />
          <Route path="/solutions/:diagnosisId" element={<SolutionDiagnosisPage />} />
          <Route path="/execution" element={<ExecutionPage />} />
          <Route path="/execution/:planId" element={<ExecutionDetailPage />} />
          <Route path="/tracking" element={<TrackingPage />} />
          <Route path="/tracking/cases" element={<TrackingCasesPage />} />
          <Route path="/tracking/cases/:caseId" element={<TrackingCaseDetailPage />} />
          <Route path="/tracking/:trackingId" element={<TrackingDetailPage />} />
          <Route path="/tracking/:trackingId/report" element={<TrackingReportPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </Suspense>
  );
}

