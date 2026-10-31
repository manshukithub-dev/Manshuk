import React from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  Flame,
  Wrench,
  UserCheck,
  Clock,
  Globe2,
  Play,
  UploadCloud,
  Download,
  ArrowRight,
  Sparkles,
  Activity,
  History,
  ArrowUpRight,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  AreaChart,
  Area,
  Legend,
  Cell,
  PieChart,
  Pie,
} from 'recharts';
import type { DashboardStats, PageId } from '../types';
import { downloadBlob } from '../api/client';

interface DashboardPageProps {
  stats: DashboardStats | null;
  loading: boolean;
  runningDemo: boolean;
  onRunDemo: () => void;
  onSelectRun: (runId: number) => void;
  onNavigate: (page: PageId) => void;
}

const QualityRing: React.FC<{
  score: number | null;
  label: string;
  sublabel: string;
  color: string;
}> = ({ score, label, sublabel, color }) => {
  const radius = 36;
  const circumference = 2 * Math.PI * radius;
  const numeric = score ?? 0;
  const offset = circumference - (Math.min(100, Math.max(0, numeric)) / 100) * circumference;

  return (
    <div className="flex items-center gap-4">
      <div className="relative w-20 h-20 shrink-0">
        <svg className="w-20 h-20 -rotate-90" viewBox="0 0 88 88">
          <circle
            cx="44"
            cy="44"
            r={radius}
            fill="none"
            stroke="rgba(255,255,255,0.07)"
            strokeWidth="7"
          />
          {score !== null && (
            <circle
              cx="44"
              cy="44"
              r={radius}
              fill="none"
              stroke={color}
              strokeWidth="7"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              className="transition-all duration-700 ease-out"
            />
          )}
        </svg>
        <div className="absolute inset-0 flex items-center justify-center font-mono text-sm font-extrabold text-white">
          {score !== null ? `${score.toFixed(0)}%` : '—'}
        </div>
      </div>
      <div>
        <div className="text-xs font-bold text-slate-200">{label}</div>
        <div className="text-xl font-black text-white mt-0.5">
          {score !== null ? `${score.toFixed(1)}%` : 'Жоқ'}
        </div>
        <div className="text-[11px] text-slate-400 mt-0.5">{sublabel}</div>
      </div>
    </div>
  );
};

