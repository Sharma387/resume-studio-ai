export interface DashboardSummary {
  resumes: { total: number; with_summary: number };
  applications: { total: number; active: number; interviewing: number; by_status: Record<string, number> };
  ats: { total_matches: number; average_score: number };
  interviews: { total: number };
  cover_letters: { total: number };
  ai_suggestions: { total: number; pending: number };
}

export interface Workspace {
  user?: { id: string; email: string; full_name: string } | null;
  active_resume?: Record<string, unknown> | null;
  dashboard: DashboardSummary;
}
