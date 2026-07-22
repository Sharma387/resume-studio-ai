export interface CoverLetterRequest {
  job_description: string;
  company_name?: string;
  hiring_manager?: string;
  role_title?: string;
  tone: 'professional' | 'enthusiastic' | 'formal' | 'concise';
}

export interface CoverLetter {
  id: string;
  resume_id: string;
  application_id?: string;
  company_name?: string;
  hiring_manager?: string;
  role_title?: string;
  tone: string;
  content: string;
  subject?: string;
  ai_model?: string;
  job_description_hash?: string;
  created_at: string;
  updated_at: string;
}

export interface CoverLetterResponse {
  success: boolean;
  data: CoverLetter;
}

export interface CoverLetterListResponse {
  success: boolean;
  data: CoverLetter[];
}
