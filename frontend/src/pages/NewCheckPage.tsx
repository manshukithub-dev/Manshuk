import React, { useRef, useState } from 'react';
import {
  UploadCloud,
  CheckCircle2,
  XCircle,
  Play,
  FileJson,
  FileSpreadsheet,
  Loader2,
  Sparkles,
  Trash2,
  ShieldCheck,
} from 'lucide-react';
import type { ProjectRun, UploadedFileItem } from '../types';
import { api } from '../api/client';

interface NewCheckPageProps {
  onRunCompleted: (run: ProjectRun) => void;
  onRunDemo: () => Promise<void>;
  runningDemo: boolean;
}

interface SlotState {
  uploading: boolean;
  file: UploadedFileItem | null;
  error: string | null;
  attemptedName?: string;
}

const SLOTS: {
  role: 'ru' | 'kk' | 'uz' | 'en' | 'glossary';
  expectedName: string;
  title: string;
  subtitle: string;
  accept: string;
  required?: boolean;
}[] = [
  {
    role: 'ru',
    expectedName: 'intl_ru.arb',
    title: 'Түпнұсқа (Орысша ARB)',
    subtitle: 'Міндетті бастапқы локализация файлы',
    accept: '.arb,.json',
    required: true,
  },
  {
    role: 'kk',
    expectedName: 'intl_kk.arb',
    title: 'Қазақша аударма (ARB)',
    subtitle: 'Қазақ тіліндегі мақсатты локализация файлы',
    accept: '.arb,.json',
  },
  {
    role: 'uz',
    expectedName: 'intl_uz.arb',
    title: 'Өзбекше аударма (ARB)',
    subtitle: 'Өзбек тіліндегі мақсатты локализация файлы',
    accept: '.arb,.json',
  },
  {
    role: 'en',
    expectedName: 'intl_en.arb',
    title: 'Ағылшынша референс (ARB)',
    subtitle: 'Қосымша контекст ретінде қолданылады',
    accept: '.arb,.json',
  },
  {
    role: 'glossary',
    expectedName: 'glossary.csv',
    title: 'Терминдер глоссарийі (CSV)',
    subtitle: 'Жүктелмесе, жүйелік базалық глоссарий қолданылады',
    accept: '.csv',
  },
];

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} Б`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} КБ`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} МБ`;
}

export const NewCheckPage: React.FC<NewCheckPageProps> = ({
  onRunCompleted,
  onRunDemo,
  runningDemo,
}) => {
  const [projectName, setProjectName] = useState('Мобильді ойын локализациясын тексеру');
  const [slots, setSlots] = useState<Record<string, SlotState>>({
    ru: { uploading: false, file: null, error: null },
    kk: { uploading: false, file: null, error: null },
    uz: { uploading: false, file: null, error: null },
    en: { uploading: false, file: null, error: null },
    glossary: { uploading: false, file: null, error: null },
  });
  const [dragRole, setDragRole] = useState<string | null>(null);
  const [progress, setProgress] = useState<number>(0);
  const [progressLabel, setProgressLabel] = useState<string>('');
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);

  const inputRefs = useRef<Record<string, HTMLInputElement | null>>({});

  const uploadToSlot = async (role: string, file: File) => {
    setSlots((prev) => ({
      ...prev,
      [role]: { uploading: true, file: null, error: null, attemptedName: file.name },
    }));
    try {
      const saved = await api.uploadFile(role, file);
      setSlots((prev) => ({
        ...prev,
        [role]: { uploading: false, file: saved, error: null, attemptedName: file.name },
      }));
    } catch (err) {
      setSlots((prev) => ({
        ...prev,
        [role]: {
          uploading: false,
          file: null,
          error: err instanceof Error ? err.message : 'Файлды жүктеу қатесі',
          attemptedName: file.name,
        },
      }));
    }
  };

  const handleBatchDrop = async (files: FileList) => {
    for (const file of Array.from(files)) {
      const low = file.name.toLowerCase();
      if (low.endsWith('.csv')) {
        await uploadToSlot('glossary', file);
      } else if (low.includes('ru')) {
        await uploadToSlot('ru', file);
      } else if (low.includes('kk') || low.includes('kz')) {
        await uploadToSlot('kk', file);
      } else if (low.includes('uz')) {
        await uploadToSlot('uz', file);
      } else if (low.includes('en')) {
        await uploadToSlot('en', file);
      } else if (!slots.ru.file) {
        await uploadToSlot('ru', file);
      } else {
        await uploadToSlot('kk', file);
      }
    }
  };

  const handleStartCheck = async () => {
    setRunError(null);
    if (!slots.ru.file) {
      setRunError('Алдымен түпнұсқа орысша ARB файлын (intl_ru.arb) жүктеңіз.');
      return;
    }
    if (!slots.kk.file && !slots.uz.file) {
      setRunError('Кемінде қазақша (intl_kk.arb) немесе өзбекше (intl_uz.arb) файлын жүктеңіз.');
      return;
    }

    setRunning(true);
    setProgress(18);
    setProgressLabel('ARB JSON және ICU құрылымы оқылуда...');

    const timer1 = window.setTimeout(() => {
      setProgress(52);
      setProgressLabel('12 қате түрі мен қазақ/өзбек морфологиясы тексерілуде...');
    }, 220);

    const timer2 = window.setTimeout(() => {
      setProgress(82);
      setProgressLabel('Глоссарий сәйкестігі және ресми латын ұзындығы есептелуде...');
    }, 480);

    try {
      const created = await api.createRun({
        name: projectName.trim() || 'Локализация тексеруі',
        ru_file_id: slots.ru.file.id,
        kk_file_id: slots.kk.file?.id ?? null,
        uz_file_id: slots.uz.file?.id ?? null,
        en_file_id: slots.en.file?.id ?? null,
        glossary_file_id: slots.glossary.file?.id ?? null,
        use_llm: true,
      });
      window.clearTimeout(timer1);
      window.clearTimeout(timer2);
      setProgress(100);
      setProgressLabel('Тексеру сәтті аяқталды!');
      setTimeout(() => {
        onRunCompleted(created);
      }, 280);
    } catch (err) {
      window.clearTimeout(timer1);
      window.clearTimeout(timer2);
      setProgress(0);
      setRunError(err instanceof Error ? err.message : 'Тексеру кезінде қате пайда болды');
    } finally {
      setRunning(false);
    }
  };

  const uploadedCount = Object.values(slots).filter((s) => s.file).length;

  return (
    <div className="space-y-6">
      {/* Workflow Stepper + Project Header */}
      <div className="saas-card p-6 space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-white/[0.06]">
          <div className="flex items-center gap-3 text-xs font-semibold flex-wrap">
            <span className="px-2.5 py-1 rounded-full bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
              1. ARB / CSV жүктеу ({uploadedCount}/5)
            </span>
            <span className="text-slate-600">→</span>
            <span className="px-2.5 py-1 rounded-full bg-white/[0.04] text-slate-300 border border-white/[0.07]">
              2. Flutter gen-l10n & ICU тексеру
            </span>
            <span className="text-slate-600">→</span>
            <span className="px-2.5 py-1 rounded-full bg-white/[0.04] text-slate-300 border border-white/[0.07]">
              3. 12-санаттық AI / NLP талдау
            </span>
          </div>

          <button
            type="button"
            disabled={runningDemo || running}
            onClick={onRunDemo}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-amber-500/15 hover:bg-amber-500/25 border border-amber-400/40 text-amber-200 text-xs font-bold transition disabled:opacity-50"
          >
            <Sparkles className="w-3.5 h-3.5 text-amber-400" />
            <span>{runningDemo ? 'DEMO жүктелуде...' : '[DEMO] Үлгі ARB файлдармен тексеру'}</span>
          </button>
        </div>

        <div className="space-y-2">
          <label className="text-xs font-bold uppercase tracking-wider text-slate-400">
            Тексеру жобасының атауы
          </label>
          <input
            type="text"
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
            placeholder="Мысалы: Grand Mobile v4.5 — Қазақша жаңарту"
            className="w-full saas-input px-4 py-2.5 text-sm"
          />
        </div>
      </div>

      {/* Multi-file Drag & Drop Zone */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragRole('batch');
        }}
        onDragLeave={() => setDragRole(null)}
        onDrop={(e) => {
          e.preventDefault();
          setDragRole(null);
          if (e.dataTransfer.files?.length) {
            handleBatchDrop(e.dataTransfer.files);
          }
        }}
        className={`relative overflow-hidden p-7 rounded-2xl border-2 border-dashed transition-all text-center ${
          dragRole === 'batch'
            ? 'border-cyan-400 bg-cyan-500/10 shadow-glow'
            : 'border-white/[0.12] bg-[#0A0F1E]/60 hover:border-cyan-400/40 hover:bg-[#0A0F1E]/90'
        }`}
      >
        <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-cyan-500/20 to-violet-500/20 border border-cyan-400/30 flex items-center justify-center mx-auto mb-3">
          <UploadCloud className="w-6 h-6 text-cyan-400" />
        </div>
        <div className="text-sm font-bold text-white">
          Барлық ARB және CSV файлдарын осы аймаққа бірден сүйреп әкеліңіз (Drag & Drop)
        </div>
        <p className="text-xs text-slate-400 mt-1.5">
          <code className="font-mono text-cyan-300">intl_ru.arb</code>,{' '}
          <code className="font-mono text-cyan-300">intl_kk.arb</code>,{' '}
          <code className="font-mono text-cyan-300">intl_uz.arb</code>,{' '}
          <code className="font-mono text-cyan-300">intl_en.arb</code> және{' '}
          <code className="font-mono text-violet-300">glossary.csv</code> атаулары бойынша автоматты
          бөлінеді • 5 500+ кілтке дейін жылдам өңделеді
        </p>
      </div>

      {/* 5 Individual Upload Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {SLOTS.map((slot) => {
          const st = slots[slot.role];
          const isCsv = slot.role === 'glossary';
          return (
            <div
              key={slot.role}
              onDragOver={(e) => {
                e.preventDefault();
                setDragRole(slot.role);
              }}
              onDragLeave={() => setDragRole(null)}
              onDrop={(e) => {
                e.preventDefault();
                setDragRole(null);
                const f = e.dataTransfer.files?.[0];
                if (f) uploadToSlot(slot.role, f);
              }}
              className={`saas-card-hover p-5 flex flex-col justify-between gap-4 ${
                dragRole === slot.role
                  ? '!border-cyan-400 !bg-cyan-500/10'
                  : st.error
                  ? '!border-rose-500/60'
                  : st.file
                  ? '!border-emerald-500/45'
                  : ''
              }`}
            >
              <div className="space-y-2.5">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-3">
                    <div
                      className={`p-2.5 rounded-xl border ${
                        isCsv
                          ? 'bg-violet-500/10 border-violet-500/25 text-violet-400'
                          : 'bg-cyan-500/10 border-cyan-500/25 text-cyan-400'
                      }`}
                    >
                      {isCsv ? (
                        <FileSpreadsheet className="w-5 h-5" />
                      ) : (
                        <FileJson className="w-5 h-5" />
                      )}
                    </div>
                    <div>
                      <div className="text-sm font-bold font-mono text-white flex items-center gap-2">
                        <span>{slot.expectedName}</span>
                        {slot.required && (
                          <span className="font-sans text-[10px] px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/30">
                            Міндетті
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-slate-300 mt-0.5">{slot.title}</div>
                    </div>
                  </div>
                </div>

                <p className="text-[11px] text-slate-400">{slot.subtitle}</p>

                {st.uploading && (
                  <div className="p-3 rounded-xl bg-[#050811] border border-white/[0.08] flex items-center gap-2 text-xs text-cyan-300">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>JSON құрылымы тексеріліп, жүктелуде...</span>
                  </div>
                )}

                {st.error && (
                  <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/40 space-y-1">
                    <div className="flex items-center gap-1.5 text-xs font-bold text-rose-300">
                      <XCircle className="w-4 h-4 shrink-0" />
                      <span>Құрылым қатесі ({st.attemptedName})</span>
                    </div>
                    <p className="text-[11px] text-rose-200/90 leading-relaxed break-words">
                      {st.error}
                    </p>
                  </div>
                )}

                {st.file && (
                  <div className="p-3.5 rounded-xl bg-emerald-500/[0.08] border border-emerald-500/30 space-y-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="flex items-center gap-1.5 font-bold text-emerald-300 truncate">
                        <CheckCircle2 className="w-4 h-4 shrink-0" />
                        <span className="truncate font-mono">{st.file.original_filename}</span>
                      </span>
                      <button
                        type="button"
                        onClick={() =>
                          setSlots((prev) => ({
                            ...prev,
                            [slot.role]: { uploading: false, file: null, error: null },
                          }))
                        }
                        className="p-1 text-slate-400 hover:text-rose-400"
                        title="Тазарту"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                    <div className="grid grid-cols-2 gap-1.5 text-[11px] text-slate-300 font-mono">
                      <div>
                        <span className="text-slate-500 font-sans">Көлемі:</span>{' '}
                        {formatBytes(st.file.size_bytes)}
                      </div>
                      <div>
                        <span className="text-slate-500 font-sans">Формат:</span>{' '}
                        {st.file.file_format}
                      </div>
                      <div>
                        <span className="text-slate-500 font-sans">Жол саны:</span>{' '}
                        {st.file.line_count}
                      </div>
                      <div>
                        <span className="text-slate-500 font-sans">Кілт саны:</span>{' '}
                        {st.file.key_count}
                      </div>
                    </div>
                    <div className="text-[11px] text-emerald-400 font-semibold flex items-center gap-1">
                      <ShieldCheck className="w-3.5 h-3.5" />
                      <span>Жүктелді • Валидация сәтті өтті</span>
                    </div>
                  </div>
                )}
              </div>

              <div>
                <input
                  ref={(el) => {
                    inputRefs.current[slot.role] = el;
                  }}
                  type="file"
                  accept={slot.accept}
                  className="hidden"
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) uploadToSlot(slot.role, f);
                    e.target.value = '';
                  }}
                />
                <button
                  type="button"
                  onClick={() => inputRefs.current[slot.role]?.click()}
                  className="btn-secondary w-full py-2 text-xs"
                >
                  Файлды таңдау ({slot.accept})
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Progress Bar */}
      {(running || progress > 0) && (
        <div className="saas-card p-5 border-cyan-500/35 space-y-2.5">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-cyan-300 flex items-center gap-2">
              {running && <Loader2 className="w-4 h-4 animate-spin" />}
              <span>{progressLabel}</span>
            </span>
            <span className="font-mono font-bold text-white">{progress}%</span>
          </div>
          <div className="w-full h-2.5 rounded-full bg-[#050811] overflow-hidden border border-white/[0.08]">
            <div
              className="h-full bg-gradient-to-r from-cyan-400 via-blue-500 to-violet-500 transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {runError && (
        <div className="p-4 rounded-xl bg-rose-500/15 border border-rose-500/40 text-xs text-rose-200 font-semibold">
          {runError}
        </div>
      )}

      <div className="flex justify-end">
        <button
          type="button"
          disabled={running || !slots.ru.file || (!slots.kk.file && !slots.uz.file)}
          onClick={handleStartCheck}
          className="btn-primary px-8 py-3.5 text-sm font-extrabold"
        >
          <Play className="w-4 h-4" />
          <span>Тексеруді бастау</span>
        </button>
      </div>
    </div>
  );
};
