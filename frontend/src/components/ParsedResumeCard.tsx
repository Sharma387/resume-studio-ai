import { useState } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  Chip,
  IconButton,
  Collapse,
  Divider,
} from '@mui/material';
import ExpandMore from '@mui/icons-material/ExpandMore';
import ExpandLess from '@mui/icons-material/ExpandLess';
import BusinessCenterOutlined from '@mui/icons-material/BusinessCenterOutlined';
import SchoolOutlined from '@mui/icons-material/SchoolOutlined';
import CodeOutlined from '@mui/icons-material/CodeOutlined';
import FolderOutlined from '@mui/icons-material/FolderOutlined';
import VerifiedOutlined from '@mui/icons-material/VerifiedOutlined';
import type { Resume, Experience, Education, Skill, Project, Certification } from '../types/resume';

interface ParsedResumeCardProps {
  resume: Resume;
}

function SectionHeader({ icon, title }: { icon: React.ReactNode; title: string }) {
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
      <Box sx={{ color: 'primary.main', display: 'flex' }}>{icon}</Box>
      <Typography variant="subtitle2" sx={{ fontWeight: 600, color: 'text.secondary', textTransform: 'uppercase', letterSpacing: 1 }}>
        {title}
      </Typography>
    </Box>
  );
}

function ExperienceCard({ exp }: { exp: Experience }) {
  const [open, setOpen] = useState(false);
  const hasDetails = exp.description.length > 0;
  return (
    <Box sx={{ mb: 1.5 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <Box>
          <Typography variant="body2" sx={{ fontWeight: 600, color: 'text.primary' }}>{exp.title}</Typography>
          <Typography variant="caption" sx={{ color: 'text.secondary' }}>
            {exp.company}{exp.location ? ` · ${exp.location}` : ''}
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <Typography variant="caption" sx={{ color: 'text.secondary', whiteSpace: 'nowrap' }}>
            {exp.start_date || ''} – {exp.current ? 'Present' : exp.end_date || ''}
          </Typography>
          {hasDetails && (
            <IconButton size="small" onClick={() => setOpen(!open)} sx={{ p: 0.3 }}>
              {open ? <ExpandLess fontSize="small" /> : <ExpandMore fontSize="small" />}
            </IconButton>
          )}
        </Box>
      </Box>
      <Collapse in={open || !hasDetails}>
        {exp.description.map((d, i) => (
          <Typography key={i} variant="caption" sx={{ display: 'block', color: 'text.secondary', mt: 0.3, pl: 1, borderLeft: '2px solid', borderColor: 'primary.main' }}>
            {d}
          </Typography>
        ))}
      </Collapse>
    </Box>
  );
}

function EducationCard({ edu }: { edu: Education }) {
  return (
    <Box sx={{ mb: 1.5 }}>
      <Typography variant="body2" sx={{ fontWeight: 600, color: 'text.primary' }}>{edu.degree}{edu.field ? ` in ${edu.field}` : ''}</Typography>
      <Typography variant="caption" sx={{ color: 'text.secondary' }}>
        {edu.institution}
        {edu.start_date ? ` · ${edu.start_date} – ${edu.end_date || ''}` : ''}
        {edu.gpa ? ` · GPA: ${edu.gpa}` : ''}
      </Typography>
      {edu.achievements.map((a, i) => (
        <Typography key={i} variant="caption" sx={{ display: 'block', color: 'text.secondary', mt: 0.2 }}>– {a}</Typography>
      ))}
    </Box>
  );
}

function SkillsSection({ skills }: { skills: Skill[] }) {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
      {skills.map((s) => (
        <Box key={s.category}>
          <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.secondary', display: 'block', mb: 0.3 }}>{s.category}</Typography>
          <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
            {s.skills.map((skill) => (
              <Chip key={skill} label={skill} size="small" variant="outlined" sx={{ borderRadius: 1 }} />
            ))}
          </Box>
        </Box>
      ))}
    </Box>
  );
}

function ProjectCard({ project }: { project: Project }) {
  return (
    <Box sx={{ mb: 1.5 }}>
      <Typography variant="body2" sx={{ fontWeight: 600, color: 'text.primary' }}>{project.name}</Typography>
      {project.description && (
        <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block' }}>{project.description}</Typography>
      )}
      {project.technologies.length > 0 && (
        <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mt: 0.5 }}>
          {project.technologies.map((t) => (
            <Chip key={t} label={t} size="small" variant="outlined" sx={{ borderRadius: 1 }} />
          ))}
        </Box>
      )}
    </Box>
  );
}