export const DashboardPage: React.FC<DashboardPageProps> = ({
  stats,
  loading,
  runningDemo,
  onRunDemo,
  onSelectRun,
  onNavigate,
}) => {
  if (loading && !stats) {
    return (
      <div className="flex items-center justify-center py-28 text-slate-400 text-sm gap-2">
        <Activity className="w-4 h-4 text-cyan-400 animate-spin" />
        <span>SQLite базасынан статистика жүктелуде...</span>
      </div>
    );
  }

  const hasRuns = Boolean(stats?.has_runs && stats.active_run);
  const activeRun = stats?.active_run || null;

  const highCnt = stats?.high_severity_issues ?? 0;
  const medCnt =
    stats?.medium_severity_issues ??
    stats?.severity_breakdown.find((s) => s.severity === 'Medium')?.count ??
    0;
  const lowCnt =
    stats?.low_severity_issues ??
    stats?.severity_breakdown.find((s) => s.severity === 'Low')?.count ??
    0;
  const totalIssues = stats?.total_issues ?? 0;
  const totalChecked = stats?.total_checked_strings ?? 0;
  const humanReviewed = stats?.human_reviewed_strings ?? 0;
  const reviewRatio = totalChecked > 0 ? Math.round((humanReviewed / totalChecked) * 100) : 0;

  const barColors = [
    '#38bdf8',
    '#8b5cf6',
    '#f43f5e',
    '#f59e0b',
    '#10b981',
    '#ec4899',
    '#6366f1',
    '#14b8a6',
  ];

  const pieData = (stats?.severity_breakdown || []).filter((d) => d.count > 0);

  return (
    <div className="space-y-6">
      {/* Top Hero / Active Run Command Banner */}
      {!hasRuns ? (
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-[#0B132B] via-[#0F172A] to-[#1E1B4B] border border-cyan-400/25 p-7 sm:p-9 shadow-[0_20px_50px_-15px_rgba(56,189,248,0.22)]">
          <div className="absolute -top-24 -right-24 w-72 h-72 rounded-full bg-cyan-500/15 blur-3xl pointer-events-none" />
          <div className="absolute -bottom-24 left-1/3 w-72 h-72 rounded-full bg-violet-600/15 blur-3xl pointer-events-none" />

          <div className="relative flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
            <div className="space-y-3 max-w-2xl">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-400/10 border border-cyan-400/30 text-cyan-300 text-xs font-bold">
                <Sparkles className="w-3.5 h-3.5" />
                <span>AI Localization QA • Шынайы SQLite деректер режимі</span>
              </div>
              <h2 className="text-2xl sm:text-3xl font-black tracking-tight text-white">
                Мобильді ойындардың Қазақша және Өзбекше локализация сапасын тексеріңіз
              </h2>
              <p className="text-sm text-slate-300 leading-relaxed">
                Деректер базасында әзірге тексеру жазбалары жоқ. Өзіңіздің{' '}
                <code className="font-mono text-cyan-300">intl_ru.arb</code>,{' '}
                <code className="font-mono text-cyan-300">intl_kk.arb</code>,{' '}
                <code className="font-mono text-cyan-300">intl_uz.arb</code> файлдарыңызды жүктеңіз
                немесе <span className="text-amber-300 font-bold">[DEMO]</span> үлгі жобасын бір
                батырмамен іске қосыңыз.
              </p>
            </div>

            <div className="flex flex-wrap gap-3 shrink-0">
              <button
                onClick={() => onNavigate('new-check')}
                className="btn-primary px-5 py-3 text-sm"
              >
                <UploadCloud className="w-4 h-4" />
                <span>ARB файлдарын жүктеу</span>
              </button>
              <button
                disabled={runningDemo}
                onClick={onRunDemo}
                className="inline-flex items-center gap-2 px-5 py-3 rounded-xl bg-amber-500/15 hover:bg-amber-500/25 border border-amber-400/40 text-amber-200 text-sm font-bold transition disabled:opacity-50"
              >
                <Play className="w-4 h-4 text-amber-400" />
                <span>{runningDemo ? 'DEMO орындалуда...' : '[DEMO] Үлгі жобаны іске қосу'}</span>
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="saas-card p-5 sm:p-6 border-cyan-500/20 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2.5 flex-wrap">
              <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-cyan-300 bg-cyan-500/10 border border-cyan-500/25 px-2.5 py-0.5 rounded-full">
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
                Белсенді жоба #{activeRun?.id}
              </span>
              <h2 className="text-base sm:text-lg font-extrabold text-white">{activeRun?.name}</h2>
              {activeRun?.is_demo && (
                <span className="px-2 py-0.5 text-[10px] font-extrabold rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40">
                  DEMO
                </span>
              )}
              <span className="text-xs font-mono text-slate-400">
                • {activeRun?.duration_ms} мс • SQLite синхрондалған
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Финалдық тексерілген аударма ретінде тек маман растаған (
              <code className="font-mono text-emerald-300">reviewed_by_human = true</code>) жолдар
              есептеледі.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5 shrink-0">
            <button
              onClick={() => onNavigate('issues')}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-rose-500/15 hover:bg-rose-500/25 border border-rose-500/35 text-rose-200 text-xs font-bold transition"
            >
              <span>Қателерді талдау ({totalIssues})</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => onNavigate('editor')}
              className="btn-secondary px-4 py-2 text-xs"
            >
              <span>Аударма редакторы</span>
            </button>
            {activeRun?.has_kk && (
              <button
                onClick={() =>
                  downloadBlob(
                    `/api/reports/${activeRun.id}/export-arb?lang=kk`,
                    'intl_kk_fixed.arb'
                  )
                }
                className="btn-primary px-4 py-2 text-xs"
              >
                <Download className="w-3.5 h-3.5" />
                <span>intl_kk_fixed.arb</span>
              </button>
            )}
          </div>
        </div>
      )}

      {/* Primary KPI Bento Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {/* Card 1: Total Checked Translations */}
        <div className="saas-card-hover p-5 flex flex-col justify-between gap-4">
          <div className="flex items-start justify-between">
            <div>
              <div className="text-xs font-semibold text-slate-400">
                Жалпы тексерілген аудармалар
              </div>
              <div className="text-3xl font-black text-white mt-2 font-mono">{totalChecked}</div>
            </div>
            <div className="p-2.5 rounded-xl bg-cyan-500/10 border border-cyan-500/25 text-cyan-400">
              <Globe2 className="w-5 h-5" />
            </div>
          </div>
          <div className="flex items-center justify-between text-[11px] text-slate-400 pt-2 border-t border-white/[0.06]">
            <span>Базадағы жобалар саны:</span>
            <span className="font-mono font-bold text-cyan-300">{stats?.total_runs_count ?? 0}</span>
          </div>
        </div>

        {/* Card 2: Found Issues + High/Medium/Low Segmented Breakdown */}
        <div
          onClick={() => hasRuns && onNavigate('issues')}
          className="saas-card-hover p-5 flex flex-col justify-between gap-4 cursor-pointer"
        >
          <div className="flex items-start justify-between">
            <div>
              <div className="text-xs font-semibold text-slate-400">
                Табылған қателер (High / Med / Low)
              </div>
              <div className="flex items-baseline gap-2.5 mt-2">
                <span className="text-3xl font-black text-rose-400 font-mono">{totalIssues}</span>
                <span className="text-xs text-slate-400">мәселе</span>
              </div>
            </div>
            <div className="p-2.5 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-400">
              <Flame className="w-5 h-5" />
            </div>
          </div>

          <div className="space-y-2">
            <div className="w-full h-2 rounded-full bg-white/[0.06] overflow-hidden flex">
              {totalIssues > 0 && (
                <>
                  <div
                    style={{ width: `${(highCnt / totalIssues) * 100}%` }}
                    className="bg-rose-500 h-full"
                  />
                  <div
                    style={{ width: `${(medCnt / totalIssues) * 100}%` }}
                    className="bg-amber-400 h-full"
                  />
                  <div
                    style={{ width: `${(lowCnt / totalIssues) * 100}%` }}
                    className="bg-sky-400 h-full"
                  />
                </>
              )}
            </div>
            <div className="flex items-center justify-between text-[11px] font-mono">
              <span className="text-rose-300 font-bold">High: {highCnt}</span>
              <span className="text-amber-300 font-bold">Med: {medCnt}</span>
              <span className="text-sky-300 font-bold">Low: {lowCnt}</span>
            </div>
          </div>
        </div>

        {/* Card 3: Human Reviewed Translations */}
        <div
          onClick={() => hasRuns && onNavigate('editor')}
          className="saas-card-hover p-5 flex flex-col justify-between gap-4 cursor-pointer"
        >
          <div className="flex items-start justify-between">
            <div>
              <div className="text-xs font-semibold text-slate-400">
                Адам тексерген аудармалар
              </div>
              <div className="flex items-baseline gap-2 mt-2">
                <span className="text-3xl font-black text-emerald-400 font-mono">
                  {humanReviewed}
                </span>
                <span className="text-xs text-slate-400">/ {totalChecked}</span>
              </div>
            </div>
            <div className="p-2.5 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-400">
              <UserCheck className="w-5 h-5" />
            </div>
          </div>

          <div className="space-y-1.5">
            <div className="w-full h-2 rounded-full bg-white/[0.06] overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-emerald-400 to-cyan-400 transition-all duration-500"
                style={{ width: `${reviewRatio}%` }}
              />
            </div>
            <div className="flex items-center justify-between text-[11px] text-slate-400">
              <span className="flex items-center gap-1">
                <Wrench className="w-3 h-3 text-violet-400" />
                Түзетілді: <b className="text-slate-200">{stats?.fixed_strings ?? 0}</b>
              </span>
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3 text-amber-400" />
                Қалғаны: <b className="text-amber-300">{stats?.unreviewed_strings ?? 0}</b>
              </span>
            </div>
          </div>
        </div>

        {/* Card 4: Localization Quality Score Gauges (KK & UZ) */}
        <div className="saas-card-hover p-5 flex flex-col justify-center gap-3">
          <QualityRing
            score={hasRuns ? stats?.kk_quality_score ?? 0 : null}
            label="Қазақша сапа (KK)"
            sublabel={
              hasRuns && stats?.uz_quality_score !== null && stats?.uz_quality_score !== undefined
                ? `Өзбекше (UZ): ${stats.uz_quality_score.toFixed(1)}%`
                : 'Негізгі локализация индексі'
            }
            color="#10b981"
          />
        </div>
      </div>

      {/* Analytics Row: Issues by Category + Severity Donut */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Horizontal Bar Chart: 12 QA Error Types */}
        <div className="xl:col-span-2 saas-card p-6 space-y-4">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div>
              <h3 className="text-sm font-bold text-white">Қателер диаграммасы (түрлері бойынша)</h3>
              <p className="text-xs text-slate-400">
                12 интеллектуалды QA ережесі бойынша табылған ауытқулар
              </p>
            </div>
            <span className="text-[11px] font-mono px-2.5 py-1 rounded-lg bg-white/[0.04] border border-white/[0.07] text-cyan-300">
              SQLite Live
            </span>
          </div>

          {hasRuns && stats && stats.issues_by_type.length > 0 ? (
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={stats.issues_by_type}
                  layout="vertical"
                  margin={{ top: 4, right: 24, left: 16, bottom: 4 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                  <XAxis type="number" stroke="#94a3b8" fontSize={11} allowDecimals={false} />
                  <YAxis
                    type="category"
                    dataKey="label"
                    stroke="#e2e8f0"
                    fontSize={11}
                    width={160}
                  />
                  <Tooltip
                    cursor={{ fill: 'rgba(255,255,255,0.03)' }}
                    contentStyle={{
                      backgroundColor: '#0A0F1E',
                      borderColor: 'rgba(255,255,255,0.12)',
                      borderRadius: '12px',
                      fontSize: '12px',
                      color: '#f8fafc',
                    }}
                  />
                  <Bar dataKey="count" name="Қате саны" radius={[0, 8, 8, 0]}>
                    {stats.issues_by_type.map((_, index) => (
                      <Cell key={index} fill={barColors[index % barColors.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-72 flex flex-col items-center justify-center text-xs text-slate-500 border border-dashed border-white/[0.08] rounded-xl gap-2">
              <AlertTriangle className="w-6 h-6 text-slate-600" />
              <span>Тексеру орындалған соң қателер диаграммасы осында шығады</span>
            </div>
          )}
        </div>

        {/* High / Medium / Low Donut + Language Comparison */}
        <div className="saas-card p-6 flex flex-col justify-between space-y-4">
          <div>
            <h3 className="text-sm font-bold text-white">High / Medium / Low үлесі</h3>
            <p className="text-xs text-slate-400">Қауіптілік деңгейі бойынша бөлініс</p>
          </div>

          {hasRuns && pieData.length > 0 ? (
            <>
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={pieData}
                      dataKey="count"
                      nameKey="severity"
                      cx="50%"
                      cy="50%"
                      innerRadius={48}
                      outerRadius={74}
                      paddingAngle={4}
                    >
                      {pieData.map((entry, idx) => (
                        <Cell key={idx} fill={entry.color} stroke="none" />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#0A0F1E',
                        borderColor: 'rgba(255,255,255,0.12)',
                        borderRadius: '12px',
                        fontSize: '12px',
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              <div className="space-y-2 pt-2 border-t border-white/[0.06] text-xs">
                {[
                  { label: 'High (Сыни қателер)', count: highCnt, dot: 'bg-rose-500', text: 'text-rose-300' },
                  { label: 'Medium (Ескертулер)', count: medCnt, dot: 'bg-amber-400', text: 'text-amber-300' },
                  { label: 'Low (Жеңіл ұсыныстар)', count: lowCnt, dot: 'bg-sky-400', text: 'text-sky-300' },
                ].map((row) => (
                  <div key={row.label} className="flex items-center justify-between">
                    <span className="flex items-center gap-2 text-slate-300">
                      <span className={`w-2.5 h-2.5 rounded-full ${row.dot}`} />
                      <span>{row.label}</span>
                    </span>
                    <span className={`font-mono font-bold ${row.text}`}>{row.count}</span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="h-60 flex items-center justify-center text-xs text-slate-500 border border-dashed border-white/[0.08] rounded-xl">
              Severity статистикасы бос
            </div>
          )}
        </div>
      </div>

      {/* Second Charts Row: KK vs UZ Comparison + Quality Trend */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="saas-card p-6 space-y-4">
          <div>
            <h3 className="text-sm font-bold text-white">
              Қазақша және өзбекше сапа көрсеткіштерін салыстыру
            </h3>
            <p className="text-xs text-slate-400">Тілдер арасындағы сапа индексі мен тексеру барысы</p>
          </div>
          {hasRuns && stats && stats.language_comparison.length > 0 ? (
            <div className="h-60">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={stats.language_comparison}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                  <XAxis dataKey="language" stroke="#cbd5e1" fontSize={12} />
                  <YAxis stroke="#94a3b8" fontSize={11} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#0A0F1E',
                      borderColor: 'rgba(255,255,255,0.12)',
                      borderRadius: '12px',
                      fontSize: '12px',
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: '12px' }} />
                  <Bar dataKey="score" name="Сапа (%)" fill="#10b981" radius={[6, 6, 0, 0]} />
                  <Bar dataKey="issues" name="Қателер" fill="#f43f5e" radius={[6, 6, 0, 0]} />
                  <Bar dataKey="reviewed" name="Адам тексерген" fill="#38bdf8" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-60 flex items-center justify-center text-xs text-slate-500 border border-dashed border-white/[0.08] rounded-xl">
              Тілдерді салыстыру деректері жоқ
            </div>
          )}
        </div>

        <div className="saas-card p-6 space-y-4">
          <div>
            <h3 className="text-sm font-bold text-white">Сапа динамикасы (Тексерулер бойынша)</h3>
            <p className="text-xs text-slate-400">Орындалған тексерулердің сапа тренді</p>
          </div>
          {hasRuns && stats && stats.runs_trend.length > 0 ? (
            <div className="h-60">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={stats.runs_trend}>
                  <defs>
                    <linearGradient id="kkGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.45} />
                      <stop offset="95%" stopColor="#38bdf8" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="uzGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.45} />
                      <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                  <XAxis dataKey="name" stroke="#cbd5e1" fontSize={11} />
                  <YAxis stroke="#94a3b8" fontSize={11} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#0A0F1E',
                      borderColor: 'rgba(255,255,255,0.12)',
                      borderRadius: '12px',
                      fontSize: '12px',
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: '12px' }} />
                  <Area
                    type="monotone"
                    dataKey="kk_score"
                    name="Қазақша сапа (%)"
                    stroke="#38bdf8"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#kkGrad)"
                  />
                  <Area
                    type="monotone"
                    dataKey="uz_score"
                    name="Өзбекше сапа (%)"
                    stroke="#8b5cf6"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#uzGrad)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-60 flex items-center justify-center text-xs text-slate-500 border border-dashed border-white/[0.08] rounded-xl">
              Динамика графигі алғашқы тексеруден кейін құрылады
            </div>
          )}
        </div>
      </div>

      {/* Recent Runs History Table directly on Dashboard (SQLite Live) */}
      <div className="saas-card overflow-hidden">
        <div className="px-6 py-4 border-b border-white/[0.07] flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-2.5">
            <History className="w-4 h-4 text-cyan-400" />
            <h3 className="text-sm font-bold text-white">Соңғы тексерулер тарихы (SQLite)</h3>
          </div>
          {hasRuns && (
            <button
              onClick={() => onNavigate('history')}
              className="text-xs font-semibold text-cyan-300 hover:text-cyan-200 inline-flex items-center gap-1"
            >
              <span>Барлық тарихты ашу</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {!hasRuns || !stats?.recent_runs?.length ? (
          <div className="p-10 text-center text-xs text-slate-500">
            Соңғы тексерулер тізімі бос. Жоғарыдағы «ARB файлдарын жүктеу» немесе «[DEMO] Үлгі
            жобаны іске қосу» батырмасын басыңыз.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="bg-white/[0.02] border-b border-white/[0.06] text-slate-400">
                  <th className="py-3 px-5">ID / Жоба атауы</th>
                  <th className="py-3 px-4">Тілдер</th>
                  <th className="py-3 px-4">Жолдар</th>
                  <th className="py-3 px-4">High / Med / Low</th>
                  <th className="py-3 px-4">Сапа (KK / UZ)</th>
                  <th className="py-3 px-4">Адам тексерген</th>
                  <th className="py-3 px-5 text-right">Әрекет</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.05]">
                {stats.recent_runs.map((r) => {
                  const isSelected = r.id === activeRun?.id;
                  return (
                    <tr
                      key={r.id}
                      onClick={() => onSelectRun(r.id)}
                      className={`cursor-pointer transition ${
                        isSelected ? 'bg-cyan-500/[0.07]' : 'hover:bg-white/[0.03]'
                      }`}
                    >
                      <td className="py-3.5 px-5 font-semibold text-white">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-cyan-400">#{r.id}</span>
                          <span>{r.name}</span>
                          {r.is_demo && (
                            <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300">
                              DEMO
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-3.5 px-4 space-x-1">
                        {r.has_kk && (
                          <span className="px-1.5 py-0.5 rounded bg-cyan-500/15 text-cyan-300 font-bold text-[10px]">
                            KK
                          </span>
                        )}
                        {r.has_uz && (
                          <span className="px-1.5 py-0.5 rounded bg-violet-500/15 text-violet-300 font-bold text-[10px]">
                            UZ
                          </span>
                        )}
                      </td>
                      <td className="py-3.5 px-4 font-mono text-slate-200">{r.checked_strings}</td>
                      <td className="py-3.5 px-4 font-mono">
                        <span className="text-rose-400 font-bold">{r.high_issues}</span>
                        <span className="text-slate-600"> / </span>
                        <span className="text-amber-300 font-bold">{r.medium_issues}</span>
                        <span className="text-slate-600"> / </span>
                        <span className="text-sky-300 font-bold">{r.low_issues}</span>
                      </td>
                      <td className="py-3.5 px-4 font-mono font-bold text-emerald-400">
                        {r.kk_quality_score.toFixed(1)}%
                        {r.uz_quality_score !== null ? ` / ${r.uz_quality_score.toFixed(1)}%` : ''}
                      </td>
                      <td className="py-3.5 px-4">
                        <span className="inline-flex items-center gap-1 font-mono text-slate-200">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                          {r.human_reviewed_count}
                        </span>
                      </td>
                      <td className="py-3.5 px-5 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectRun(r.id);
                            onNavigate('issues');
                          }}
                          className="px-3 py-1 rounded-lg bg-white/[0.05] hover:bg-cyan-500/20 text-cyan-300 font-semibold transition"
                        >
                          Талдау →
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
