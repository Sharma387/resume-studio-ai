export interface Education {
  institution: string;
  degree: string;
  field?: string;
  start_date?: string;
  end_date?: string;
  gpa?: number;
  achievements: string[];
}

export interface Experience {
  company: string;
  title: string;
  location?: string;
  start_date?: string;
  end_date?: string;
  current: boolean;
  description: string[];
}

export interface Project {
  name: string;
  description?: string;
  url?: string;
  technologies: string[];
}

export interface Skill {
  category: string;
  skills: string[];
}

export interface Certification {
  name: string;
  issuer?: string;
  date?: string;
  url?: string;
}

export interface Resume {
  full_name: string;
  email: string;
  phone?: string;
  location?: string;
  linkedin?: string;
  github?: string;
  website?: string;
  summary?: string;
  education: Education[];
  experience: Experience[];
  projects: Project[];
  skills: Skill[];
  certifications: Certification[];
}
