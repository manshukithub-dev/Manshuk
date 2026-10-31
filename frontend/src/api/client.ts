import type {
  AppSettings,
  DashboardStats,
  GlossaryTerm,
  ProjectRun,
  QAIssueItem,
  ReportSummary,
  TeamMember,
  TranslationEntryItem,
  UploadedFileItem,
} from '../types';

const rawApiBase = (import.meta.env.VITE_API_BASE_URL || '').trim().replace(/\/+$/, '');
export const API_BASE_URL = rawApiBase.endsWith('/api') ? rawApiBase.slice(0, -4) : rawApiBase;

export function buildApiUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) {
    return path;
  }
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${API_BASE_URL}${normalizedPath}`;
}

export function getWorkspaceId(): string {
  const key = 'qazaq_locqa_workspace_token';
  let token = localStorage.getItem(key) || sessionStorage.getItem(key);
  if (!token) {
    token = 'ws-' + Math.random().toString(36).slice(2, 10) + Date.now().toString(36).slice(-4);
  }
  localStorage.setItem(key, token);
  return token;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers || {});
  headers.set('X-Workspace-Id', getWorkspaceId());
  headers.set('bypass-tunnel-reminder', 'true');
  if (!(init?.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const resp = await fetch(buildApiUrl(path), { ...init, headers });
  if (!resp.ok) {
    let msg = `Сервер қатесі (${resp.status})`;
    try {
      const errJson = await resp.json();
      if (errJson?.detail) {
        msg = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // ignore json parse failure
    }
    throw new Error(msg);
  }
  return resp.json() as Promise<T>;
}

export async function downloadBlob(path: string, fallbackFilename: string): Promise<void> {
  const headers = new Headers();
  headers.set('X-Workspace-Id', getWorkspaceId());
  headers.set('bypass-tunnel-reminder', 'true');
  const resp = await fetch(buildApiUrl(path), { headers });
  if (!resp.ok) {
    let msg = `Экспорт қатесі (${resp.status})`;
    try {
      const err = await resp.json();
      if (err?.detail) msg = err.detail;
    } catch {
      // ignore
    }
    throw new Error(msg);
  }

  const disposition = resp.headers.get('Content-Disposition') || '';
  const match = disposition.match(/filename="?([^"]+)"?/i);
  const filename = match?.[1] || fallbackFilename;

  const blob = await resp.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export const api = {
  getDashboard: (runId?: number | null) =>
    request<DashboardStats>(`/api/dashboard${runId ? `?run_id=${runId}` : ''}`),

  listRuns: () => request<ProjectRun[]>('/api/checks'),
  runDemoCheck: () => request<ProjectRun>('/api/checks/demo', { method: 'POST' }),
  createRun: (payload: {
    name: string;
    ru_file_id: number;
    kk_file_id?: number | null;
    uz_file_id?: number | null;
    en_file_id?: number | null;
    glossary_file_id?: number | null;
    use_llm?: boolean;
  }) => request<ProjectRun>('/api/checks/run', { method: 'POST', body: JSON.stringify(payload) }),
  deleteRun: (runId: number) => request<{ ok: boolean }>(`/api/checks/${runId}`, { method: 'DELETE' }),

  uploadFile: (role: string, file: File) => {
    const fd = new FormData();
    fd.append('role', role);
    fd.append('file', file);
    return request<UploadedFileItem>('/api/files/upload', { method: 'POST', body: fd });
  },
  listFiles: () => request<UploadedFileItem[]>('/api/files'),
  previewFile: (fileId: number) =>
    request<{
      id: number;
      filename: string;
      role: string;
      format: string;
      locale: string | null;
      key_count: number;
      metadata_count: number;
      line_count: number;
      size_bytes: number;
      sample: Record<string, unknown>[];
    }>(`/api/files/${fileId}/preview`),
  deleteFile: (fileId: number) => request<{ ok: boolean }>(`/api/files/${fileId}`, { method: 'DELETE' }),

  listIssues: (params: {
    run_id?: number | null;
    severity?: string;
    lang?: string;
    issue_type?: string;
    reviewed?: string;
    search?: string;
    page?: number;
    page_size?: number;
  }) => {
    const q = new URLSearchParams();
    if (params.run_id) q.set('run_id', String(params.run_id));
    if (params.severity && params.severity !== 'all') q.set('severity', params.severity);
    if (params.lang && params.lang !== 'all') q.set('lang', params.lang);
    if (params.issue_type && params.issue_type !== 'all') q.set('issue_type', params.issue_type);
    if (params.reviewed && params.reviewed !== 'all') q.set('reviewed', params.reviewed);
    if (params.search) q.set('search', params.search);
    q.set('page', String(params.page || 1));
    q.set('page_size', String(params.page_size || 50));
    return request<{
      run_id: number | null;
      run_name?: string;
      is_demo?: boolean;
      total: number;
      page: number;
      page_size: number;
      items: QAIssueItem[];
    }>(`/api/issues?${q.toString()}`);
  },

  applyIssueAction: (
    issueId: number,
    payload: { action: string; new_target?: string; reviewer_name?: string }
  ) =>
    request<QAIssueItem>(`/api/issues/${issueId}/action`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  batchAutoFix: (runId: number, lang?: string) =>
    request<{ applied_count: number; reviewed_by_human: boolean }>(
      `/api/issues/batch-auto-fix?run_id=${runId}${lang && lang !== 'all' ? `&lang=${lang}` : ''}`,
      { method: 'POST' }
    ),

  listEntries: (params: {
    run_id?: number | null;
    lang?: string;
    filter_mode?: string;
    search?: string;
    page?: number;
    page_size?: number;
  }) => {
    const q = new URLSearchParams();
    if (params.run_id) q.set('run_id', String(params.run_id));
    q.set('lang', params.lang || 'kk');
    q.set('filter_mode', params.filter_mode || 'all');
    if (params.search) q.set('search', params.search);
    q.set('page', String(params.page || 1));
    q.set('page_size', String(params.page_size || 50));
    return request<{
      run_id: number | null;
      run_name?: string;
      is_demo?: boolean;
      total: number;
      items: TranslationEntryItem[];
    }>(`/api/entries?${q.toString()}`);
  },

  updateEntry: (
    entryId: number,
    payload: { current_target: string; reviewed_by_human: boolean; reviewer_name?: string }
  ) =>
    request<{
      id: number;
      key: string;
      current_target: string;
      latin_preview: string | null;
      is_fixed: boolean;
      reviewed_by_human: boolean;
      review_status: string;
    }>(`/api/entries/${entryId}`, { method: 'PUT', body: JSON.stringify(payload) }),

  listGlossary: (search?: string) =>
    request<GlossaryTerm[]>(`/api/glossary${search ? `?search=${encodeURIComponent(search)}` : ''}`),
  createGlossaryTerm: (payload: Omit<GlossaryTerm, 'id' | 'created_at'>) =>
    request<GlossaryTerm>('/api/glossary', { method: 'POST', body: JSON.stringify(payload) }),
  updateGlossaryTerm: (id: number, payload: Omit<GlossaryTerm, 'id' | 'created_at'>) =>
    request<GlossaryTerm>(`/api/glossary/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteGlossaryTerm: (id: number) =>
    request<{ ok: boolean }>(`/api/glossary/${id}`, { method: 'DELETE' }),
  importGlossaryCsv: (file: File) => {
    const fd = new FormData();
    fd.append('file', file);
    return request<{ added: number; updated: number; total_imported: number }>(
      '/api/glossary/import-csv',
      { method: 'POST', body: fd }
    );
  },

  getReportSummary: (runId: number, lang?: string) =>
    request<ReportSummary>(
      `/api/reports/${runId}/summary${lang && lang !== 'all' ? `?lang=${lang}` : ''}`
    ),

  getReportHtmlPreview: async (runId: number, lang?: string): Promise<string> => {
    const headers = new Headers();
    headers.set('X-Workspace-Id', getWorkspaceId());
    headers.set('bypass-tunnel-reminder', 'true');
    const langParam = lang && lang !== 'all' ? `&lang=${encodeURIComponent(lang)}` : '';
    const resp = await fetch(buildApiUrl(`/api/reports/${runId}/html?download=false${langParam}`), { headers });
    if (!resp.ok) throw new Error('HTML есебін жүктеу мүмкін болмады');
    return resp.text();
  },

  listTeam: () => request<TeamMember[]>('/api/team'),
  createTeamMember: (payload: {
    name: string;
    role: string;
    languages: string;
    email: string;
    is_active_reviewer: boolean;
  }) => request<TeamMember>('/api/team', { method: 'POST', body: JSON.stringify(payload) }),
  activateReviewer: (id: number) =>
    request<TeamMember>(`/api/team/${id}/activate`, { method: 'POST' }),
  deleteTeamMember: (id: number) =>
    request<{ ok: boolean }>(`/api/team/${id}`, { method: 'DELETE' }),

  getSettings: () => request<AppSettings>('/api/settings'),
  updateSettings: (payload: {
    llm_provider: string;
    llm_api_key?: string;
    clear_api_key?: boolean;
    llm_model: string;
    llm_base_url: string;
    length_overflow_ratio: number;
    button_max_chars: number;
    latin_check_enabled: boolean;
  }) => request<AppSettings>('/api/settings', { method: 'PUT', body: JSON.stringify(payload) }),
  testLlm: () =>
    request<{ ok: boolean; message: string; mode: string }>('/api/settings/test-llm', {
      method: 'POST',
    }),

  transliterate: (text: string, maxLength?: number) =>
    request<{
      source_cyrillic: string;
      latin_text: string;
      cyrillic_length: number;
      latin_length: number;
      length_delta: number;
      overflow: boolean;
    }>('/api/transliterate', {
      method: 'POST',
      body: JSON.stringify({ text, max_length: maxLength ?? 24 }),
    }),
};
