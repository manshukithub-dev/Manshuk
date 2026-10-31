import React, { useEffect, useState } from 'react';
import { KeyRound, Save, Wifi, Terminal, ShieldCheck, Trash2 } from 'lucide-react';
import type { AppSettings } from '../types';
import { api } from '../api/client';

interface SettingsPageProps {
  settings: AppSettings | null;
  onSettingsUpdated: (s: AppSettings) => void;
}

export const SettingsPage: React.FC<SettingsPageProps> = ({ settings, onSettingsUpdated }) => {
  const [provider, setProvider] = useState('gemini');
  const [apiKeyInput, setApiKeyInput] = useState('');
  const [model, setModel] = useState('gemini-2.5-flash');
  const [baseUrl, setBaseUrl] = useState('');
  const [overflowRatio, setOverflowRatio] = useState(1.45);
  const [buttonMaxChars, setButtonMaxChars] = useState(24);
  const [latinCheck, setLatinCheck] = useState(true);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);
  const [testing, setTesting] = useState(false);

  useEffect(() => {
    if (settings) {
      setProvider(settings.llm_provider);
      setModel(settings.llm_model);
      setBaseUrl(settings.llm_base_url);
      setOverflowRatio(settings.length_overflow_ratio);
      setButtonMaxChars(settings.button_max_chars);
      setLatinCheck(settings.latin_check_enabled);
    }
  }, [settings]);

  const handleSave = async (clearKey = false) => {
    const updated = await api.updateSettings({
      llm_provider: provider,
      llm_api_key: clearKey ? undefined : apiKeyInput || undefined,
      clear_api_key: clearKey,
      llm_model: model,
      llm_base_url: baseUrl,
      length_overflow_ratio: overflowRatio,
      button_max_chars: buttonMaxChars,
      latin_check_enabled: latinCheck,
    });
    setApiKeyInput('');
    onSettingsUpdated(updated);
    setStatusMsg(
      clearKey
        ? 'API кілті өшірілді. Жүйе ережелерге негізделген тексеру режиміне ауысты.'
        : 'Баптаулар серверлік базаға қауіпсіз сақталды!'
    );
  };

  const handleTestConnection = async () => {
    setTesting(true);
    try {
      const res = await api.testLlm();
      setStatusMsg(res.message);
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="saas-card p-6 space-y-5">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-base font-extrabold text-white">
              <KeyRound className="w-5 h-5 text-violet-400" />
              <span>AI / LLM интеграциясының баптаулары</span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed max-w-2xl">
              API кілті браузерде (Frontend) ешқашан сақталмайды — тек Backend SQLite базасында
              қорғалып сақталады. Кілт болмаған жағдайда 12 санаттық ережелік лингвистикалық
              қозғалтқыш толық жұмыс істейді.
            </p>
          </div>
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs font-semibold">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Макс. жүктеу: {settings?.max_upload_mb || 25} МБ</span>
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div>
            <label className="text-slate-400 block mb-1.5 font-semibold">AI Провайдері</label>
            <select
              value={provider}
              onChange={(e) => {
                setProvider(e.target.value);
                if (e.target.value === 'gemini') setModel('gemini-2.5-flash');
                if (e.target.value === 'openai') setModel('gpt-4o-mini');
              }}
              className="w-full saas-input px-3.5 py-2.5"
            >
              <option value="gemini" className="bg-[#0A0F1E]">Google Gemini API</option>
              <option value="openai" className="bg-[#0A0F1E]">OpenAI / OpenAI-үйлесімді API</option>
            </select>
          </div>

          <div>
            <label className="text-slate-400 block mb-1.5 font-semibold">Модель атауы</label>
            <input
              value={model}
              onChange={(e) => setModel(e.target.value)}
              placeholder="gemini-2.5-flash немесе gpt-4o-mini"
              className="w-full saas-input px-3.5 py-2.5 font-mono"
            />
          </div>

          <div className="md:col-span-2">
            <label className="text-slate-400 block mb-1.5 font-semibold">
              API Кілті{' '}
              {settings?.has_api_key && (
                <span className="font-mono text-emerald-400 ml-2">
                  (Сақталған: {settings.masked_api_key})
                </span>
              )}
            </label>
            <input
              type="password"
              value={apiKeyInput}
              onChange={(e) => setApiKeyInput(e.target.value)}
              placeholder={
                settings?.has_api_key
                  ? 'Жаңарту үшін жаңа API кілтін енгізіңіз...'
                  : 'AI функцияларын қосу үшін API кілтін енгізіңіз (міндетті емес)...'
              }
              className="w-full saas-input px-3.5 py-2.5 font-mono"
            />
          </div>

          {provider !== 'gemini' && (
            <div className="md:col-span-2">
              <label className="text-slate-400 block mb-1.5 font-semibold">
                Арнайы Base URL (міндетті емес)
              </label>
              <input
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                placeholder="https://api.openai.com/v1"
                className="w-full saas-input px-3.5 py-2.5 font-mono"
              />
            </div>
          )}
        </div>

        <div className="pt-4 border-t border-white/[0.07] grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
          <div>
            <label className="text-slate-400 block mb-1.5 font-semibold">
              Ұзындық коэффициенті (Overflow ratio)
            </label>
            <input
              type="number"
              step="0.05"
              min="1.1"
              max="3.0"
              value={overflowRatio}
              onChange={(e) => setOverflowRatio(Number(e.target.value))}
              className="w-full saas-input px-3.5 py-2 font-mono"
            />
          </div>
          <div>
            <label className="text-slate-400 block mb-1.5 font-semibold">
              UI Батырма макс. таңбасы
            </label>
            <input
              type="number"
              min="10"
              max="80"
              value={buttonMaxChars}
              onChange={(e) => setButtonMaxChars(Number(e.target.value))}
              className="w-full saas-input px-3.5 py-2 font-mono"
            />
          </div>
          <div className="flex items-end pb-2">
            <label className="flex items-center gap-2 text-slate-200 cursor-pointer">
              <input
                type="checkbox"
                checked={latinCheck}
                onChange={(e) => setLatinCheck(e.target.checked)}
              />
              <span>Қазақ латын ұзындығын қоса тексеру</span>
            </label>
          </div>
        </div>

        {statusMsg && (
          <div className="p-3.5 rounded-xl bg-cyan-500/15 border border-cyan-500/35 text-xs text-cyan-200 font-medium">
            {statusMsg}
          </div>
        )}

        <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={testing}
              onClick={handleTestConnection}
              className="btn-secondary px-4 py-2 text-xs"
            >
              <Wifi className="w-3.5 h-3.5 text-cyan-400" />
              <span>{testing ? 'Тексерілуде...' : 'Байланысты тексеру'}</span>
            </button>
            {settings?.has_api_key && (
              <button
                type="button"
                onClick={() => handleSave(true)}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-rose-500/15 hover:bg-rose-500/25 text-xs font-semibold text-rose-300 transition"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Кілтті өшіру</span>
              </button>
            )}
          </div>

          <button
            type="button"
            onClick={() => handleSave(false)}
            className="btn-primary px-6 py-2.5 text-xs font-bold"
          >
            <Save className="w-4 h-4" />
            <span>Баптауларды сақтау</span>
          </button>
        </div>
      </div>

      <div className="saas-card p-6 space-y-3">
        <div className="flex items-center gap-2 text-sm font-bold text-cyan-300">
          <Terminal className="w-4 h-4" />
          <span>CLI және CI/CD (GitHub Actions) қолдану пәрмені</span>
        </div>
        <pre className="p-4 rounded-xl bg-[#050811] border border-white/[0.07] font-mono text-xs text-slate-200 overflow-x-auto">
          {`locqa check --source intl_ru.arb --target intl_kk.arb --glossary glossary.csv --out report.json --html report.html --fixed-arb intl_kk_fixed.arb`}
        </pre>
      </div>
    </div>
  );
};