function CertificationCard({ cert }: { cert: Certification }) {
  return (
    <Box sx={{ mb: 1 }}>
      <Typography variant="body2" sx={{ fontWeight: 600, color: 'text.primary' }}>{cert.name}</Typography>
      <Typography variant="caption" sx={{ color: 'text.secondary' }}>
        {cert.issuer}{cert.date ? ` · ${cert.date}` : ''}
      </Typography>
    </Box>
  );
}

function ParsedResumeCard({ resume }: ParsedResumeCardProps) {
  return (
    <Card sx={{ mt: 3, p: 2.5, animation: 'fadeIn 0.5s ease-out' }}>
      <CardContent sx={{ p: 0, '&:last-child': { pb: 0 } }}>
        <Box sx={{ mb: 2 }}>
          <Typography variant="h5" sx={{ fontWeight: 700, color: 'text.primary' }}>{resume.full_name}</Typography>
          <Typography variant="body2" sx={{ color: 'text.secondary' }}>
            {resume.email}{resume.phone ? ` · ${resume.phone}` : ''}{resume.location ? ` · ${resume.location}` : ''}
          </Typography>
          <Box sx={{ display: 'flex', gap: 1.5, mt: 0.5, flexWrap: 'wrap' }}>
            {resume.linkedin && <Typography variant="caption" sx={{ color: 'primary.main' }}>{resume.linkedin}</Typography>}
            {resume.github && <Typography variant="caption" sx={{ color: 'primary.main' }}>{resume.github}</Typography>}
            {resume.website && <Typography variant="caption" sx={{ color: 'primary.main' }}>{resume.website}</Typography>}
          </Box>
        </Box>

        {resume.summary && (
          <Typography variant="body2" sx={{ color: 'text.secondary', mb: 2, lineHeight: 1.6 }}>
            {resume.summary}
          </Typography>
        )}

        <Divider sx={{ mb: 2 }} />

        {resume.experience.length > 0 && (
          <Box sx={{ mb: 2 }}>
            <SectionHeader icon={<BusinessCenterOutlined fontSize="small" />} title="Experience" />
            {resume.experience.map((exp, i) => <ExperienceCard key={i} exp={exp} />)}
          </Box>
        )}

        {resume.education.length > 0 && (
          <Box sx={{ mb: 2 }}>
            <SectionHeader icon={<SchoolOutlined fontSize="small" />} title="Education" />
            {resume.education.map((edu, i) => <EducationCard key={i} edu={edu} />)}
          </Box>
        )}

        {resume.skills.length > 0 && (
          <Box sx={{ mb: 2 }}>
            <SectionHeader icon={<CodeOutlined fontSize="small" />} title="Skills" />
            <SkillsSection skills={resume.skills} />
          </Box>
        )}

        {resume.projects.length > 0 && (
          <Box sx={{ mb: 2 }}>
            <SectionHeader icon={<FolderOutlined fontSize="small" />} title="Projects" />
            {resume.projects.map((p, i) => <ProjectCard key={i} project={p} />)}
          </Box>
        )}

        {resume.certifications.length > 0 && (
          <Box>
            <SectionHeader icon={<VerifiedOutlined fontSize="small" />} title="Certifications" />
            {resume.certifications.map((c, i) => <CertificationCard key={i} cert={c} />)}
          </Box>
        )}
      </CardContent>
    </Card>
  );
}

export default ParsedResumeCard;
