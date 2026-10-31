import React, { useEffect, useState } from 'react';
import {
  X,
  CheckCircle2,
  Sparkles,
  AlertOctagon,
  Save,
  RotateCcw,
  ShieldAlert,
  Languages,
  Copy,
  Check,
} from 'lucide-react';
import { ISSUE_TYPE_LABELS, type QAIssueItem } from '../types';
import { api } from '../api/client';

interface IssueEditorModalProps {
  issue: QAIssueItem | null;
  reviewerName?: string;
  onClose: () => void;
  onUpdated: (updated: QAIssueItem) => void;
}

export const IssueEditorModal: React.FC<IssueEditorModalProps> = ({
  issue,
  reviewerName,
  onClose,
  onUpdated,
}) => {
  const [draftTarget, setDraftTarget] = useState('');
  const [latinPreview, setLatinPreview] = useState('');
  const [saving, setSaving] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (issue) {
      const initial = issue.current_target ?? issue.target;
      setDraftTarget(initial);
      setLatinPreview(issue.latin_preview || '');
      setError(null);
      if (issue.lang === 'kk' && initial) {
        api
          .transliterate(initial)
          .then((res) => setLatinPreview(res.latin_text))
          .catch(() => {});
      }
    }
  }, [issue]);

  useEffect(() => {
    if (!issue) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [issue, onClose]);

  if (!issue) return null;

  const handleDraftChange = (val: string) => {
    setDraftTarget(val);
    if (issue.lang === 'kk') {
      api
        .transliterate(val)
        .then((res) => setLatinPreview(res.latin_text))
        .catch(() => {});
    }
  };

  const triggerAction = async (
    action: 'accept_suggestion' | 'manual_edit' | 'mark_reviewed' | 'reject_suggestion'
  ) => {
    setSaving(true);
    setError(null);
    try {
      const updated = await api.applyIssueAction(issue.id, {
        action,
        new_target: action === 'manual_edit' || action === 'mark_reviewed' ? draftTarget : undefined,
        reviewer_name: reviewerName,
      });
      onUpdated(updated);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Сақтау кезінде қате шықты');
    } finally {
      setSaving(false);
    }
  };

  const sevBadge =
    issue.severity === 'high'
      ? 'bg-rose-500/20 text-rose-300 border-rose-500/40'
      : issue.severity === 'medium'
      ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
      : 'bg-sky-500/20 text-sky-300 border-sky-500/40';

  const sourcePlaceholders = Array.from(issue.source.matchAll(/\{[a-zA-Z0-9_]+\}|%[sd]|\$\d+/g)).map(
    (m) => m[0]
  );

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-black/80 backdrop-blur-sm overflow-y-auto"
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="saas-card border-white/[0.14] max-w-4xl w-full shadow-2xl overflow-hidden my-auto animate-page"
      >
        {/* Modal Header */}
        <div className="px-6 py-4 bg-[#060A14]/90 border-b border-white/[0.08] flex items-center justify-between gap-4">
          <div className="flex items-center gap-2.5 flex-wrap">
            <span className="font-mono text-xs px-2.5 py-1 rounded-lg bg-cyan-500/10 text-cyan-300 border border-cyan-500/25">
              {issue.key}
            </span>
            <span className={`text-[11px] font-extrabold uppercase px-2.5 py-0.5 rounded-full border ${sevBadge}`}>
              {issue.severity}
            </span>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-violet-500/15 text-violet-300 border border-violet-500/30 font-medium">
              {ISSUE_TYPE_LABELS[issue.issue_type] || issue.issue_type}
            </span>
            <span className="text-[11px] px-2 py-0.5 rounded-md bg-white/[0.06] text-slate-200 font-bold uppercase">
              {issue.lang}
            </span>
            {issue.reviewed_by_human ? (
              <span className="text-[11px] px-2.5 py-0.5 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 font-semibold">
                Маман растаған (reviewed_by_human = true)
              </span>
            ) : (
              <span className="text-[11px] px-2.5 py-0.5 rounded-full bg-white/[0.05] text-slate-400 border border-white/[0.08]">
                reviewed_by_human = false
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/[0.06]"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-5">
          {error && (
            <div className="p-3.5 rounded-xl bg-rose-500/15 border border-rose-500/40 text-xs text-rose-200 font-medium">
              {error}
            </div>
          )}

          {/* Special Kazakh Dynamic Suffix Warning */}
          {issue.issue_type === 'suffix_harmony' && !issue.auto_fix_safe && (
            <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/35 flex items-start gap-3">
              <ShieldAlert className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
              <div className="text-xs text-amber-100/95 space-y-1">
                <div className="font-bold text-amber-300">
                  Қазақ тілінің динамикалық жалғау ескертуі (Қауіпті авто-түзету бұғатталған)
                </div>
                <p className="text-amber-200/85 leading-relaxed">
                  Ойыншының есімі тек бағдарлама орындалғанда (runtime) белгілі болады. Жалғауды
                  сөйлемді қайта құрастыру арқылы шешіңіз немесе код деңгейінде{' '}
                  <code className="font-mono text-cyan-300">KazakhSuffixHelper</code> функциясын
                  қолданыңыз.
                </p>
              </div>
            </div>
          )}

          {/* Left: Russian Source | Right: Kazakh/Uzbek Target */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Left Side */}
            <div className="p-4 rounded-xl bg-[#060A15] border border-white/[0.08] space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                  Орысша түпнұсқа (intl_ru.arb)
                </span>
                <span className="text-[11px] font-mono text-slate-500">
                  {issue.source.length} таңба
                </span>
              </div>
              <div className="text-sm text-slate-100 whitespace-pre-wrap leading-relaxed min-h-[84px]">
                {issue.source}
              </div>

              {sourcePlaceholders.length > 0 && (
                <div className="pt-2 border-t border-white/[0.06] flex items-center gap-1.5 flex-wrap">
                  <span className="text-[10px] text-slate-500">Плейсхолдерлер:</span>
                  {sourcePlaceholders.map((ph, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => handleDraftChange(draftTarget + (draftTarget ? ' ' : '') + ph)}
                      className="font-mono text-[11px] px-2 py-0.5 rounded bg-cyan-500/15 hover:bg-cyan-500/25 text-cyan-300 border border-cyan-500/30 transition"
                      title="Аудармаға қосу үшін басыңыз"
                    >
                      + {ph}
                    </button>
                  ))}
                </div>
              )}

              {issue.en_text && (
                <div className="pt-3 border-t border-white/[0.06]">
                  <div className="text-[11px] font-semibold text-slate-400 mb-1">
                    Ағылшынша референс (intl_en.arb):
                  </div>
                  <div className="text-xs text-slate-300">{issue.en_text}</div>
                </div>
              )}
            </div>

            {/* Right Side */}
            <div className="p-4 rounded-xl bg-[#060A15] border border-cyan-500/30 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold uppercase tracking-wider text-cyan-300">
                  {issue.lang === 'kk'
                    ? 'Қазақша аударма (intl_kk.arb)'
                    : 'Өзбекше аударма (intl_uz.arb)'}
                </span>
                <div className="flex items-center gap-2">
                  <span className="text-[11px] font-mono text-slate-400">
                    {draftTarget.length} таңба
                  </span>
                  <button
                    type="button"
                    onClick={() => {
                      navigator.clipboard?.writeText(draftTarget);
                      setCopied(true);
                      setTimeout(() => setCopied(false), 1500);
                    }}
                    className="p-1 rounded bg-white/[0.05] hover:bg-white/[0.1] text-slate-300"
                    title="Көшіру"
                  >
                    {copied ? (
                      <Check className="w-3.5 h-3.5 text-emerald-400" />
                    ) : (
                      <Copy className="w-3.5 h-3.5" />
                    )}
                  </button>
                </div>
              </div>

              <textarea
                rows={4}
                value={draftTarget}
                onChange={(e) => handleDraftChange(e.target.value)}
                className="w-full saas-input p-3 text-sm leading-relaxed"
              />

              {issue.lang === 'kk' && latinPreview && (
                <div className="flex items-start gap-2 text-[11px] text-slate-400 bg-white/[0.03] p-2.5 rounded-lg border border-white/[0.06]">
                  <Languages className="w-3.5 h-3.5 text-cyan-400 shrink-0 mt-0.5" />
                  <div>
                    <span className="text-slate-500">Латынша ({latinPreview.length} т.): </span>
                    <span className="text-slate-200">{latinPreview}</span>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Bottom: AI Suggestion, Evidence, Confidence */}
          <div className="p-4 rounded-xl bg-white/[0.025] border border-white/[0.08] space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="md:col-span-2 space-y-2">
                <div className="flex items-center gap-2 text-xs font-bold text-violet-300">
                  <Sparkles className="w-4 h-4 text-violet-400" />
                  <span>AI ұсынған түзету:</span>
                </div>
                {issue.suggestion ? (
                  <div className="p-3 rounded-xl bg-gradient-to-r from-violet-500/10 to-cyan-500/10 border border-violet-500/30 text-sm text-emerald-300 font-medium flex items-center justify-between gap-3">
                    <span>{issue.suggestion}</span>
                    <button
                      type="button"
                      onClick={() => handleDraftChange(issue.suggestion)}
                      className="text-xs px-3 py-1 rounded-lg bg-violet-500/25 hover:bg-violet-500/40 text-violet-100 font-semibold shrink-0 transition"
                    >
                      Өріске қолдану
                    </button>
                  </div>
                ) : (
                  <div className="text-xs text-slate-400 italic">
                    Контекст бойынша маманның қолмен өңдеуі ұсынылады.
                  </div>
                )}
              </div>

              <div className="space-y-2">
                <div className="text-xs font-bold text-slate-300">AI Confidence:</div>
                <div className="p-3 rounded-xl bg-[#060A15] border border-white/[0.08]">
                  <div className="flex items-center justify-between text-xs mb-1.5">
                    <span className="text-slate-400">Сенімділік</span>
                    <span className="font-mono font-bold text-cyan-300">
                      {Math.round(issue.confidence * 100)}%
                    </span>
                  </div>
                  <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-cyan-400 via-blue-500 to-violet-500"
                      style={{ width: `${Math.round(issue.confidence * 100)}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>

            <div className="pt-2.5 border-t border-white/[0.06]">
              <div className="flex items-center gap-1.5 text-xs font-bold text-rose-300 mb-1">
                <AlertOctagon className="w-3.5 h-3.5" />
                <span>Қате себебі (Evidence):</span>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">{issue.evidence}</p>
            </div>
          </div>

          {/* 4 Required Action Buttons */}
          <div className="flex flex-wrap items-center justify-end gap-2.5 pt-1">
            <button
              disabled={saving}
              onClick={() => triggerAction('reject_suggestion')}
              className="btn-secondary px-4 py-2.5 text-xs"
            >
              <RotateCcw className="w-3.5 h-3.5 text-rose-400" />
              <span>Түзетуден бас тарту</span>
            </button>

            <button
              disabled={saving}
              onClick={() => triggerAction('mark_reviewed')}
              className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/40 text-emerald-300 text-xs font-bold transition disabled:opacity-50"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Тексерілді деп белгілеу</span>
            </button>

            <button
              disabled={saving}
              onClick={() => triggerAction('manual_edit')}
              className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-500/40 text-cyan-200 text-xs font-bold transition disabled:opacity-50"
            >
              <Save className="w-3.5 h-3.5" />
              <span>Қолмен өзгерту</span>
            </button>

            <button
              disabled={saving || !issue.suggestion}
              onClick={() => triggerAction('accept_suggestion')}
              className="btn-primary px-5 py-2.5 text-xs font-bold"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Түзетуді қабылдау</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
