import React, { useEffect, useRef, useState } from 'react';
import {
  Eye,
  Trash2,
  FileJson,
  FileSpreadsheet,
  CheckCircle2,
  X,
  Download,
  Search,
  Upload,
} from 'lucide-react';
import type { UploadedFileItem } from '../types';
import { api, downloadBlob } from '../api/client';

export const FilesPage: React.FC = () => {
  const [files, setFiles] = useState<UploadedFileItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [roleFilter, setRoleFilter] = useState<string>('all');
  const [search, setSearch] = useState<string>('');
  const [uploadRole, setUploadRole] = useState<'ru' | 'kk' | 'uz' | 'en' | 'glossary'>('kk');
  const [uploadErr, setUploadErr] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement | null>(null);

  const [preview, setPreview] = useState<{
    filename: string;
    role: string;
    format: string;
    locale: string | null;
    key_count: number;
    metadata_count: number;
    line_count: number;
    sample: Record<string, unknown>[];
  } | null>(null);

  const loadFiles = async () => {
    setLoading(true);
    try {
      const list = await api.listFiles();
      setFiles(list);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFiles();
  }, []);

  const handlePreview = async (id: number) => {
    const data = await api.previewFile(id);
    setPreview(data);
  };

  const handleDelete = async (id: number) => {
    await api.deleteFile(id);
    await loadFiles();
  };

  const handleQuickUpload = async (file: File) => {
    setUploadErr(null);
    try {
      await api.uploadFile(uploadRole, file);
      await loadFiles();
    } catch (err) {
      setUploadErr(err instanceof Error ? err.message : 'Жүктеу қатесі');
    }
  };

  const filtered = files.filter((f) => {
    if (roleFilter !== 'all' && f.role !== roleFilter) return false;
    if (search && !f.original_filename.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Header & Quick Upload Bar */}
      <div className="saas-card p-5 space-y-4">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-extrabold text-white">
              ARB және CSV файлдар репозиторийі
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Жүктелген барлық файлдардың UTF-8 кодталуы, кілттер саны және Flutter{' '}
              <code className="font-mono text-cyan-300">@metadata</code> құрылымы тексерілген.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <select
              value={uploadRole}
              onChange={(e) =>
                setUploadRole(e.target.value as 'ru' | 'kk' | 'uz' | 'en' | 'glossary')
              }
              className="saas-input px-3 py-2 text-xs font-semibold"
            >
              <option value="ru" className="bg-[#0A0F1E]">RU — Түпнұсқа (.arb)</option>
              <option value="kk" className="bg-[#0A0F1E]">KK — Қазақша (.arb)</option>
              <option value="uz" className="bg-[#0A0F1E]">UZ — Өзбекше (.arb)</option>
              <option value="en" className="bg-[#0A0F1E]">EN — Референс (.arb)</option>
              <option value="glossary" className="bg-[#0A0F1E]">CSV — Глоссарий (.csv)</option>
            </select>

            <input
              ref={fileRef}
              type="file"
              accept={uploadRole === 'glossary' ? '.csv' : '.arb,.json'}
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) handleQuickUpload(f);
                e.target.value = '';
              }}
            />
            <button
              onClick={() => fileRef.current?.click()}
              className="btn-primary px-4 py-2 text-xs"
            >
              <Upload className="w-3.5 h-3.5" />
              <span>Файл қосу</span>
            </button>
          </div>
        </div>

        {uploadErr && (
          <div className="p-3 rounded-xl bg-rose-500/15 border border-rose-500/40 text-xs text-rose-200">
            {uploadErr}
          </div>
        )}

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-3 border-t border-white/[0.06]">
          <div className="flex flex-wrap gap-1.5">
            {[
              { id: 'all', label: `Барлығы (${files.length})` },
              { id: 'ru', label: 'RU Түпнұсқа' },
              { id: 'kk', label: 'KK Қазақша' },
              { id: 'uz', label: 'UZ Өзбекше' },
              { id: 'en', label: 'EN Референс' },
              { id: 'glossary', label: 'CSV Глоссарий' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setRoleFilter(tab.id)}
                className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition border ${
                  roleFilter === tab.id
                    ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/35'
                    : 'bg-white/[0.03] text-slate-400 border-white/[0.07] hover:text-slate-200'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="relative w-full sm:w-64">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Файл атауымен іздеу..."
              className="w-full saas-input pl-9 pr-3 py-1.5 text-xs"
            />
          </div>
        </div>
      </div>

      {/* Files Table */}
      {loading ? (
        <div className="text-center py-16 text-sm text-slate-400">Файлдар жүктелуде...</div>
      ) : filtered.length === 0 ? (
        <div className="saas-card p-12 border-dashed text-center text-sm text-slate-400">
          Сәйкес файлдар табылмады. Жоғарыдағы «Файл қосу» батырмасын немесе «Жаңа тексеру» бетін
          пайдаланыңыз.
        </div>
      ) : (
        <div className="saas-card overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-white/[0.07] text-slate-400 bg-white/[0.02]">
                <th className="py-3.5 px-5">Файл атауы</th>
                <th className="py-3.5 px-4">Рөлі</th>
                <th className="py-3.5 px-4">Формат</th>
                <th className="py-3.5 px-4">Жол саны</th>
                <th className="py-3.5 px-4">Кілт / Термин</th>
                <th className="py-3.5 px-4">Көлемі</th>
                <th className="py-3.5 px-4">Күйі</th>
                <th className="py-3.5 px-5 text-right">Әрекеттер</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.05]">
              {filtered.map((f) => (
                <tr key={f.id} className="hover:bg-white/[0.03] transition">
                  <td className="py-3.5 px-5 font-medium text-slate-100 flex items-center gap-2.5">
                    {f.file_format === 'CSV' ? (
                      <FileSpreadsheet className="w-4 h-4 text-violet-400 shrink-0" />
                    ) : (
                      <FileJson className="w-4 h-4 text-cyan-400 shrink-0" />
                    )}
                    <span className="font-mono">{f.original_filename}</span>
                    {f.is_demo && (
                      <span className="px-1.5 py-0.5 text-[10px] rounded bg-amber-500/20 text-amber-300 font-bold">
                        DEMO
                      </span>
                    )}
                  </td>
                  <td className="py-3.5 px-4">
                    <span className="px-2 py-0.5 rounded-md bg-cyan-500/10 border border-cyan-500/25 uppercase font-mono font-bold text-cyan-300 text-[11px]">
                      {f.role}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 font-mono text-slate-300">{f.file_format}</td>
                  <td className="py-3.5 px-4 font-mono text-slate-300">{f.line_count}</td>
                  <td className="py-3.5 px-4 font-mono font-bold text-white">{f.key_count}</td>
                  <td className="py-3.5 px-4 font-mono text-slate-400">
                    {(f.size_bytes / 1024).toFixed(1)} КБ
                  </td>
                  <td className="py-3.5 px-4">
                    <span className="inline-flex items-center gap-1 text-emerald-400 font-semibold">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>Жарамды</span>
                    </span>
                  </td>
                  <td className="py-3.5 px-5 text-right whitespace-nowrap space-x-1.5">
                    <button
                      onClick={() => handlePreview(f.id)}
                      className="btn-secondary px-2.5 py-1.5 text-xs"
                      title="Құрылымын қарау"
                    >
                      <Eye className="w-3.5 h-3.5 text-cyan-400" />
                      <span>Қарау</span>
                    </button>
                    <button
                      onClick={() =>
                        downloadBlob(`/api/files/${f.id}/download`, f.original_filename)
                      }
                      className="btn-secondary px-2.5 py-1.5 text-xs"
                      title="Жүктеп алу"
                    >
                      <Download className="w-3.5 h-3.5 text-emerald-400" />
                    </button>
                    <button
                      onClick={() => handleDelete(f.id)}
                      className="inline-flex items-center justify-center p-1.5 rounded-xl bg-rose-500/15 hover:bg-rose-500/25 text-rose-300 transition"
                      title="Жою"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ARB / CSV Inspector Modal */}
      {preview && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm"
          onClick={() => setPreview(null)}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="saas-card border-white/[0.14] max-w-3xl w-full max-h-[82vh] flex flex-col overflow-hidden"
          >
            <div className="px-6 py-4 border-b border-white/[0.08] flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold font-mono text-white">{preview.filename}</h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Locale: <b className="text-cyan-300">{preview.locale || '—'}</b> • Кілттер:{' '}
                  <b className="text-white">{preview.key_count}</b> • @metadata:{' '}
                  <b className="text-violet-300">{preview.metadata_count}</b>
                </p>
              </div>
              <button
                onClick={() => setPreview(null)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/[0.06]"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="p-5 overflow-y-auto space-y-2 text-xs">
              {preview.sample.map((item, idx) => (
                <div
                  key={idx}
                  className="p-3 rounded-xl bg-[#050811] border border-white/[0.07] flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                >
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="font-mono text-cyan-300">
                      {String(item.key ?? item.ru_term ?? `#${idx + 1}`)}
                    </span>
                    {Boolean(item.has_metadata) && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-violet-500/15 text-violet-300 font-mono">
                        @meta
                      </span>
                    )}
                  </div>
                  <span className="text-slate-200 break-words flex-1 sm:text-right">
                    {String(item.value ?? item.kk_term ?? '')}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
