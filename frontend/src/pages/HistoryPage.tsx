import React from 'react';
import { Trash2, ArrowUpRight, CheckCircle2, Clock } from 'lucide-react';
import type { PageId, ProjectRun } from '../types';

interface HistoryPageProps {
  runs: ProjectRun[];
  activeRunId: number | null;
  onSelectRun: (runId: number) => void;
  onDeleteRun: (runId: number) => void;
  onNavigate: (page: PageId) => void;
}

export const HistoryPage: React.FC<HistoryPageProps> = ({
  runs,
  activeRunId,
  onSelectRun,
  onDeleteRun,
  onNavigate,
}) => {
  return (
    <div className="space-y-6">
      <div className="saas-card p-5 flex items-center justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-base font-extrabold text-white">Жобалар және тексерулер тарихы</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Кез келген бұрынғы тексеруді белсенді етіп, оның қателерін немесе ARB экспортын аша
            аласыз.
          </p>
        </div>
        <span className="text-xs font-mono px-3 py-1.5 rounded-xl bg-white/[0.05] border border-white/[0.08] text-cyan-300 font-bold">
          Барлығы: {runs.length} тексеру
        </span>
      </div>

      {runs.length === 0 ? (
        <div className="saas-card p-12 border-dashed text-center text-sm text-slate-400">
          Орындалған тексерулер тарихы бос.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {runs.map((r) => {
            const isCurrent = r.id === activeRunId;
            return (
              <div
                key={r.id}
                className={`saas-card-hover p-5 space-y-4 ${
                  isCurrent ? '!border-cyan-400/50 shadow-glow' : ''
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs font-mono text-cyan-400 font-bold">#{r.id}</span>
                      <h3 className="text-sm font-bold text-white">{r.name}</h3>
                      {r.is_demo && (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40">
                          DEMO
                        </span>
                      )}
                      {isCurrent && (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-cyan-500/20 text-cyan-300">
                          Белсенді
                        </span>
                      )}
                    </div>
                    <div className="text-[11px] text-slate-500 mt-1 flex items-center gap-2 font-mono">
                      <Clock className="w-3 h-3" />
                      <span>{new Date(r.created_at).toLocaleString('kk-KZ')}</span>
                      <span>•</span>
                      <span>{r.duration_ms} мс</span>
                    </div>
                  </div>
                  <button
                    onClick={() => onDeleteRun(r.id)}
                    className="p-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 transition"
                    title="Жою"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>

                <div className="grid grid-cols-4 gap-2 text-center text-xs">
                  <div className="p-2.5 rounded-xl bg-[#050811] border border-white/[0.06]">
                    <div className="text-[10px] text-slate-400">Жолдар</div>
                    <div className="font-mono font-bold text-white mt-0.5">
                      {r.checked_strings}
                    </div>
                  </div>
                  <div className="p-2.5 rounded-xl bg-[#050811] border border-white/[0.06]">
                    <div className="text-[10px] text-slate-400">Қателер</div>
                    <div className="font-mono font-bold text-rose-400 mt-0.5">{r.total_issues}</div>
                  </div>
                  <div className="p-2.5 rounded-xl bg-[#050811] border border-white/[0.06]">
                    <div className="text-[10px] text-slate-400">KK сапа</div>
                    <div className="font-mono font-bold text-emerald-400 mt-0.5">
                      {r.kk_quality_score.toFixed(1)}%
                    </div>
                  </div>
                  <div className="p-2.5 rounded-xl bg-[#050811] border border-white/[0.06]">
                    <div className="text-[10px] text-slate-400">Адам текс.</div>
                    <div className="font-mono font-bold text-cyan-300 mt-0.5">
                      {r.human_reviewed_count}
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-1">
                  <span className="inline-flex items-center gap-1.5 text-[11px] text-slate-400">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    <span>
                      Режим: {r.ai_mode_used === 'hybrid_llm' ? 'Hybrid LLM' : 'Rule Engine'}
                    </span>
                  </span>
                  <button
                    onClick={() => {
                      onSelectRun(r.id);
                      onNavigate('issues');
                    }}
                    className="btn-primary px-3.5 py-1.5 text-xs"
                  >
                    <span>Нәтижені ашу</span>
                    <ArrowUpRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
