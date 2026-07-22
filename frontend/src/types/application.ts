export interface ApplicationNote {
  id: string;
  content: string;
  created_at: string;
}

export interface TimelineEvent {
  id: string;
  application_id: string;
  event_type: string;
  title: string;
  description: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface Application {
  id: string;
  company: string;
  role_title: string;
  location?: string;
  url?: string;
  status: 'draft' | 'applied' | 'screening' | 'interviewing' | 'offered' | 'rejected' | 'withdrawn' | 'accepted' | 'archived';
  priority: 'low' | 'medium' | 'high';
  salary_range?: string;
  notes: ApplicationNote[];
  tags: string[];
  resume_id?: string;
  cover_letter_ids: string[];
  match_ids: string[];
  version_ids: string[];
  writer_suggestion_ids: string[];
  last_activity?: string;
  next_action?: string;
  next_action_date?: string;
  created_at: string;
  updated_at: string;
}

export interface ApplicationView {
  application: Application;
  resume_name?: string;
  cover_letter_count: number;
  match_count: number;
  version_count: number;
  recent_timeline: TimelineEvent[];
}

export interface DashboardSummary {
  total: number;
  by_status: Record<string, number>;
  by_priority: Record<string, number>;
  active: number;
  interviews: number;
  offers: number;
  recent_applications: Application[];
}
