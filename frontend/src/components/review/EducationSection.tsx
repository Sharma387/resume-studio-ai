import { Box, Button, TextField, IconButton, Typography, Card } from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DeleteOutlined from '@mui/icons-material/DeleteOutlined';
import type { Resume, Education } from '../../types/resume';

interface EducationSectionProps {
  resume: Resume;
  onChange: (r: Resume) => void;
}

function emptyEdu(): Education {
  return { institution: '', degree: '', field: '', start_date: '', end_date: '', gpa: undefined, achievements: [] };
}

function EducationSection({ resume, onChange }: EducationSectionProps) {
  const list = resume.education;

  const update = (idx: number, edu: Education) => {
    const next = [...list];
    next[idx] = edu;
    onChange({ ...resume, education: next });
  };

  const remove = (idx: number) => {
    onChange({ ...resume, education: list.filter((_, i) => i !== idx) });
  };

  const add = () => {
    onChange({ ...resume, education: [...list, emptyEdu()] });
  };

  return (
    <Box>
      {list.map((edu, i) => (
        <Card key={i} sx={{ p: 2, mb: 2 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1.5 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>Education #{i + 1}</Typography>
            <IconButton size="small" color="error" aria-label="Delete item" onClick={() => remove(i)}>
              <DeleteOutlined fontSize="small" />
            </IconButton>
          </Box>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
            <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap' }}>
              <TextField label="Institution" value={edu.institution} onChange={(e) => update(i, { ...edu, institution: e.target.value })} required sx={{ flex: 1 }} />
              <TextField label="Degree" value={edu.degree} onChange={(e) => update(i, { ...edu, degree: e.target.value })} required sx={{ flex: 1 }} />
            </Box>
            <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap' }}>
              <TextField label="Field of Study" value={edu.field || ''} onChange={(e) => update(i, { ...edu, field: e.target.value })} sx={{ flex: 1 }} />
              <TextField label="Start Date" value={edu.start_date || ''} onChange={(e) => update(i, { ...edu, start_date: e.target.value })} sx={{ flex: 1 }} />
              <TextField label="End Date" value={edu.end_date || ''} onChange={(e) => update(i, { ...edu, end_date: e.target.value })} sx={{ flex: 1 }} />
              <TextField label="GPA" type="number" value={edu.gpa ?? ''} onChange={(e) => update(i, { ...edu, gpa: e.target.value ? parseFloat(e.target.value) : undefined })} slotProps={{ htmlInput: { min: 0, max: 4, step: 0.1 } }} sx={{ width: 100 }} />
            </Box>
            <TextField
              label="Achievements (one per line)"
              value={edu.achievements.join('\n')}
              onChange={(e) => update(i, { ...edu, achievements: e.target.value.split('\n').filter(Boolean) })}
              multiline
              rows={2}
              fullWidth
            />
          </Box>
        </Card>
      ))}
      <Button startIcon={<AddIcon />} onClick={add} variant="outlined" sx={{ textTransform: 'none', borderRadius: 2 }}>
        Add Education
      </Button>
    </Box>
  );
}

export default EducationSection;
