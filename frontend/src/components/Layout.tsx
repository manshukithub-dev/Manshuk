import React, { useEffect, useState } from 'react';
import {
  LayoutDashboard,
  FilePlus2,
  FolderKanban,
  AlertTriangle,
  PenTool,
  BookOpen,
  FileBarChart2,
  History,
  Users,
  Settings,
  Menu,
  X,
  Sparkles,
  ShieldCheck,
  Languages,
  Search,
  ChevronRight,
  Command,
  Play,
  Download,
} from 'lucide-react';
import type { AppSettings, PageId, ProjectRun, TeamMember } from '../types';
import { api, downloadBlob } from '../api/client';

interface LayoutProps {
  activePage: PageId;
  onNavigate: (page: PageId) => void;
  runs: ProjectRun[];
  activeRunId: number | null;
  onSelectRun: (runId: number) => void;
  activeLang: 'kk' | 'uz';
  onSelectLang: (lang: 'kk' | 'uz') => void;
  onRunDemo?: () => void;
  activeReviewer: TeamMember | null;
  settings: AppSettings | null;
  children: React.ReactNode;
}

interface NavItem {
  id: PageId;
  label: string;
  group: string;
  icon: React.ComponentType<{ className?: string }>;
}

const MENU_ITEMS: NavItem[] = [
  { id: 'dashboard', label: 'Dashboard', group: 'НЕГІЗГІ АҒЫН', icon: LayoutDashboard },
  { id: 'new-check', label: 'Жаңа тексеру', group: 'НЕГІЗГІ АҒЫН', icon: FilePlus2 },
  { id: 'files', label: 'Файлдар', group: 'НЕГІЗГІ АҒЫН', icon: FolderKanban },
  { id: 'issues', label: 'Қателерді талдау', group: 'ЛИНГВИСТИКА ЖӘНЕ QA', icon: AlertTriangle },
  { id: 'editor', label: 'Аударманы түзету', group: 'ЛИНГВИСТИКА ЖӘНЕ QA', icon: PenTool },
  { id: 'glossary', label: 'Глоссарий', group: 'ЛИНГВИСТИКА ЖӘНЕ QA', icon: BookOpen },
  { id: 'reports', label: 'Есептер', group: 'ЕСЕП ПЕН БАСҚАРУ', icon: FileBarChart2 },
  { id: 'history', label: 'Жобалар тарихы', group: 'ЕСЕП ПЕН БАСҚАРУ', icon: History },
  { id: 'team', label: 'Команда', group: 'ЕСЕП ПЕН БАСҚАРУ', icon: Users },
  { id: 'settings', label: 'Баптаулар', group: 'ЕСЕП ПЕН БАСҚАРУ', icon: Settings },
];

const GROUPS = ['НЕГІЗГІ АҒЫН', 'ЛИНГВИСТИКА ЖӘНЕ QA', 'ЕСЕП ПЕН БАСҚАРУ'];

