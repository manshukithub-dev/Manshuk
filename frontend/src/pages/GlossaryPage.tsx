import React, { useEffect, useRef, useState } from 'react';
import {
  Plus,
  Search,
  Upload,
  Download,
  Pencil,
  Trash2,
  X,
  Shield,
  BookOpen,
} from 'lucide-react';
import type { GlossaryTerm } from '../types';
import { api, downloadBlob } from '../api/client';

const EMPTY_FORM = {
  ru_term: '',
  kk_term: '',
  uz_term: '',
  en_term: '',
  description: '',
  example: '',
  is_slang_or_brand: false,
};

export const GlossaryPage: React.FC = () => {
  const [terms, setTerms] = useState<GlossaryTerm[]>([]);
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<'all' | 'slang' | 'standard'>('all');
  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [message, setMessage] = useState<string | null>(null);
  const csvInputRef = useRef<HTMLInputElement | null>(null);

  const loadGlossary = async (q?: string) => {
    const data = await api.listGlossary(q ?? search);
    setTerms(data);
  };

  useEffect(() => {
    loadGlossary();
  }, [search]);

  const openCreate = () => {
    setEditingId(null);
    setForm(EMPTY_FORM);
    setModalOpen(true);
  };

  const openEdit = (t: GlossaryTerm) => {
    setEditingId(t.id);
    setForm({
      ru_term: t.ru_term,
      kk_term: t.kk_term,
      uz_term: t.uz_term,
      en_term: t.en_term,
      description: t.description,
      example: t.example,
      is_slang_or_brand: t.is_slang_or_brand,
    });
    setModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.ru_term.trim() || !form.kk_term.trim()) return;
    if (editingId) {
      await api.updateGlossaryTerm(editingId, form);
      setMessage('Глоссарий термині жаңартылды!');
    } else {
      await api.createGlossaryTerm(form);
      setMessage('Жаңа термин глоссарийге қосылды!');
    }
    setModalOpen(false);
    await loadGlossary();
    setTimeout(() => setMessage(null), 2500);
  };

  const handleDelete = async (id: number) => {
    await api.deleteGlossaryTerm(id);
    await loadGlossary();
  };

  const handleImportCsv = async (file: File) => {
    const res = await api.importGlossaryCsv(file);
    setMessage(
      `CSV импортталды: жаңадан ${res.added} термин қосылды, ${res.updated} термин жаңартылды.`
    );
    await loadGlossary();
    setTimeout(() => setMessage(null), 3500);
  };

  const visibleTerms = terms.filter((t) => {
    if (categoryFilter === 'slang') return t.is_slang_or_brand;
    if (categoryFilter === 'standard') return !t.is_slang_or_brand;
    return true;
  });

  const slangCount = terms.filter((t) => t.is_slang_or_brand).length;

  return (
    <div className="space-y-6">
      {/* KPI Header */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="saas-card p-4 flex items-center justify-between">
          <div>
            <div className="text-xs text-slate-400">Барлық терминдер</div>
            <div className="text-2xl font-black font-mono text-white mt-1">{terms.length}</div>
          </div>
          <div className="p-2.5 rounded-xl bg-cyan-500/10 border border-cyan-500/25 text-cyan-400">
            <BookOpen className="w-5 h-5" />
          </div>
        </div>
        <div className="saas-card p-4 flex items-center justify-between">
          <div>
            <div className="text-xs text-slate-400">Қорғалған сленг / Бренд</div>
            <div className="text-2xl font-black font-mono text-violet-300 mt-1">{slangCount}</div>
          </div>
          <div className="p-2.5 rounded-xl bg-violet-500/10 border border-violet-500/25 text-violet-400">
            <Shield className="w-5 h-5" />
          </div>
        </div>
        <div className="saas-card p-4 flex items-center justify-between">
          <div>
            <div className="text-xs text-slate-400">Тілдік бағандар</div>
            <div className="text-lg font-extrabold text-emerald-400 mt-1">RU • KK • UZ • EN</div>
          </div>
          <span className="text-[11px] font-mono px-2.5 py-1 rounded-lg bg-emerald-500/10 text-emerald-300 border border-emerald-500/25">
            Active
          </span>
        </div>
      </div>

      {/* Controls Bar */}
      <div className="saas-card p-5 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-2 flex-1">
          <div className="relative flex-1 min-w-[220px] max-w-md">
            <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Терминді орысша, қазақша, өзбекше, ағылшынша іздеу..."
              className="w-full saas-input pl-10 pr-4 py-2 text-xs"
            />
          </div>

          {(['all', 'slang', 'standard'] as const).map((cat) => (
            <button
              key={cat}
              onClick={() => setCategoryFilter(cat)}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold border transition ${
                categoryFilter === cat
                  ? 'bg-cyan-500/20 text-cyan-300 border-cyan-400/40'
                  : 'bg-white/[0.03] text-slate-400 border-white/[0.07]'
              }`}
            >
              {cat === 'all' ? 'Барлығы' : cat === 'slang' ? 'Сленг / Бренд' : 'Аударылатын'}
            </button>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <input
            ref={csvInputRef}
            type="file"
            accept=".csv"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) handleImportCsv(f);
              e.target.value = '';
            }}
          />
          <button
            onClick={() => csvInputRef.current?.click()}
            className="btn-secondary px-3.5 py-2 text-xs"
          >
            <Upload className="w-3.5 h-3.5 text-cyan-400" />
            <span>CSV импорттау</span>
          </button>

          <button
            onClick={() => downloadBlob('/api/glossary/export-csv', 'qazaq_locqa_glossary.csv')}
            className="btn-secondary px-3.5 py-2 text-xs"
          >
            <Download className="w-3.5 h-3.5 text-violet-400" />
            <span>CSV экспорттау</span>
          </button>

          <button onClick={openCreate} className="btn-primary px-4 py-2 text-xs font-bold">
            <Plus className="w-4 h-4" />
            <span>Термин қосу</span>
          </button>
        </div>
      </div>

      {message && (
        <div className="p-3.5 rounded-xl bg-emerald-500/15 border border-emerald-500/40 text-xs text-emerald-200 font-semibold">
          {message}
        </div>
      )}

      {/* Glossary Table */}
      <div className="saas-card overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-white/[0.07] bg-white/[0.02] text-slate-400">
              <th className="py-3.5 px-4">Орысша термин</th>
              <th className="py-3.5 px-4">Қазақша термин</th>
              <th className="py-3.5 px-4">Өзбекше термин</th>
              <th className="py-3.5 px-4">Ағылшынша термин</th>
              <th className="py-3.5 px-4">Түсіндірме</th>
              <th className="py-3.5 px-4">Қолданылу мысалы</th>
              <th className="py-3.5 px-4 text-right">Әрекеттер</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.05]">
            {visibleTerms.map((t) => (
              <tr key={t.id} className="hover:bg-white/[0.03] transition">
                <td className="py-3.5 px-4 font-bold text-white">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span>{t.ru_term}</span>
                    {t.is_slang_or_brand && (
                      <span
                        title="Ойын сленгі немесе қорғалған бренд"
                        className="inline-flex items-center px-1.5 py-0.5 rounded bg-violet-500/20 text-violet-300 border border-violet-500/30 text-[10px]"
                      >
                        <Shield className="w-2.5 h-2.5 mr-0.5" />
                        Сленг/Бренд
                      </span>
                    )}
                  </div>
                </td>
                <td className="py-3.5 px-4 font-bold text-cyan-300">{t.kk_term}</td>
                <td className="py-3.5 px-4 text-sky-300">{t.uz_term || '—'}</td>
                <td className="py-3.5 px-4 font-mono text-slate-300">{t.en_term || '—'}</td>
                <td className="py-3.5 px-4 text-slate-300 max-w-xs leading-relaxed">
                  {t.description}
                </td>
                <td className="py-3.5 px-4 text-emerald-300/90 max-w-xs italic">{t.example}</td>
                <td className="py-3.5 px-4 text-right whitespace-nowrap space-x-1.5">
                  <button
                    onClick={() => openEdit(t)}
                    className="p-1.5 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] text-slate-200 transition"
                    title="Өзгерту"
                  >
                    <Pencil className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => handleDelete(t.id)}
                    className="p-1.5 rounded-lg bg-rose-500/15 hover:bg-rose-500/25 text-rose-300 transition"
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

      {/* Add / Edit Term Modal */}
      {modalOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm"
          onClick={() => setModalOpen(false)}
        >
          <form
            onClick={(e) => e.stopPropagation()}
            onSubmit={handleSubmit}
            className="saas-card border-white/[0.14] max-w-lg w-full p-6 space-y-4"
          >
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-white">
                {editingId ? 'Терминді өзгерту' : 'Жаңа ойын терминін қосу'}
              </h3>
              <button
                type="button"
                onClick={() => setModalOpen(false)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/[0.06]"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div>
                <label className="text-slate-400 block mb-1">Орысша термин *</label>
                <input
                  required
                  value={form.ru_term}
                  onChange={(e) => setForm({ ...form, ru_term: e.target.value })}
                  className="w-full saas-input px-3 py-2"
                />
              </div>
              <div>
                <label className="text-slate-400 block mb-1">Қазақша термин *</label>
                <input
                  required
                  value={form.kk_term}
                  onChange={(e) => setForm({ ...form, kk_term: e.target.value })}
                  className="w-full saas-input px-3 py-2"
                />
              </div>
              <div>
                <label className="text-slate-400 block mb-1">Өзбекше термин</label>
                <input
                  value={form.uz_term}
                  onChange={(e) => setForm({ ...form, uz_term: e.target.value })}
                  className="w-full saas-input px-3 py-2"
                />
              </div>
              <div>
                <label className="text-slate-400 block mb-1">Ағылшынша термин</label>
                <input
                  value={form.en_term}
                  onChange={(e) => setForm({ ...form, en_term: e.target.value })}
                  className="w-full saas-input px-3 py-2"
                />
              </div>
            </div>

            <div className="text-xs">
              <label className="text-slate-400 block mb-1">Түсіндірме</label>
              <textarea
                rows={2}
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                className="w-full saas-input p-3"
              />
            </div>

            <div className="text-xs">
              <label className="text-slate-400 block mb-1">Қолданылу мысалы</label>
              <input
                value={form.example}
                onChange={(e) => setForm({ ...form, example: e.target.value })}
                className="w-full saas-input px-3 py-2"
              />
            </div>

            <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
              <input
                type="checkbox"
                checked={form.is_slang_or_brand}
                onChange={(e) => setForm({ ...form, is_slang_or_brand: e.target.checked })}
                className="rounded border-slate-700"
              />
              <span>Ойыншылар сленгі немесе бренд атауы (жалған қате ретінде белгіленбейді)</span>
            </label>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setModalOpen(false)}
                className="btn-secondary px-4 py-2 text-xs"
              >
                Болдырмау
              </button>
              <button type="submit" className="btn-primary px-5 py-2 text-xs font-bold">
                Сақтау
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};
