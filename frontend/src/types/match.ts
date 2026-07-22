export interface SkillMatch {
  skill: string;
  required: boolean;
  matched: boolean;
  category?: string;
}

export interface Recommendation {
  section: string;
  priority: 'high' | 'medium' | 'low';
  message: string;
  suggestion?: string;
}

export interface MatchResult {
  id: string;
  resume_id: string;
  job_title?: string;
  overall_score: number;
  skill_matches: SkillMatch[];
  matched_skills: string[];
  missing_skills: string[];
  recommendations: Recommendation[];
  summary?: string;
  created_at?: string;
}
