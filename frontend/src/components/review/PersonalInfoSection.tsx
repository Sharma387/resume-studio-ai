import { Box, TextField } from '@mui/material';
import type { Resume } from '../../types/resume';

interface PersonalInfoSectionProps {
  resume: Resume;
  onChange: (r: Resume) => void;
}

function PersonalInfoSection({ resume, onChange }: PersonalInfoSectionProps) {
  const set = <K extends keyof Resume>(field: K, value: Resume[K]) => {
    onChange({ ...resume, [field]: value });
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.5 }}>
      <TextField
        label="Full Name"
        value={resume.full_name}
        onChange={(e) => set('full_name', e.target.value)}
        required
        fullWidth
        error={resume.full_name.trim() === ''}
        helperText={resume.full_name.trim() === '' ? 'Required' : ''}
      />
      <TextField
        label="Email"
        type="email"
        value={resume.email}
        onChange={(e) => set('email', e.target.value)}
        required
        fullWidth
        error={!resume.email.includes('@')}
        helperText={!resume.email.includes('@') ? 'Valid email required' : ''}
      />
      <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
        <TextField label="Phone" value={resume.phone || ''} onChange={(e) => set('phone', e.target.value || undefined)} sx={{ flex: 1 }} />
        <TextField label="Location" value={resume.location || ''} onChange={(e) => set('location', e.target.value || undefined)} sx={{ flex: 1 }} />
      </Box>
      <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
        <TextField label="LinkedIn" value={resume.linkedin || ''} onChange={(e) => set('linkedin', e.target.value || undefined)} fullWidth />
      </Box>
      <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
        <TextField label="GitHub" value={resume.github || ''} onChange={(e) => set('github', e.target.value || undefined)} sx={{ flex: 1 }} />
        <TextField label="Website" value={resume.website || ''} onChange={(e) => set('website', e.target.value || undefined)} sx={{ flex: 1 }} />
      </Box>
    </Box>
  );
}

export default PersonalInfoSection;
