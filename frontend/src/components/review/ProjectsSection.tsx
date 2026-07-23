import { Box, Button, TextField, IconButton, Typography, Card } from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DeleteOutlined from '@mui/icons-material/DeleteOutlined';
import type { Resume, Project } from '../../types/resume';

interface ProjectsSectionProps {
  resume: Resume;
  onChange: (r: Resume) => void;
}

function emptyProj(): Project {
  return { name: '', description: '', url: '', technologies: [] };
}

function ProjectsSection({ resume, onChange }: ProjectsSectionProps) {
  const list = resume.projects;

  const update = (idx: number, proj: Project) => {
    const next = [...list];
    next[idx] = proj;
    onChange({ ...resume, projects: next });
  };

  const remove = (idx: number) => {
    onChange({ ...resume, projects: list.filter((_, i) => i !== idx) });
  };

  const add = () => {
    onChange({ ...resume, projects: [...list, emptyProj()] });
  };

  return (
    <Box>
      {list.map((p, i) => (
        <Card key={i} sx={{ p: 2, mb: 2 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1.5 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>Project #{i + 1}</Typography>
            <IconButton size="small" color="error" aria-label="Delete item" onClick={() => remove(i)}>
              <DeleteOutlined fontSize="small" />
            </IconButton>
          </Box>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
            <TextField label="Project Name" value={p.name} onChange={(e) => update(i, { ...p, name: e.target.value })} required fullWidth />
            <TextField label="Description" value={p.description || ''} onChange={(e) => update(i, { ...p, description: e.target.value })} multiline rows={2} fullWidth />
            <Box sx={{ display: 'flex', gap: 1.5 }}>
              <TextField label="URL" value={p.url || ''} onChange={(e) => update(i, { ...p, url: e.target.value })} sx={{ flex: 1 }} />
              <TextField
                label="Technologies (comma-separated)"
                value={p.technologies.join(', ')}
                onChange={(e) => update(i, { ...p, technologies: e.target.value.split(',').map((s) => s.trim()).filter(Boolean) })}
                sx={{ flex: 2 }}
              />
            </Box>
          </Box>
        </Card>
      ))}
      <Button startIcon={<AddIcon />} onClick={add} variant="outlined" sx={{ textTransform: 'none', borderRadius: 2 }}>
        Add Project
      </Button>
    </Box>
  );
}

export default ProjectsSection;