export const Layout: React.FC<LayoutProps> = ({
  activePage,
  onNavigate,
  runs,
  activeRunId,
  onSelectRun,
  activeLang,
  onSelectLang,
  onRunDemo,
  activeReviewer,
  settings,
  children,
}) => {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [cmdOpen, setCmdOpen] = useState(false);
  const [cmdQuery, setCmdQuery] = useState('');
  const [latinModalOpen, setLatinModalOpen] = useState(false);
  const [cyrInput, setCyrInput] = useState('Қазақша ойын локализациясының сапасын тексеру: {name}!');
  const [latinResult, setLatinResult] = useState<{
    latin_text: string;
    cyrillic_length: number;
    latin_length: number;
    overflow: boolean;
  } | null>(null);

  const currentRun = runs.find((r) => r.id === activeRunId) || runs[0] || null;

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setCmdOpen((v) => !v);
      } else if (e.key === 'Escape') {
        setCmdOpen(false);
        setLatinModalOpen(false);
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  const handleOpenLatinTool = async () => {
    setLatinModalOpen(true);
    try {
      const res = await api.transliterate(cyrInput, settings?.button_max_chars || 24);
      setLatinResult(res);
    } catch {
      // ignore
    }
  };

  const handleTransliterateChange = async (val: string) => {
    setCyrInput(val);
    try {
      const res = await api.transliterate(val, settings?.button_max_chars || 24);
      setLatinResult(res);
    } catch {
      // ignore
    }
  };

  const filteredCmdItems = MENU_ITEMS.filter(
    (m) =>
      m.label.toLowerCase().includes(cmdQuery.toLowerCase()) ||
      m.id.toLowerCase().includes(cmdQuery.toLowerCase())
  );

  const sidebarContent = (
    <div className="flex flex-col h-full bg-[#070B16]/95 backdrop-blur-2xl border-r border-white/[0.07] w-[276px] select-none">
      {/* Brand + Reviewer Profile */}
      <div className="p-5 border-b border-white/[0.06] space-y-4">
        <div className="flex items-center justify-between">
          <button
            onClick={() => onNavigate('dashboard')}
            className="flex items-center gap-3 group text-left"
          >
            <div className="relative w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-400 via-blue-600 to-violet-600 flex items-center justify-center shadow-[0_0_24px_-4px_rgba(56,189,248,0.5)] font-black text-white text-sm tracking-tight group-hover:scale-105 transition-transform">
              QL
              <span className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-emerald-400 ring-2 ring-[#070B16]" />
            </div>
            <div>
              <div className="font-black text-sm tracking-wider bg-gradient-to-r from-white via-cyan-200 to-violet-300 bg-clip-text text-transparent">
                QAZAQ LOC QA
              </div>
              <div className="text-[11px] text-slate-400 font-medium">
                Localization Intelligence
              </div>
            </div>
          </button>
          <button
            onClick={() => setMobileOpen(false)}
            className="lg:hidden p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/[0.06]"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* User Profile Card */}
        <button
          onClick={() => {
            onNavigate('team');
            setMobileOpen(false);
          }}
          className="w-full flex items-center gap-3 p-2.5 rounded-xl bg-white/[0.03] hover:bg-white/[0.06] border border-white/[0.07] hover:border-cyan-400/30 transition-all text-left group"
        >
          <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-violet-600 via-indigo-500 to-cyan-400 flex items-center justify-center text-xs font-extrabold text-white shrink-0 shadow-md">
            {activeReviewer?.avatar_initials || 'АС'}
          </div>
          <div className="min-w-0 flex-1">
            <div className="text-xs font-semibold text-slate-100 truncate flex items-center gap-1.5">
              <span className="truncate">{activeReviewer?.name || 'Айгерім Сейітова'}</span>
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0" />
            </div>
            <div className="text-[11px] text-cyan-400/90 truncate">
              {activeReviewer?.role || 'Қазақ тілінің бас лингвисі'}
            </div>
          </div>
          <ChevronRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-cyan-300 transition" />
        </button>
      </div>

      {/* Categorized Navigation */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-5">
        {GROUPS.map((group) => {
          const items = MENU_ITEMS.filter((i) => i.group === group);
          return (
            <div key={group} className="space-y-1">
              <div className="px-3 pb-1 text-[10px] font-bold tracking-widest uppercase text-slate-500">
                {group}
              </div>
              {items.map((item) => {
                const Icon = item.icon;
                const isActive = activePage === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => {
                      onNavigate(item.id);
                      setMobileOpen(false);
                    }}
                    className={`relative w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-[13px] font-medium transition-all duration-150 group ${
                      isActive
                        ? 'bg-gradient-to-r from-cyan-500/15 via-blue-500/10 to-violet-500/15 text-white border border-cyan-400/25 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.08)]'
                        : 'text-slate-400 hover:text-slate-100 hover:bg-white/[0.04] border border-transparent'
                    }`}
                  >
                    {isActive && (
                      <span className="absolute left-0 top-2 bottom-2 w-1 rounded-r-full bg-gradient-to-b from-cyan-400 to-violet-500 shadow-[0_0_10px_rgba(56,189,248,0.9)]" />
                    )}
                    <span className="flex items-center gap-3">
                      <Icon
                        className={`w-4 h-4 transition-colors ${
                          isActive
                            ? 'text-cyan-400'
                            : 'text-slate-500 group-hover:text-slate-300'
                        }`}
                      />
                      <span>{item.label}</span>
                    </span>
                    {item.id === 'issues' && currentRun && currentRun.total_issues > 0 && (
                      <span className="px-2 py-0.5 text-[10px] font-extrabold rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/35">
                        {currentRun.total_issues}
                      </span>
                    )}
                    {item.id === 'history' && runs.length > 0 && (
                      <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-white/[0.06] text-slate-300">
                        {runs.length}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          );
        })}
      </nav>

      {/* Bottom Quick Tools & AI Status */}
      <div className="p-4 border-t border-white/[0.06] space-y-2.5">
        <button
          onClick={handleOpenLatinTool}
          className="w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl bg-white/[0.03] hover:bg-white/[0.07] border border-white/[0.08] hover:border-cyan-400/30 text-xs font-semibold text-slate-200 transition group"
        >
          <span className="flex items-center gap-2">
            <Languages className="w-4 h-4 text-cyan-400" />
            <span>Қазақ латын транслитераторы</span>
          </span>
          <span className="text-[10px] text-slate-500 group-hover:text-cyan-300">A→Ä</span>
        </button>

        <div className="flex items-center justify-between px-3.5 py-2 rounded-xl bg-[#050811]/90 border border-white/[0.06] text-[11px]">
          <span className="flex items-center gap-1.5 text-slate-400">
            {settings?.has_api_key ? (
              <Sparkles className="w-3.5 h-3.5 text-violet-400" />
            ) : (
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            )}
            <span>Қозғалтқыш:</span>
          </span>
          <span
            className={`font-bold ${
              settings?.has_api_key ? 'text-violet-300' : 'text-emerald-300'
            }`}
          >
            {settings?.has_api_key ? 'Hybrid LLM + Ереже' : '12-Rule NLP Engine'}
          </span>
        </div>
      </div>
    </div>
  );

  const activeNavObj = MENU_ITEMS.find((m) => m.id === activePage);

  return (
    <div className="min-h-screen flex ambient-canvas text-slate-100">
      {/* Desktop Sidebar */}
      <aside className="hidden lg:block shrink-0 h-screen sticky top-0 z-30">
        {sidebarContent}
      </aside>

      {/* Mobile Drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden flex">
          <div
            className="fixed inset-0 bg-black/75 backdrop-blur-sm"
            onClick={() => setMobileOpen(false)}
          />
          <div className="relative z-10 h-full">{sidebarContent}</div>
        </div>
      )}

      {/* Main Column */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Glass Navigation Header */}
        <header className="sticky top-0 z-20 h-16 bg-[#050811]/80 backdrop-blur-xl border-b border-white/[0.07] px-4 sm:px-6 lg:px-8 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5 min-w-0">
            <button
              onClick={() => setMobileOpen(true)}
              className="lg:hidden p-2 rounded-xl bg-white/[0.04] border border-white/[0.08] text-slate-300 hover:text-white"
            >
              <Menu className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-2 text-xs sm:text-sm min-w-0">
              <span className="hidden sm:inline text-slate-500 font-medium">Qazaq Loc QA</span>
              <ChevronRight className="hidden sm:inline w-3.5 h-3.5 text-slate-600 shrink-0" />
              <h1 className="font-bold text-slate-100 truncate text-sm sm:text-base">
                {activeNavObj?.label || 'Dashboard'}
              </h1>
            </div>

            {currentRun?.is_demo && (
              <span className="hidden md:inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-extrabold tracking-wide bg-amber-500/15 text-amber-300 border border-amber-500/35">
                DEMO РЕЖИМ
              </span>
            )}
          </div>

          <div className="flex items-center gap-2.5">
            {/* Linear/Vercel Command Palette Trigger */}
            <button
              onClick={() => setCmdOpen(true)}
              className="hidden md:flex items-center gap-3 px-3 py-1.5 rounded-xl bg-white/[0.03] hover:bg-white/[0.07] border border-white/[0.08] text-xs text-slate-400 hover:text-slate-200 transition"
              title="Жылдам пәрмендер мәзірі (Ctrl+K)"
            >
              <Search className="w-3.5 h-3.5 text-slate-400" />
              <span>Жылдам өту...</span>
              <kbd className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-white/[0.06] text-slate-300 border border-white/[0.08]">
                Ctrl K
              </kbd>
            </button>

            {/* Active SQLite Project Switcher */}
            {runs.length > 0 && (
              <select
                value={currentRun?.id || ''}
                onChange={(e) => onSelectRun(Number(e.target.value))}
                className="hidden sm:block saas-input px-3 py-1.5 text-xs font-medium max-w-[200px]"
              >
                {runs.map((r) => {
                  const cleanName = r.name.replace(/\s*—\s*Қазақша және Өзбекше QA$/i, '');
                  return (
                    <option key={r.id} value={r.id} className="bg-[#0A0F1E] text-slate-100">
                      #{r.id} • {cleanName}
                    </option>
                  );
                })}
              </select>
            )}

            {/* Separate Kazakh / Uzbek Switcher Buttons */}
            <div className="inline-flex items-center gap-1 rounded-xl bg-white/[0.03] p-1 border border-white/[0.08]">
              <button
                type="button"
                onClick={() => onSelectLang('kk')}
                disabled={Boolean(currentRun && !currentRun.has_kk)}
                className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${
                  activeLang === 'kk'
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-400/40 shadow-[0_0_12px_-3px_rgba(56,189,248,0.45)]'
                    : 'text-slate-400 hover:text-slate-100 border border-transparent disabled:opacity-40'
                }`}
              >
                Қазақша
              </button>
              <button
                type="button"
                onClick={() => onSelectLang('uz')}
                disabled={Boolean(currentRun && !currentRun.has_uz)}
                className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${
                  activeLang === 'uz'
                    ? 'bg-violet-500/20 text-violet-300 border border-violet-400/40 shadow-[0_0_12px_-3px_rgba(139,92,246,0.45)]'
                    : 'text-slate-400 hover:text-slate-100 border border-transparent disabled:opacity-40'
                }`}
              >
                Өзбекше
              </button>
            </div>

            <button
              onClick={() => onNavigate('new-check')}
              className="btn-primary px-3.5 py-1.5 text-xs shrink-0"
            >
              <FilePlus2 className="w-3.5 h-3.5" />
              <span>Жаңа тексеру</span>
            </button>
          </div>
        </header>

        <main
          key={activePage}
          className="flex-1 p-4 sm:p-6 lg:p-8 max-w-[1600px] w-full mx-auto animate-page"
        >
          {children}
        </main>
      </div>

      {/* Command Palette (Ctrl+K) — Linear / Vercel Inspired */}
      {cmdOpen && (
        <div
          className="fixed inset-0 z-50 flex items-start justify-center pt-[12vh] p-4 bg-black/75 backdrop-blur-sm"
          onClick={() => setCmdOpen(false)}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="saas-card max-w-xl w-full overflow-hidden border-white/[0.14] shadow-2xl"
          >
            <div className="flex items-center gap-3 px-4 py-3.5 border-b border-white/[0.08]">
              <Command className="w-4 h-4 text-cyan-400 shrink-0" />
              <input
                autoFocus
                value={cmdQuery}
                onChange={(e) => setCmdQuery(e.target.value)}
                placeholder="Бетке өту немесе әрекет таңдау..."
                className="w-full bg-transparent text-sm text-white placeholder:text-slate-500 focus:outline-none"
              />
              <button
                onClick={() => setCmdOpen(false)}
                className="text-[11px] px-2 py-0.5 rounded bg-white/[0.06] text-slate-400"
              >
                ESC
              </button>
            </div>

            <div className="max-h-80 overflow-y-auto p-2 space-y-1">
              <div className="px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-slate-500">
                Жылдам әрекеттер
              </div>
              {onRunDemo && (
                <button
                  onClick={() => {
                    setCmdOpen(false);
                    onRunDemo();
                  }}
                  className="w-full flex items-center justify-between px-3 py-2.5 rounded-xl hover:bg-amber-500/15 text-xs text-amber-200 transition"
                >
                  <span className="flex items-center gap-2.5 font-semibold">
                    <Play className="w-4 h-4 text-amber-400" />
                    <span>[DEMO] Grand RP Mobile үлгі жобасын іске қосу</span>
                  </span>
                  <span className="text-[10px] text-amber-400/80">1-Click QA</span>
                </button>
              )}

              <button
                onClick={() => {
                  setCmdOpen(false);
                  handleOpenLatinTool();
                }}
                className="w-full flex items-center justify-between px-3 py-2.5 rounded-xl hover:bg-white/[0.06] text-xs text-slate-200 transition"
              >
                <span className="flex items-center gap-2.5">
                  <Languages className="w-4 h-4 text-cyan-400" />
                  <span>Ресми қазақ латын әліпбиіне транслитерациялау</span>
                </span>
                <span className="text-[10px] text-slate-500">Құрал</span>
              </button>

              {currentRun?.has_kk && (
                <button
                  onClick={() => {
                    setCmdOpen(false);
                    downloadBlob(
                      `/api/reports/${currentRun.id}/export-arb?lang=kk`,
                      'intl_kk_fixed.arb'
                    );
                  }}
                  className="w-full flex items-center justify-between px-3 py-2.5 rounded-xl hover:bg-emerald-500/15 text-xs text-emerald-300 transition"
                >
                  <span className="flex items-center gap-2.5 font-semibold">
                    <Download className="w-4 h-4 text-emerald-400" />
                    <span>intl_kk_fixed.arb файлын бірден экспорттау</span>
                  </span>
                  <span className="text-[10px] text-emerald-400/80">gen-l10n</span>
                </button>
              )}

              <div className="px-2.5 pt-2 pb-1 text-[10px] font-bold uppercase tracking-wider text-slate-500">
                Барлық бөлімдер
              </div>
              {filteredCmdItems.map((item) => {
                const Icon = item.icon;
                return (
                  <button
                    key={item.id}
                    onClick={() => {
                      onNavigate(item.id);
                      setCmdOpen(false);
                      setCmdQuery('');
                    }}
                    className="w-full flex items-center justify-between px-3 py-2 rounded-xl hover:bg-white/[0.06] text-xs text-slate-200 transition"
                  >
                    <span className="flex items-center gap-2.5">
                      <Icon className="w-4 h-4 text-cyan-400" />
                      <span>{item.label}</span>
                    </span>
                    <span className="text-[10px] text-slate-500">{item.group}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Official Kazakh Latin Transliteration Modal */}
      {latinModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
          <div className="saas-card max-w-xl w-full p-6 border-white/[0.12] space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-xl bg-cyan-500/15 border border-cyan-500/30">
                  <Languages className="w-5 h-5 text-cyan-400" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white">
                    Ресми қазақ латын әліпбиіне транслитерация
                  </h3>
                  <p className="text-[11px] text-slate-400">
                    Плейсхолдерлер (<code>{'{name}'}</code>) мен HTML тегтері өзгеріссіз сақталады
                  </p>
                </div>
              </div>
              <button
                onClick={() => setLatinModalOpen(false)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/[0.06]"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-slate-400">Қазақша (Кирилл) мәтіні:</label>
              <textarea
                rows={3}
                value={cyrInput}
                onChange={(e) => handleTransliterateChange(e.target.value)}
                className="w-full saas-input p-3 text-sm"
              />
            </div>

            {latinResult && (
              <div className="space-y-3">
                <div className="p-4 rounded-xl bg-gradient-to-br from-cyan-500/10 to-violet-500/10 border border-cyan-400/30">
                  <div className="text-[10px] uppercase tracking-wider text-cyan-300 font-bold mb-1">
                    Латын нұсқасы (2021 стандарт)
                  </div>
                  <div className="text-sm font-semibold text-white break-words">
                    {latinResult.latin_text || '—'}
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-3 text-center">
                  <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.07]">
                    <div className="text-[11px] text-slate-400">Кирилл</div>
                    <div className="text-base font-extrabold text-white mt-0.5">
                      {latinResult.cyrillic_length} т.
                    </div>
                  </div>
                  <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.07]">
                    <div className="text-[11px] text-slate-400">Латын</div>
                    <div className="text-base font-extrabold text-cyan-300 mt-0.5">
                      {latinResult.latin_length} т.
                    </div>
                  </div>
                  <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.07]">
                    <div className="text-[11px] text-slate-400">UI Лимит</div>
                    <div
                      className={`text-xs font-extrabold mt-1.5 ${
                        latinResult.overflow ? 'text-amber-400' : 'text-emerald-400'
                      }`}
                    >
                      {latinResult.overflow
                        ? `Асты (>${settings?.button_max_chars || 24})`
                        : 'Сыйымды (OK)'}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
