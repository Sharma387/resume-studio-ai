export interface ResumeSuggestion {
  id: string;
  resume_id: string;
  suggestion_type: string;
  section: string;
  field_path?: string;
  original_text: string;
  suggested_text: string;
  reason: string;
  confidence: number;
  ai_model?: string;
  source: string;
  status: 'pending' | 'accepted' | 'rejected';
  created_at: string;
}

export interface WriterRequest {
  prompt: string;
  focus_section?: string;
}

export interface WriterResponse {
  success: boolean;
  suggestions: ResumeSuggestion[];
}

export interface QuickActions {
  [key: string]: string;
}
