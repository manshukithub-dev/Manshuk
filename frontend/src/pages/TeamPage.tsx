import React, { useState } from 'react';
import { UserPlus, CheckCircle2, Trash2, Award } from 'lucide-react';
import type { TeamMember } from '../types';
import { api } from '../api/client';

interface TeamPageProps {
  members: TeamMember[];
  onRefreshTeam: () => Promise<void>;
}

export const TeamPage: React.FC<TeamPageProps> = ({ members, onRefreshTeam }) => {
  const [name, setName] = useState('');
  const [role, setRole] = useState('Қазақ тілінің локализация редакторы');
  const [languages, setLanguages] = useState('KK, RU, EN');
  const [email, setEmail] = useState('');

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    await api.createTeamMember({
      name: name.trim(),
      role: role.trim(),
      languages: languages.trim(),
      email: email.trim(),
      is_active_reviewer: false,
    });
    setName('');
    setEmail('');
    await onRefreshTeam();
  };

  const handleActivate = async (id: number) => {
    await api.activateReviewer(id);
    await onRefreshTeam();
  };

  const handleDelete = async (id: number) => {
    await api.deleteTeamMember(id);
    await onRefreshTeam();
  };

  return (
    <div className="space-y-6">
      <div className="saas-card p-5">
        <h2 className="text-base font-extrabold text-white">Локализация QA командасы</h2>
        <p className="text-xs text-slate-400 mt-1">
          Белсенді ретінде таңдалған маманның аты-жөні тексерілген ARB файлдарының{' '}
          <code className="font-mono text-cyan-300">@key.x-reviewed-by</code> метадерегіне жазылады.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {members.map((m) => (
          <div
            key={m.id}
            className={`saas-card-hover p-5 flex items-start justify-between gap-4 ${
              m.is_active_reviewer ? '!border-emerald-400/50 shadow-glow' : ''
            }`}
          >
            <div className="flex items-start gap-3.5">
              <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-cyan-500 via-blue-600 to-violet-600 flex items-center justify-center font-extrabold text-white text-sm shrink-0 shadow-md">
                {m.avatar_initials}
              </div>
              <div className="space-y-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-bold text-white">{m.name}</span>
                  {m.is_active_reviewer && (
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/35">
                      Белсенді тексеруші
                    </span>
                  )}
                </div>
                <div className="text-xs text-cyan-300 font-medium">{m.role}</div>
                <div className="text-[11px] text-slate-400">
                  Тілдері: {m.languages} {m.email ? `• ${m.email}` : ''}
                </div>
                <div className="inline-flex items-center gap-1.5 text-xs text-emerald-400 pt-1 font-semibold">
                  <Award className="w-3.5 h-3.5" />
                  <span>SQLite базасында растаған жолдары: {m.reviewed_count}</span>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-1.5">
              {!m.is_active_reviewer && (
                <button
                  onClick={() => handleActivate(m.id)}
                  className="px-3 py-1.5 rounded-xl bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/35 text-emerald-300 text-xs font-bold flex items-center gap-1 transition"
                >
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Таңдау</span>
                </button>
              )}
              {members.length > 1 && (
                <button
                  onClick={() => handleDelete(m.id)}
                  className="p-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 transition"
                  title="Жою"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      <form onSubmit={handleAdd} className="saas-card p-6 space-y-4">
        <div className="flex items-center gap-2 text-sm font-bold text-white">
          <UserPlus className="w-4 h-4 text-cyan-400" />
          <span>Жаңа маман қосу</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
          <input
            required
            placeholder="Аты-жөні *"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="saas-input px-3.5 py-2.5"
          />
          <input
            required
            placeholder="Лауазымы *"
            value={role}
            onChange={(e) => setRole(e.target.value)}
            className="saas-input px-3.5 py-2.5"
          />
          <input
            placeholder="Тілдері (KK, UZ, RU, EN)"
            value={languages}
            onChange={(e) => setLanguages(e.target.value)}
            className="saas-input px-3.5 py-2.5"
          />
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="saas-input px-3.5 py-2.5"
          />
        </div>

        <div className="flex justify-end">
          <button type="submit" className="btn-primary px-5 py-2.5 text-xs font-bold">
            Командаға қосу
          </button>
        </div>
      </form>
    </div>
  );
};
