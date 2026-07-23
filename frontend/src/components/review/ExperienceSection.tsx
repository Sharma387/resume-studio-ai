import { Box, Button, TextField, IconButton, Typography, Card } from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DeleteOutlined from '@mui/icons-material/DeleteOutlined';
import type { Resume, Experience } from '../../types/resume';

interface ExperienceSectionProps {
  resume: Resume;
  onChange: (r: Resume) => void;
}

function emptyExp(): Experience {
  return { company: '', title: '', location: '', start_date: '', end_date: '', current: false, description: [] };
}

function ExperienceSection({ resume, onChange }: ExperienceSectionProps) {
  const list = resume.experience;

  const update = (idx: number, exp: Experience) => {
    const next = [...list];
    next[idx] = exp;
    onChange({ ...resume, experience: next });
  };

  const remove = (idx: number) => {
    onChange({ ...resume, experience: list.filter((_, i) => i !== idx) });
  };

  const add = () => {
    onChange({ ...resume, experience: [...list, emptyExp()] });
  };

  return (
    <Box>
      {list.map((exp, i) => (
        <Card key={i} sx={{ p: 2, mb: 2 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1.5 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>Experience #{i + 1}</Typography>
            <IconButton size="small" color="error" aria-label="Delete item" onClick={() => remove(i)}>
              <DeleteOutlined fontSize="small" />
            </IconButton>
          </Box>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
            <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap' }}>
              <TextField label="Company" value={exp.company} onChange={(e) => update(i, { ...exp, company: e.target.value })} required sx={{ flex: 1 }} />
              <TextField label="Title" value={exp.title} onChange={(e) => update(i, { ...exp, title: e.target.value })} required sx={{ flex: 1 }} />
            </Box>
            <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap' }}>
              <TextField label="Location" value={exp.location || ''} onChange={(e) => update(i, { ...exp, location: e.target.value })} sx={{ flex: 1 }} />
              <TextField label="Start Date" value={exp.start_date || ''} onChange={(e) => update(i, { ...exp, start_date: e.target.value })} sx={{ flex: 1 }} />
              <TextField label="End Date" value={exp.end_date || ''} onChange={(e) => update(i, { ...exp, end_date: e.target.value })} sx={{ flex: 1 }} disabled={exp.current} />
            </Box>
            <TextField
              label="Description (one per line)"
              value={exp.description.join('\n')}
              onChange={(e) => update(i, { ...exp, description: e.target.value.split('\n').filter(Boolean) })}
              multiline
              rows={3}
              fullWidth
            />
          </Box>
        </Card>
      ))}
      <Button startIcon={<AddIcon />} onClick={add} variant="outlined" sx={{ textTransform: 'none', borderRadius: 2 }}>
        Add Experience
      </Button>
    </Box>
  );
}

export default ExperienceSection;
