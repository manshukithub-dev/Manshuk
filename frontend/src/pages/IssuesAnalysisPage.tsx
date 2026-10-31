import React, { useCallback, useEffect, useState } from 'react';
import {
  Search,
  Wand2,
  CheckCircle2,
  Clock,
  SlidersHorizontal,
  AlertTriangle,
} from 'lucide-react';
import { ISSUE_TYPE_LABELS, type QAIssueItem } from '../types';
import { api } from '../api/client';
import { IssueEditorModal } from '../components/IssueEditorModal';

interface IssuesAnalysisPageProps {
  activeRunId: number | null;
  activeLang?: 'kk' | 'uz';
  onSelectLang?: (lang: 'kk' | 'uz') => void;
  reviewerName?: string;
  onStatsChanged: () => void;
}

export const IssuesAnalysisPage: React.FC<IssuesAnalysisPageProps> = ({
  activeRunId,
  activeLang,
  onSelectLang,
  reviewerName,
  onStatsChanged,
}) => {
  const [issues, setIssues] = useState<QAIssueItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);

  const [severity, setSeverity] = useState<string>('all');
  const [lang, setLang] = useState<string>(activeLang || 'all');

  useEffect(() => {
    if (activeLang) {
      setLang(activeLang);
    }
  }, [activeLang]);
  const [reviewed, setReviewed] = useState<string>('all');
  const [issueType, setIssueType] = useState<string>('all');
  const [search, setSearch] = useState<string>('');
  const [selectedIssue, setSelectedIssue] = useState<QAIssueItem | null>(null);
  const [batchMessage, setBatchMessage] = useState<string | null>(null);

  const fetchIssues = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.listIssues({
        run_id: activeRunId,
        severity,
        lang,
        issue_type: issueType,
        reviewed,
        search,
        page: 1,
        page_size: 250,
      });
      setIssues(res.items);
      setTotal(res.total);
    } finally {
      setLoading(false);
    }
  }, [activeRunId, severity, lang, issueType, reviewed, search]);

  useEffect(() => {
    fetchIssues();
  }, [fetchIssues]);

  const handleBatchAutoFix = async () => {
    if (!activeRunId) return;
    const res = await api.batchAutoFix(activeRunId, lang);
    setBatchMessage(
      `${res.applied_count} қауіпсіз жол автоматты түрде түзетілді (reviewed_by_human = false күйінде қалды). Маман растауы қажет.`
    );
    await fetchIssues();
    onStatsChanged();
  };

  return (
    <div className="space-y-5">
      {/* Filter Controls Card */}
      <div className="saas-card p-5 space-y-4">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-1.5">
            {[
              { id: 'all', label: 'Барлық қателер' },
              { id: 'high', label: 'High' },
              { id: 'medium', label: 'Medium' },
              { id: 'low', label: 'Low' },
            ].map((btn) => (
              <button
                key={btn.id}
                onClick={() => setSeverity(btn.id)}
                className={`px-3 py-1.5 rounded-xl text-xs font-bold transition border ${
                  severity === btn.id
                    ? 'bg-cyan-500/20 text-cyan-300 border-cyan-400/40 shadow-glow'
                    : 'bg-white/[0.03] text-slate-400 border-white/[0.07] hover:text-slate-200'
                }`}
              >
                {btn.label}
              </button>
            ))}

            <div className="h-4 w-px bg-white/[0.08] mx-1 hidden sm:block" />

            {[
              { id: 'all', label: 'Барлық тіл' },
              { id: 'kk', label: 'Қазақша' },
              { id: 'uz', label: 'Өзбекше' },
            ].map((lBtn) => (
              <button
                key={lBtn.id}
                onClick={() => {
                  setLang(lBtn.id);
                  if (lBtn.id === 'kk' || lBtn.id === 'uz') {
                    onSelectLang?.(lBtn.id);
                  }
                }}
                className={`px-3 py-1.5 rounded-xl text-xs font-bold transition border ${
                  lang === lBtn.id
                    ? 'bg-violet-500/20 text-violet-300 border-violet-400/40'
                    : 'bg-white/[0.03] text-slate-400 border-white/[0.07] hover:text-slate-200'
                }`}
              >
                {lBtn.label}
              </button>
            ))}

            <div className="h-4 w-px bg-white/[0.08] mx-1 hidden sm:block" />

            {[
              { id: 'all', label: 'Барлық мәртебе' },
              { id: 'false', label: 'Адам тексермеген' },
              { id: 'true', label: 'Адам тексерген' },
            ].map((rBtn) => (
              <button
                key={rBtn.id}
                onClick={() => setReviewed(rBtn.id)}
                className={`px-3 py-1.5 rounded-xl text-xs font-bold transition border ${
                  reviewed === rBtn.id
                    ? 'bg-emerald-500/20 text-emerald-300 border-emerald-400/40'
                    : 'bg-white/[0.03] text-slate-400 border-white/[0.07] hover:text-slate-200'
                }`}
              >
                {rBtn.label}
              </button>
            ))}
          </div>

          {activeRunId && (
            <button
              onClick={handleBatchAutoFix}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-violet-500/15 hover:bg-violet-500/25 border border-violet-400/35 text-violet-200 text-xs font-bold transition shrink-0"
              title="Тек қауіпсіз жолдарды автоматты түзетеді (reviewed_by_human = false сақталады)"
            >
              <Wand2 className="w-3.5 h-3.5 text-violet-400" />
              <span>Қауіпсіз авто-түзету</span>
            </button>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-1">
          <div className="md:col-span-2 relative">
            <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Key, орысша түпнұсқа, аударма немесе қате түсіндірмесі бойынша іздеу..."
              className="w-full saas-input pl-10 pr-4 py-2 text-xs"
            />
          </div>
          <div className="flex items-center gap-2">
            <SlidersHorizontal className="w-4 h-4 text-slate-400 shrink-0" />
            <select
              value={issueType}
              onChange={(e) => setIssueType(e.target.value)}
              className="w-full saas-input px-3 py-2 text-xs font-medium"
            >
              <option value="all" className="bg-[#0A0F1E]">
                Барлық 12 қате түрі ({total})
              </option>
              {Object.entries(ISSUE_TYPE_LABELS).map(([k, lbl]) => (
                <option key={k} value={k} className="bg-[#0A0F1E]">
                  {lbl} ({k})
                </option>
              ))}
            </select>
          </div>
        </div>

        {batchMessage && (
          <div className="p-3.5 rounded-xl bg-violet-500/15 border border-violet-500/35 text-xs text-violet-200 font-medium">
            {batchMessage}
          </div>
        )}
      </div>

      {/* Issues Data Table */}
      <div className="saas-card overflow-x-auto">
        {loading ? (
          <div className="py-20 text-center text-xs text-slate-400">
            Қателер тізімі жүктелуде...
          </div>
        ) : issues.length === 0 ? (
          <div className="py-20 flex flex-col items-center justify-center text-sm text-slate-400 gap-2">
            <AlertTriangle className="w-6 h-6 text-slate-600" />
            <span>Таңдалған сүзгілер бойынша қателер табылмады.</span>
          </div>
        ) : (
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-white/[0.07] bg-white/[0.02] text-slate-400">
                <th className="py-3.5 px-4">Key</th>
                <th className="py-3.5 px-3">Тіл</th>
                <th className="py-3.5 px-3">Қате түрі</th>
                <th className="py-3.5 px-3">Severity</th>
                <th className="py-3.5 px-4">Source (RU)</th>
                <th className="py-3.5 px-4">Target</th>
                <th className="py-3.5 px-4">Suggestion</th>
                <th className="py-3.5 px-3">Conf.</th>
                <th className="py-3.5 px-4">Human Review</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.05]">
              {issues.map((iss) => {
                const sevStyle =
                  iss.severity === 'high'
                    ? 'bg-rose-500/20 text-rose-300 border-rose-500/40'
                    : iss.severity === 'medium'
                    ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                    : 'bg-sky-500/20 text-sky-300 border-sky-500/40';
                return (
                  <tr
                    key={iss.id}
                    onClick={() => setSelectedIssue(iss)}
                    className="hover:bg-cyan-500/[0.05] cursor-pointer transition group"
                  >
                    <td className="py-3.5 px-4 font-mono text-[11px] text-cyan-300 group-hover:text-cyan-200 font-semibold">
                      {iss.key}
                    </td>
                    <td className="py-3.5 px-3 uppercase font-mono font-bold text-slate-300">
                      {iss.lang}
                    </td>
                    <td className="py-3.5 px-3">
                      <span className="px-2.5 py-0.5 rounded-md bg-white/[0.04] text-slate-200 border border-white/[0.08] text-[11px] whitespace-nowrap">
                        {ISSUE_TYPE_LABELS[iss.issue_type] || iss.issue_type}
                      </span>
                    </td>
                    <td className="py-3.5 px-3">
                      <span
                        className={`px-2 py-0.5 rounded-full border text-[10px] font-extrabold uppercase ${sevStyle}`}
                      >
                        {iss.severity}
                      </span>
                    </td>
                    <td
                      className="py-3.5 px-4 text-slate-200 max-w-[220px] truncate"
                      title={iss.source}
                    >
                      {iss.source}
                    </td>
                    <td
                      className="py-3.5 px-4 text-rose-300 max-w-[220px] truncate"
                      title={iss.current_target ?? iss.target}
                    >
                      {(iss.current_target ?? iss.target) || (
                        <span className="italic opacity-60">(бос)</span>
                      )}
                    </td>
                    <td
                      className="py-3.5 px-4 text-emerald-300 max-w-[220px] truncate font-medium"
                      title={iss.suggestion}
                    >
                      {iss.suggestion || '—'}
                    </td>
                    <td className="py-3.5 px-3 font-mono font-semibold text-slate-300">
                      {Math.round(iss.confidence * 100)}%
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      {iss.reviewed_by_human ? (
                        <span className="inline-flex items-center gap-1 text-emerald-400 font-bold">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>Тексерілді</span>
                        </span>
                      ) : iss.resolution === 'auto_applied' ? (
                        <span className="inline-flex items-center gap-1 text-violet-300">
                          <Clock className="w-3.5 h-3.5" />
                          <span>Авто (расталмаған)</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-amber-300/90">
                          <Clock className="w-3.5 h-3.5" />
                          <span>Күтілуде</span>
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      <IssueEditorModal
        issue={selectedIssue}
        reviewerName={reviewerName}
        onClose={() => setSelectedIssue(null)}
        onUpdated={() => {
          fetchIssues();
          onStatsChanged();
        }}
      />
    </div>
  );
};
