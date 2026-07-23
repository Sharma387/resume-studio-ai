import { Box, Button, TextField, IconButton, Typography, Card } from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DeleteOutlined from '@mui/icons-material/DeleteOutlined';
import type { Resume, Certification } from '../../types/resume';

interface CertificationsSectionProps {
  resume: Resume;
  onChange: (r: Resume) => void;
}

function emptyCert(): Certification {
  return { name: '', issuer: '', date: '', url: '' };
}

function CertificationsSection({ resume, onChange }: CertificationsSectionProps) {
  const list = resume.certifications;

  const update = (idx: number, cert: Certification) => {
    const next = [...list];
    next[idx] = cert;
    onChange({ ...resume, certifications: next });
  };

  const remove = (idx: number) => {
    onChange({ ...resume, certifications: list.filter((_, i) => i !== idx) });
  };

  const add = () => {
    onChange({ ...resume, certifications: [...list, emptyCert()] });
  };

  return (
    <Box>
      {list.map((c, i) => (
        <Card key={i} sx={{ p: 2, mb: 2 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1.5 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>Certification #{i + 1}</Typography>
            <IconButton size="small" color="error" aria-label="Delete item" onClick={() => remove(i)}>
              <DeleteOutlined fontSize="small" />
            </IconButton>
          </Box>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
            <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap' }}>
              <TextField label="Name" value={c.name} onChange={(e) => update(i, { ...c, name: e.target.value })} required sx={{ flex: 1 }} />
              <TextField label="Issuer" value={c.issuer || ''} onChange={(e) => update(i, { ...c, issuer: e.target.value })} sx={{ flex: 1 }} />
            </Box>
            <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap' }}>
              <TextField label="Date" value={c.date || ''} onChange={(e) => update(i, { ...c, date: e.target.value })} sx={{ flex: 1 }} />
              <TextField label="URL" value={c.url || ''} onChange={(e) => update(i, { ...c, url: e.target.value })} sx={{ flex: 2 }} />
            </Box>
          </Box>
        </Card>
      ))}
      <Button startIcon={<AddIcon />} onClick={add} variant="outlined" sx={{ textTransform: 'none', borderRadius: 2 }}>
        Add Certification
      </Button>
    </Box>
  );
}

export default CertificationsSection;
