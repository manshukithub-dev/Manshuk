import React, { useCallback, useEffect, useState } from 'react';
import {
  CheckCircle2,
  Sparkles,
  Save,
  RotateCcw,
  Download,
  Search,
  ChevronRight,
  Languages,
  AlertTriangle,
} from 'lucide-react';
import { ISSUE_TYPE_LABELS, type TranslationEntryItem } from '../types';
import { api, downloadBlob } from '../api/client';

interface TranslationEditorPageProps {
  activeRunId: number | null;
  activeLang?: 'kk' | 'uz';
  onSelectLang?: (lang: 'kk' | 'uz') => void;
  reviewerName?: string;
  onStatsChanged: () => void;
}

const KAZAKH_CHARS = [
  'ә',
  'ғ',
  'қ',
  'ң',
  'ө',
  'ұ',
  'ү',
  'һ',
  'і',
  'Ә',
  'Ғ',
  'Қ',
  'Ң',
  'Ө',
  'Ұ',
  'Ү',
  'І',
];

export const TranslationEditorPage: React.FC<TranslationEditorPageProps> = ({
  activeRunId,
  activeLang,
  onSelectLang,
  reviewerName,
  onStatsChanged,
}) => {
  const [lang, setLang] = useState<'kk' | 'uz'>(activeLang || 'kk');

  useEffect(() => {
    if (activeLang && activeLang !== lang) {
      setLang(activeLang);
    }
  }, [activeLang]);
  const [filterMode, setFilterMode] = useState<string>('with_issues');
  const [search, setSearch] = useState<string>('');
  const [entries, setEntries] = useState<TranslationEntryItem[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [draft, setDraft] = useState<string>('');
  const [latinText, setLatinText] = useState<string>('');
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const loadEntries = useCallback(async () => {
    const res = await api.listEntries({
      run_id: activeRunId,
      lang,
      filter_mode: filterMode,
      search,
      page: 1,
      page_size: 200,
    });
    setEntries(res.items);
    if (res.items.length > 0 && !res.items.some((e) => e.id === selectedId)) {
      setSelectedId(res.items[0].id);
    } else if (res.items.length === 0) {
      setSelectedId(null);
    }
  }, [activeRunId, lang, filterMode, search, selectedId]);

  useEffect(() => {
    loadEntries();
  }, [loadEntries]);

  const currentEntry = entries.find((e) => e.id === selectedId) || null;

  useEffect(() => {
    if (currentEntry) {
      setDraft(currentEntry.current_target);
      setLatinText(currentEntry.latin_preview || '');
      if (currentEntry.lang === 'kk' && currentEntry.current_target) {
        api
          .transliterate(currentEntry.current_target)
          .then((r) => setLatinText(r.latin_text))
          .catch(() => {});
      }
    }
  }, [currentEntry]);

  const updateDraftWithLatin = (val: string) => {
    setDraft(val);
    if (lang === 'kk') {
      api
        .transliterate(val)
        .then((r) => setLatinText(r.latin_text))
        .catch(() => {});
    }
  };

  const handleSaveEntry = async (newValue: string, humanReviewed: boolean, msg: string) => {
    if (!currentEntry) return;
    setSaving(true);
    try {
      await api.updateEntry(currentEntry.id, {
        current_target: newValue,
        reviewed_by_human: humanReviewed,
        reviewer_name: reviewerName,
      });
      setToast(msg);
      setTimeout(() => setToast(null), 2500);
      await loadEntries();
      onStatsChanged();
    } finally {
      setSaving(false);
    }
  };

  const moveNext = () => {
    if (!currentEntry || entries.length === 0) return;
    const idx = entries.findIndex((e) => e.id === currentEntry.id);
    if (idx >= 0 && idx + 1 < entries.length) {
      setSelectedId(entries[idx + 1].id);
    }
  };

  const reviewedCountInList = entries.filter((e) => e.reviewed_by_human).length;
  const sourcePlaceholders = currentEntry
    ? Array.from(currentEntry.source_text.matchAll(/\{[a-zA-Z0-9_]+\}|%[sd]|\$\d+/g)).map(
        (m) => m[0]
      )
    : [];

  return (
    <div className="space-y-5">
      {/* Top CAT Toolbar */}
      <div className="saas-card p-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          {(['kk', 'uz'] as const).map((l) => (
            <button
              key={l}
              onClick={() => {
                setLang(l);
                onSelectLang?.(l);
              }}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-extrabold uppercase border transition ${
                lang === l
                  ? 'bg-cyan-500/20 text-cyan-300 border-cyan-400/40 shadow-glow'
                  : 'bg-white/[0.03] text-slate-400 border-white/[0.07]'
              }`}
            >
              {l === 'kk' ? 'Қазақша (KK)' : 'Өзбекше (UZ)'}
            </button>
          ))}

          <select
            value={filterMode}
            onChange={(e) => setFilterMode(e.target.value)}
            className="saas-input px-3 py-1.5 text-xs font-medium"
          >
            <option value="with_issues" className="bg-[#0A0F1E]">Қатесі бар жолдар</option>
            <option value="unreviewed" className="bg-[#0A0F1E]">Адам тексермеген</option>
            <option value="auto_fixed" className="bg-[#0A0F1E]">Авто-түзетілген (расталмаған)</option>
            <option value="reviewed" className="bg-[#0A0F1E]">Маман растаған (reviewed_by_human = true)</option>
            <option value="all" className="bg-[#0A0F1E]">Барлық ARB кілттері</option>
          </select>

          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Кілт немесе мәтін іздеу..."
              className="saas-input pl-8 pr-3 py-1.5 text-xs"
            />
          </div>
        </div>

        <div className="flex items-center gap-3">
          {entries.length > 0 && (
            <span className="text-xs text-slate-400 font-mono">
              Расталды: <b className="text-emerald-400">{reviewedCountInList}</b> / {entries.length}
            </span>
          )}
          {activeRunId && (
            <button
              onClick={() =>
                downloadBlob(
                  `/api/reports/${activeRunId}/export-arb?lang=${lang}`,
                  `intl_${lang}_fixed.arb`
                )
              }
              className="btn-primary px-4 py-2 text-xs"
            >
              <Download className="w-3.5 h-3.5" />
              <span>intl_{lang}_fixed.arb экспорттау</span>
            </button>
          )}
        </div>
      </div>

      {toast && (
        <div className="p-3.5 rounded-xl bg-emerald-500/15 border border-emerald-500/40 text-xs text-emerald-200 font-semibold">
          {toast}
        </div>
      )}

      {/* Split-Pane CAT Workbench */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left List */}
        <div className="lg:col-span-4 saas-card overflow-hidden flex flex-col max-h-[72vh]">
          <div className="px-4 py-3 border-b border-white/[0.07] bg-white/[0.02] text-xs font-bold text-slate-300 flex items-center justify-between">
            <span>ARB Жолдар тізімі</span>
            <span className="font-mono text-cyan-300">{entries.length}</span>
          </div>
          <div className="overflow-y-auto divide-y divide-white/[0.05]">
            {entries.length === 0 ? (
              <div className="p-10 text-center text-xs text-slate-500">Жолдар табылмады</div>
            ) : (
              entries.map((entry) => {
                const active = entry.id === currentEntry?.id;
                return (
                  <button
                    key={entry.id}
                    onClick={() => setSelectedId(entry.id)}
                    className={`w-full text-left p-3.5 transition space-y-1 ${
                      active
                        ? 'bg-gradient-to-r from-cyan-500/15 to-transparent border-l-2 border-cyan-400'
                        : 'hover:bg-white/[0.03]'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-mono text-[11px] text-cyan-300 truncate font-semibold">
                        {entry.key}
                      </span>
                      {entry.reviewed_by_human ? (
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                      ) : entry.issues.length > 0 ? (
                        <AlertTriangle className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                      ) : null}
                    </div>
                    <div className="text-xs text-slate-200 truncate">{entry.source_text}</div>
                    <div className="text-[11px] text-slate-400 truncate">
                      {entry.current_target || '(Аударылмаған)'}
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* Right Specialist Editor */}
        <div className="lg:col-span-8 saas-card p-6 space-y-5">
          {!currentEntry ? (
            <div className="py-24 text-center text-sm text-slate-500">
              Сол жақтағы тізімнен түзетілетін жолды таңдаңыз.
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between flex-wrap gap-2 pb-3 border-b border-white/[0.07]">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-mono text-xs px-2.5 py-1 rounded-lg bg-cyan-500/10 border border-cyan-500/25 text-cyan-300 font-semibold">
                    {currentEntry.key}
                  </span>
                  {currentEntry.reviewed_by_human ? (
                    <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 font-semibold">
                      Маман растаған ({currentEntry.reviewer_name || 'QA'})
                    </span>
                  ) : (
                    <span className="text-xs px-2.5 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/30 font-mono">
                      reviewed_by_human = false
                    </span>
                  )}
                </div>
                <button
                  onClick={moveNext}
                  className="inline-flex items-center gap-1 text-xs text-cyan-300 hover:text-cyan-200 font-bold"
                >
                  <span>Келесі жол</span>
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>

              {/* Source vs Target */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 rounded-xl bg-[#050811] border border-white/[0.08] space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                      Орысша түпнұсқа (Source)
                    </span>
                    <span className="text-[11px] font-mono text-slate-500">
                      {currentEntry.source_text.length} т.
                    </span>
                  </div>
                  <div className="text-sm text-slate-100 whitespace-pre-wrap leading-relaxed min-h-[90px]">
                    {currentEntry.source_text}
                  </div>

                  {sourcePlaceholders.length > 0 && (
                    <div className="pt-2 border-t border-white/[0.06] flex flex-wrap gap-1.5 items-center">
                      <span className="text-[10px] text-slate-500">Кірістіру:</span>
                      {sourcePlaceholders.map((ph, idx) => (
                        <button
                          key={idx}
                          type="button"
                          onClick={() => updateDraftWithLatin(draft + (draft ? ' ' : '') + ph)}
                          className="font-mono text-[11px] px-2 py-0.5 rounded bg-cyan-500/15 hover:bg-cyan-500/25 text-cyan-300 border border-cyan-500/30"
                        >
                          + {ph}
                        </button>
                      ))}
                    </div>
                  )}

                  {currentEntry.en_text && (
                    <div className="pt-3 border-t border-white/[0.06] text-xs">
                      <span className="text-slate-500 block mb-0.5">English reference:</span>
                      <span className="text-slate-300">{currentEntry.en_text}</span>
                    </div>
                  )}
                </div>

                <div className="p-4 rounded-xl bg-[#050811] border border-cyan-500/30 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-bold text-cyan-300 uppercase tracking-wider">
                      {lang === 'kk' ? 'Қазақша аударма' : 'Өзбекше аударма'}
                    </span>
                    <span className="text-[11px] font-mono text-slate-400">
                      {draft.length} таңба • Ctrl+Enter сақтау
                    </span>
                  </div>

                  <textarea
                    rows={4}
                    value={draft}
                    onChange={(e) => updateDraftWithLatin(e.target.value)}
                    onKeyDown={(e) => {
                      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                        e.preventDefault();
                        handleSaveEntry(
                          draft,
                          true,
                          'Аударма сақталып, маман растауымен белгіленді!'
                        );
                      }
                    }}
                    className="w-full saas-input p-3 text-sm leading-relaxed"
                  />

                  {lang === 'kk' && (
                    <div className="flex flex-wrap gap-1">
                      {KAZAKH_CHARS.map((ch) => (
                        <button
                          key={ch}
                          type="button"
                          onClick={() => updateDraftWithLatin(draft + ch)}
                          className="w-6 h-6 rounded-md bg-white/[0.05] hover:bg-cyan-500/25 hover:text-cyan-200 text-xs font-bold text-slate-200 border border-white/[0.08] transition"
                        >
                          {ch}
                        </button>
                      ))}
                    </div>
                  )}

                  {lang === 'kk' && latinText && (
                    <div className="p-2.5 rounded-lg bg-white/[0.03] border border-white/[0.06] text-[11px] flex items-start gap-2">
                      <Languages className="w-3.5 h-3.5 text-cyan-400 shrink-0 mt-0.5" />
                      <div>
                        <span className="text-slate-500">Латын ({latinText.length} т.): </span>
                        <span className="text-slate-200">{latinText}</span>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Detected Issues & AI Suggestions */}
              {currentEntry.issues.length > 0 && (
                <div className="space-y-2.5">
                  {currentEntry.issues.map((iss) => (
                    <div
                      key={iss.id}
                      className="p-4 rounded-xl bg-white/[0.025] border border-white/[0.08] space-y-2"
                    >
                      <div className="flex items-center justify-between flex-wrap gap-2">
                        <span className="text-xs font-bold text-rose-300">
                          {ISSUE_TYPE_LABELS[iss.issue_type] || iss.issue_type} (
                          {iss.severity.toUpperCase()})
                        </span>
                        <span className="text-[11px] font-mono text-cyan-300 font-bold">
                          Confidence: {Math.round(iss.confidence * 100)}%
                        </span>
                      </div>
                      <p className="text-xs text-slate-300 leading-relaxed">{iss.evidence}</p>
                      {iss.suggestion && (
                        <div className="flex items-center justify-between gap-3 p-2.5 rounded-xl bg-gradient-to-r from-violet-500/15 to-cyan-500/10 border border-violet-500/30 text-xs">
                          <span className="text-emerald-300 font-semibold">
                            Ұсыныс: {iss.suggestion}
                          </span>
                          <button
                            type="button"
                            onClick={() =>
                              handleSaveEntry(
                                iss.suggestion,
                                true,
                                'AI ұсынысы қабылданып, маман растауымен сақталды!'
                              )
                            }
                            className="btn-primary px-3.5 py-1.5 text-xs shrink-0"
                          >
                            Түзетуді қабылдау
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Actions */}
              <div className="flex flex-wrap items-center justify-end gap-2.5 pt-2">
                <button
                  disabled={saving}
                  onClick={() =>
                    handleSaveEntry(
                      currentEntry.original_target,
                      true,
                      'Түзетуден бас тартылды, бастапқы мәтін сақталды.'
                    )
                  }
                  className="btn-secondary px-4 py-2 text-xs"
                >
                  <RotateCcw className="w-3.5 h-3.5 text-rose-400" />
                  <span>Түзетуден бас тарту</span>
                </button>

                <button
                  disabled={saving}
                  onClick={() =>
                    handleSaveEntry(
                      draft,
                      true,
                      'Жол маман тексерген аударма ретінде белгіленді!'
                    )
                  }
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/40 text-emerald-300 text-xs font-bold transition"
                >
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Тексерілді деп белгілеу</span>
                </button>

                <button
                  disabled={saving}
                  onClick={() =>
                    handleSaveEntry(
                      draft,
                      true,
                      'Қолмен енгізілген өзгеріс базаға сақталды (reviewed_by_human = true)!'
                    )
                  }
                  className="btn-primary px-5 py-2 text-xs font-bold"
                >
                  {saving ? (
                    <Sparkles className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Save className="w-3.5 h-3.5" />
                  )}
                  <span>Қолмен өзгертуді сақтау</span>
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
