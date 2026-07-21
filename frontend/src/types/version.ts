import type { Resume } from './resume';

export interface ResumeVersion {
  id: string;
  resume_id: string;
  label?: string;
  resume: Resume;
  created_at: string;
}
