import React, { useEffect, useState } from 'react';
import {
  FileCode2,
  FileJson,
  Download,
  CheckCircle2,
  ShieldCheck,
  Lightbulb,
  Eye,
  Copy,
  Check,
} from 'lucide-react';
import type { ReportSummary } from '../types';
import { api, downloadBlob } from '../api/client';

interface ReportsPageProps {
  activeRunId: number | null;
  activeLang?: 'kk' | 'uz';
  onSelectLang?: (lang: 'kk' | 'uz') => void;
}

export const ReportsPage: React.FC<ReportsPageProps> = ({
  activeRunId,
  activeLang,
  onSelectLang,
}) => {
  const [summary, setSummary] = useState<ReportSummary | null>(null);
  const [htmlPreview, setHtmlPreview] = useState<string>('');
  const [previewTab, setPreviewTab] = useState<'json' | 'html'>('json');
  const [reportLang, setReportLang] = useState<'all' | 'kk' | 'uz'>(activeLang || 'all');
  const [onlyHumanVerified, setOnlyHumanVerified] = useState<boolean>(false);
  const [copiedJson, setCopiedJson] = useState<boolean>(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (activeLang) {
      setReportLang(activeLang);
    }
  }, [activeLang]);

  useEffect(() => {
    if (!activeRunId) {
      setSummary(null);
      setHtmlPreview('');
      return;
    }
    setLoading(true);
    Promise.all([
      api.getReportSummary(activeRunId, reportLang),
      api.getReportHtmlPreview(activeRunId, reportLang),
    ])
      .then(([sum, html]) => {
        setSummary(sum);
        setHtmlPreview(html);
      })
      .finally(() => setLoading(false));
  }, [activeRunId, reportLang]);

  if (!activeRunId) {
    return (
      <div className="saas-card p-12 border-dashed text-center text-sm text-slate-400">
        Есептерді қалыптастыру үшін алдымен «Жаңа тексеру» немесе Dashboard бетінен локализация
        тексеруін орындаңыз.
      </div>
    );
  }

  if (loading || !summary) {
    return <div className="py-20 text-center text-sm text-slate-400">Есеп дайындалуда...</div>;
  }

  const jsonFormatted = JSON.stringify(summary.sample_json.slice(0, 5), null, 2);

  return (
    <div className="space-y-6">
      {/* Export Command Hero */}
      <div className="saas-card p-6 border-cyan-500/25 space-y-5">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-mono text-xs text-cyan-400">#{summary.run_id}</span>
              <h2 className="text-lg font-extrabold text-white">{summary.project_name}</h2>
              {summary.is_demo && (
                <span className="px-2 py-0.5 text-[10px] rounded-full bg-amber-500/20 text-amber-300 font-bold border border-amber-500/40">
                  DEMO
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Flutter <code className="font-mono text-cyan-300">gen-l10n</code> стандартына толық
              сәйкес келетін ARB экспорты және JSON / HTML есептері
            </p>
          </div>

          <div className="flex flex-wrap gap-2.5">
            <div className="inline-flex items-center gap-1 rounded-xl bg-white/[0.03] p-1 border border-white/[0.08]">
              {(
                [
                  { id: 'all', label: 'Барлық тіл' },
                  { id: 'kk', label: 'Қазақша' },
                  { id: 'uz', label: 'Өзбекше' },
                ] as const
              ).map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => {
                    setReportLang(item.id);
                    if (item.id === 'kk' || item.id === 'uz') {
                      onSelectLang?.(item.id);
                    }
                  }}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${
                    reportLang === item.id
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-400/40'
                      : 'text-slate-400 hover:text-slate-200 border border-transparent'
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </div>

            <button
              onClick={() =>
                downloadBlob(
                  `/api/reports/${summary.run_id}/json${reportLang !== 'all' ? `?lang=${reportLang}` : ''}`,
                  `locqa_report_${summary.run_id}${reportLang !== 'all' ? `_${reportLang}` : ''}.json`
                )
              }
              className="btn-secondary px-4 py-2.5 text-xs text-cyan-300"
            >
              <FileJson className="w-4 h-4" />
              <span>JSON есебін жүктеу</span>
            </button>

            <button
              onClick={() =>
                downloadBlob(
                  `/api/reports/${summary.run_id}/html`,
                  `locqa_report_${summary.run_id}.html`
                )
              }
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-violet-500/20 hover:bg-violet-500/30 border border-violet-400/40 text-xs font-bold text-violet-200 transition"
            >
              <FileCode2 className="w-4 h-4" />
              <span>HTML есебін жүктеу</span>
            </button>

            {summary.has_kk && (
              <button
                onClick={() =>
                  downloadBlob(
                    `/api/reports/${summary.run_id}/export-arb?lang=kk&only_human_verified=${onlyHumanVerified}`,
                    'intl_kk_fixed.arb'
                  )
                }
                className="btn-primary px-5 py-2.5 text-xs font-extrabold"
              >
                <Download className="w-4 h-4" />
                <span>intl_kk_fixed.arb жүктеу</span>
              </button>
            )}

            {summary.has_uz && (
              <button
                onClick={() =>
                  downloadBlob(
                    `/api/reports/${summary.run_id}/export-arb?lang=uz&only_human_verified=${onlyHumanVerified}`,
                    'intl_uz_fixed.arb'
                  )
                }
                className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/40 text-emerald-300 text-xs font-bold transition"
              >
                <Download className="w-4 h-4" />
                <span>intl_uz_fixed.arb</span>
              </button>
            )}
          </div>
        </div>

        <div className="pt-4 border-t border-white/[0.07] flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
          <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
            <input
              type="checkbox"
              checked={onlyHumanVerified}
              onChange={(e) => setOnlyHumanVerified(e.target.checked)}
              className="rounded border-slate-700"
            />
            <span>
              ARB экспортында тек адам растаған (
              <code className="font-mono text-emerald-300">reviewed_by_human = true</code>)
              өзгерістерді қолдану
            </span>
          </label>
          <span className="inline-flex items-center gap-1.5 text-emerald-400 font-semibold">
            <ShieldCheck className="w-4 h-4" />
            <span>@metadata, ICU plural/select және плейсхолдерлер 100% сақталады</span>
          </span>
        </div>
      </div>

      {/* 6 Report Stat Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3.5 text-center">
        <div className="saas-card p-4">
          <div className="text-[11px] text-slate-400">Жалпы жол саны</div>
          <div className="text-xl font-black font-mono text-white mt-1">
            {summary.total_strings}
          </div>
        </div>
        <div className="saas-card p-4">
          <div className="text-[11px] text-slate-400">Табылған қателер</div>
          <div className="text-xl font-black font-mono text-rose-400 mt-1">
            {summary.total_issues}
          </div>
        </div>
        <div className="saas-card p-4">
          <div className="text-[11px] text-slate-400">High / Med / Low</div>
          <div className="text-base font-black font-mono text-slate-200 mt-1.5">
            <span className="text-rose-400">{summary.severity_stats.high}</span> /{' '}
            <span className="text-amber-400">{summary.severity_stats.medium}</span> /{' '}
            <span className="text-sky-400">{summary.severity_stats.low}</span>
          </div>
        </div>
        <div className="saas-card p-4">
          <div className="text-[11px] text-slate-400">Түзетілген жолдар</div>
          <div className="text-xl font-black font-mono text-violet-300 mt-1">
            {summary.fixed_strings}
          </div>
        </div>
        <div className="saas-card p-4">
          <div className="text-[11px] text-slate-400">Адам тексерген</div>
          <div className="text-xl font-black font-mono text-emerald-400 mt-1">
            {summary.human_reviewed_strings}
          </div>
        </div>
        <div className="saas-card p-4">
          <div className="text-[11px] text-slate-400">Тексерілмеген</div>
          <div className="text-xl font-black font-mono text-amber-300 mt-1">
            {summary.unreviewed_strings}
          </div>
        </div>
      </div>

      {/* Recommendations + Issue Types */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="saas-card p-5 space-y-3">
          <div className="flex items-center gap-2 text-sm font-bold text-amber-300">
            <Lightbulb className="w-4 h-4" />
            <span>Сапаны жақсарту ұсыныстары</span>
          </div>
          <ul className="space-y-2.5 text-xs text-slate-300">
            {summary.recommendations.map((rec, i) => (
              <li key={i} className="flex items-start gap-2.5 leading-relaxed">
                <CheckCircle2 className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
                <span>{rec}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="saas-card p-5 space-y-3">
          <div className="text-sm font-bold text-cyan-300">Қате түрлерінің үлесі</div>
          <div className="space-y-2 text-xs max-h-60 overflow-y-auto pr-1">
            {summary.issue_types.map((it) => (
              <div
                key={it.issue_type}
                className="flex items-center justify-between p-2.5 rounded-xl bg-[#050811] border border-white/[0.06]"
              >
                <span className="text-slate-200">{it.label}</span>
                <span className="font-mono font-bold text-cyan-300">{it.count}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Live Preview Tabs: JSON Schema vs Embedded HTML Report */}
      <div className="saas-card overflow-hidden">
        <div className="px-5 py-3.5 border-b border-white/[0.07] bg-white/[0.02] flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPreviewTab('json')}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition ${
                previewTab === 'json'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-400/35'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <FileJson className="w-3.5 h-3.5" />
              <span>JSON Есеп құрылымы</span>
            </button>
            <button
              onClick={() => setPreviewTab('html')}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition ${
                previewTab === 'html'
                  ? 'bg-violet-500/20 text-violet-300 border border-violet-400/35'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Eye className="w-3.5 h-3.5" />
              <span>HTML Есепті алдын ала қарау</span>
            </button>
          </div>

          {previewTab === 'json' && (
            <button
              onClick={() => {
                navigator.clipboard?.writeText(jsonFormatted);
                setCopiedJson(true);
                setTimeout(() => setCopiedJson(false), 1500);
              }}
              className="btn-secondary px-3 py-1.5 text-xs"
            >
              {copiedJson ? (
                <Check className="w-3.5 h-3.5 text-emerald-400" />
              ) : (
                <Copy className="w-3.5 h-3.5" />
              )}
              <span>{copiedJson ? 'Көшірілді!' : 'JSON көшіру'}</span>
            </button>
          )}
        </div>

        <div className="p-5">
          {previewTab === 'json' ? (
            <pre className="p-4 rounded-xl bg-[#050811] border border-white/[0.07] font-mono text-xs text-cyan-200 overflow-x-auto leading-relaxed">
              {jsonFormatted}
            </pre>
          ) : (
            <iframe
              title="Qazaq Loc QA HTML Report Preview"
              srcDoc={htmlPreview}
              className="w-full h-[540px] rounded-xl border border-white/[0.08] bg-[#070b14]"
            />
          )}
        </div>
      </div>
    </div>
  );
};
