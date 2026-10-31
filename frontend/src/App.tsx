import React, { useCallback, useEffect, useState } from 'react';
import { Layout } from './components/Layout';
import { DashboardPage } from './pages/DashboardPage';
import { NewCheckPage } from './pages/NewCheckPage';
import { FilesPage } from './pages/FilesPage';
import { IssuesAnalysisPage } from './pages/IssuesAnalysisPage';
import { TranslationEditorPage } from './pages/TranslationEditorPage';
import { GlossaryPage } from './pages/GlossaryPage';
import { ReportsPage } from './pages/ReportsPage';
import { HistoryPage } from './pages/HistoryPage';
import { TeamPage } from './pages/TeamPage';
import { SettingsPage } from './pages/SettingsPage';
import { api } from './api/client';
import type {
  AppSettings,
  DashboardStats,
  PageId,
  ProjectRun,
  TeamMember,
} from './types';

export const App: React.FC = () => {
  const [activePage, setActivePage] = useState<PageId>('dashboard');
  const [activeLang, setActiveLang] = useState<'kk' | 'uz'>('kk');
  const [runs, setRuns] = useState<ProjectRun[]>([]);
  const [activeRunId, setActiveRunId] = useState<number | null>(null);
  const [dashboardStats, setDashboardStats] = useState<DashboardStats | null>(null);
  const [team, setTeam] = useState<TeamMember[]>([]);
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [loadingDash, setLoadingDash] = useState<boolean>(true);
  const [runningDemo, setRunningDemo] = useState<boolean>(false);
  const [backendOfflineMsg, setBackendOfflineMsg] = useState<string | null>(null);

  const refreshCoreData = useCallback(
    async (preferredRunId?: number | null) => {
      try {
        const [runsData, teamData, settingsData] = await Promise.all([
          api.listRuns(),
          api.listTeam(),
          api.getSettings(),
        ]);
        setBackendOfflineMsg(null);
        setRuns(runsData);
        setTeam(teamData);
        setSettings(settingsData);

        const targetRunId =
          preferredRunId !== undefined
            ? preferredRunId
            : activeRunId && runsData.some((r) => r.id === activeRunId)
            ? activeRunId
            : runsData[0]?.id ?? null;

        setActiveRunId(targetRunId);
        const dash = await api.getDashboard(targetRunId);
        setDashboardStats(dash);
      } catch (err) {
        const message =
          err instanceof Error
            ? err.message
            : 'Backend API серверімен (127.0.0.1:8000) байланыс уақытша үзілді.';
        setBackendOfflineMsg(message);
        console.warn('Backend temporarily unreachable; Frontend remains active:', err);
      } finally {
        setLoadingDash(false);
      }
    },
    [activeRunId]
  );

  useEffect(() => {
    refreshCoreData();
  }, []);

  useEffect(() => {
    if (!backendOfflineMsg) return;
    const timer = window.setInterval(() => {
      refreshCoreData();
    }, 5000);
    return () => window.clearInterval(timer);
  }, [backendOfflineMsg, refreshCoreData]);

  const handleSelectRun = async (runId: number) => {
    setActiveRunId(runId);
    const dash = await api.getDashboard(runId);
    setDashboardStats(dash);
  };

  const handleRunDemo = async () => {
    setRunningDemo(true);
    try {
      const demoRun = await api.runDemoCheck();
      await refreshCoreData(demoRun.id);
      setActivePage('dashboard');
    } finally {
      setRunningDemo(false);
    }
  };

  const handleDeleteRun = async (runId: number) => {
    await api.deleteRun(runId);
    await refreshCoreData(null);
  };

  const activeReviewer = team.find((m) => m.is_active_reviewer) || team[0] || null;

  return (
    <Layout
      activePage={activePage}
      onNavigate={setActivePage}
      runs={runs}
      activeRunId={activeRunId}
      onSelectRun={handleSelectRun}
      activeLang={activeLang}
      onSelectLang={setActiveLang}
      onRunDemo={handleRunDemo}
      activeReviewer={activeReviewer}
      settings={settings}
    >
      {backendOfflineMsg && (
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
          <div className="flex items-center gap-2.5">
            <span className="inline-block h-2.5 w-2.5 animate-pulse rounded-full bg-amber-400" />
            <span>
              <strong>Backend (8000) уақытша қолжетімсіз:</strong> {backendOfflineMsg} (Frontend дербес жұмыс істеп тұр, 5 сек сайын автоматты қайта қосылады)
            </span>
          </div>
          <button
            type="button"
            onClick={() => refreshCoreData()}
            className="rounded-lg border border-amber-400/40 bg-amber-500/20 px-3 py-1.5 text-xs font-medium text-amber-100 transition hover:bg-amber-500/30"
          >
            Қайта қосылу
          </button>
        </div>
      )}
      {activePage === 'dashboard' && (
        <DashboardPage
          stats={dashboardStats}
          loading={loadingDash}
          runningDemo={runningDemo}
          onRunDemo={handleRunDemo}
          onSelectRun={handleSelectRun}
          onNavigate={setActivePage}
        />
      )}

      {activePage === 'new-check' && (
        <NewCheckPage
          onRunCompleted={async (created) => {
            await refreshCoreData(created.id);
            setActivePage('issues');
          }}
          onRunDemo={handleRunDemo}
          runningDemo={runningDemo}
        />
      )}

      {activePage === 'files' && <FilesPage />}

      {activePage === 'issues' && (
        <IssuesAnalysisPage
          activeRunId={activeRunId}
          activeLang={activeLang}
          onSelectLang={setActiveLang}
          reviewerName={activeReviewer?.name}
          onStatsChanged={() => refreshCoreData(activeRunId)}
        />
      )}

      {activePage === 'editor' && (
        <TranslationEditorPage
          activeRunId={activeRunId}
          activeLang={activeLang}
          onSelectLang={setActiveLang}
          reviewerName={activeReviewer?.name}
          onStatsChanged={() => refreshCoreData(activeRunId)}
        />
      )}

      {activePage === 'glossary' && <GlossaryPage />}

      {activePage === 'reports' && (
        <ReportsPage
          activeRunId={activeRunId}
          activeLang={activeLang}
          onSelectLang={setActiveLang}
        />
      )}

      {activePage === 'history' && (
        <HistoryPage
          runs={runs}
          activeRunId={activeRunId}
          onSelectRun={handleSelectRun}
          onDeleteRun={handleDeleteRun}
          onNavigate={setActivePage}
        />
      )}

      {activePage === 'team' && (
        <TeamPage
          members={team}
          onRefreshTeam={async () => {
            const t = await api.listTeam();
            setTeam(t);
          }}
        />
      )}

      {activePage === 'settings' && (
        <SettingsPage
          settings={settings}
          onSettingsUpdated={(updated) => setSettings(updated)}
        />
      )}
    </Layout>
  );
};

export default App;
