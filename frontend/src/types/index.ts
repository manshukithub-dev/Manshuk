export type PageId =
  | 'dashboard'
  | 'new-check'
  | 'files'
  | 'issues'
  | 'editor'
  | 'glossary'
  | 'reports'
  | 'history'
  | 'team'
  | 'settings';

export interface ProjectRun {
  id: number;
  name: string;
  is_demo: boolean;
  status: string;
  source_locale: string;
  has_kk: boolean;
  has_uz: boolean;
  has_en: boolean;
  total_keys: number;
  checked_strings: number;
  total_issues: number;
  high_issues: number;
  medium_issues: number;
  low_issues: number;
  fixed_count: number;
  human_reviewed_count: number;
  kk_quality_score: number;
  uz_quality_score: number | null;
  ai_mode_used: string;
  duration_ms: number;
  created_at: string;
}

export interface UploadedFileItem {
  id: number;
  run_id: number | null;
  role: 'ru' | 'kk' | 'uz' | 'en' | 'glossary';
  original_filename: string;
  file_format: string;
  size_bytes: number;
  line_count: number;
  key_count: number;
  is_valid: boolean;
  validation_error: string | null;
  is_demo: boolean;
  created_at: string;
}

export interface QAIssueItem {
  id: number;
  run_id: number;
  entry_id: number;
  lang: 'kk' | 'uz';
  key: string;
  issue_type: string;
  severity: 'high' | 'medium' | 'low';
  source: string;
  target: string;
  evidence: string;
  suggestion: string;
  confidence: number;
  auto_fix_safe: boolean;
  reviewed_by_human: boolean;
  resolution: string;
  resolved_by: string | null;
  updated_at: string;
  en_text?: string | null;
  current_target?: string | null;
  latin_preview?: string | null;
  entry_review_status?: string | null;
}

export interface TranslationEntryItem {
  id: number;
  run_id: number;
  lang: 'kk' | 'uz';
  key: string;
  source_text: string;
  en_text: string | null;
  original_target: string;
  current_target: string;
  latin_preview: string | null;
  is_fixed: boolean;
  reviewed_by_human: boolean;
  reviewer_name: string | null;
  review_status: string;
  issues: QAIssueItem[];
}

export interface GlossaryTerm {
  id: number;
  ru_term: string;
  kk_term: string;
  uz_term: string;
  en_term: string;
  description: string;
  example: string;
  is_slang_or_brand: boolean;
  created_at: string;
}

export interface TeamMember {
  id: number;
  name: string;
  role: string;
  languages: string;
  email: string;
  avatar_initials: string;
  is_active_reviewer: boolean;
  reviewed_count: number;
  created_at: string;
}

export interface AppSettings {
  llm_provider: string;
  has_api_key: boolean;
  masked_api_key: string;
  llm_model: string;
  llm_base_url: string;
  length_overflow_ratio: number;
  button_max_chars: number;
  latin_check_enabled: boolean;
  max_upload_mb: number;
}

export interface DashboardStats {
  has_runs: boolean;
  active_run: ProjectRun | null;
  total_runs_count: number;
  total_checked_strings: number;
  total_issues: number;
  high_severity_issues: number;
  medium_severity_issues: number;
  low_severity_issues: number;
  fixed_strings: number;
  human_reviewed_strings: number;
  unreviewed_strings: number;
  kk_quality_score: number;
  uz_quality_score: number | null;
  issues_by_type: { issue_type: string; label: string; count: number }[];
  severity_breakdown: { severity: string; count: number; color: string }[];
  runs_trend: {
    id: number;
    name: string;
    kk_score: number;
    uz_score: number;
    issues: number;
    reviewed: number;
    is_demo: boolean;
  }[];
  language_comparison: {
    language: string;
    score: number;
    issues: number;
    reviewed: number;
    total: number;
  }[];
  recent_runs: ProjectRun[];
}

export interface ReportSummary {
  run_id: number;
  project_name: string;
  is_demo: boolean;
  has_kk: boolean;
  has_uz: boolean;
  total_strings: number;
  total_keys: number;
  total_issues: number;
  severity_stats: { high: number; medium: number; low: number };
  issue_types: { issue_type: string; label: string; count: number }[];
  fixed_strings: number;
  human_reviewed_strings: number;
  unreviewed_strings: number;
  kk_quality_score: number;
  uz_quality_score: number | null;
  recommendations: string[];
  sample_json: Record<string, unknown>[];
}

export const ISSUE_TYPE_LABELS: Record<string, string> = {
  untranslated: 'Аударылмаған жол',
  same_as_source: 'Түпнұсқамен бірдей',
  placeholder_mismatch: 'Плейсхолдер сәйкессіздігі',
  plural_mismatch: 'ICU көпше түр қатесі',
  glossary_violation: 'Глоссарий бұзушылығы',
  length_overflow: 'Мәтін тым ұзын',
  machine_translation_suspect: 'Машиналық аударма күдігі',
  inconsistent_term: 'Біркелкі емес термин',
  suffix_harmony: 'Қосымша үндестігі',
  orthography: 'Емле қатесі',
  wrong_language: 'Қате тіл',
  other_localization_issue: 'Басқа локализация қатесі',
};
