import { useState } from 'react';
import { Box, Button, TextField, IconButton, Typography, Card, Chip } from '@mui/material';
import DeleteOutlined from '@mui/icons-material/DeleteOutlined';
import type { Resume } from '../../types/resume';

interface SkillsSectionProps {
  resume: Resume;
  onChange: (r: Resume) => void;
}

function SkillsSection({ resume, onChange }: SkillsSectionProps) {
  const [newCat, setNewCat] = useState('');
  const list = resume.skills;

  const addCategory = () => {
    if (!newCat.trim()) return;
    onChange({ ...resume, skills: [...list, { category: newCat.trim(), skills: [] }] });
    setNewCat('');
  };

  const removeCategory = (idx: number) => {
    onChange({ ...resume, skills: list.filter((_, i) => i !== idx) });
  };

  const addSkill = (catIdx: number, skill: string) => {
    const next = [...list];
    next[catIdx] = { ...next[catIdx], skills: [...next[catIdx].skills, skill] };
    onChange({ ...resume, skills: next });
  };

  const removeSkill = (catIdx: number, skillIdx: number) => {
    const next = [...list];
    next[catIdx] = { ...next[catIdx], skills: next[catIdx].skills.filter((_, i) => i !== skillIdx) };
    onChange({ ...resume, skills: next });
  };

  return (
    <Box>
      {list.map((cat, ci) => (
        <Card key={ci} sx={{ p: 2, mb: 2 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>{cat.category}</Typography>
            <IconButton size="small" color="error" onClick={() => removeCategory(ci)}>
              <DeleteOutlined fontSize="small" />
            </IconButton>
          </Box>
          <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mb: 1 }}>
            {cat.skills.map((s, si) => (
              <Chip key={si} label={s} onDelete={() => removeSkill(ci, si)} size="small" variant="outlined" sx={{ borderRadius: 1 }} />
            ))}
          </Box>
          <SkillInput onAdd={(skill) => addSkill(ci, skill)} />
        </Card>
      ))}
      <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
        <TextField
          size="small"
          placeholder="New category name"
          value={newCat}
          onChange={(e) => setNewCat(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addCategory(); } }}
        />
        <Button variant="outlined" onClick={addCategory} disabled={!newCat.trim()} sx={{ textTransform: 'none', borderRadius: 2 }}>
          Add Category
        </Button>
      </Box>
    </Box>
  );
}

function SkillInput({ onAdd }: { onAdd: (s: string) => void }) {
  const [val, setVal] = useState('');
  const handleAdd = () => {
    if (!val.trim()) return;
    onAdd(val.trim());
    setVal('');
  };
  return (
    <Box sx={{ display: 'flex', gap: 0.5 }}>
      <TextField
        size="small"
        placeholder="Add skill..."
        value={val}
        onChange={(e) => setVal(e.target.value)}
        onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleAdd(); } }}
      />
      <Button size="small" variant="text" onClick={handleAdd} disabled={!val.trim()}>Add</Button>
    </Box>
  );
}

export default SkillsSection;
