import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box, Grid, Card, CardContent, CardMedia, Typography, Button, Chip,
  TextField, Select, MenuItem, FormControl, InputLabel, CircularProgress,
  Alert, Rating,
} from '@mui/material';
import { authFetch } from '../services/authFetch';
import API_URL from '../config';

interface TemplateInfo {
  id: string; name: string; description: string; category: string;
  ats_score: number; colour_themes: string[]; tags: string[];
  has_preview: boolean; has_thumbnail: boolean;
}

export default function TemplateGalleryPage() {
  const navigate = useNavigate();
  const [templates, setTemplates] = useState<TemplateInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [sort, setSort] = useState('name');
  const [resumeId, setResumeId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [tRes, rRes] = await Promise.all([
        authFetch(`${API_URL}/resume/templates`),
        authFetch(`${API_URL}/resumes`),
      ]);
      const tBody = await tRes.json();
      if (tBody.success) setTemplates(tBody.data);
      const rBody = await rRes.json();
      if (rBody.success && rBody.data?.length) setResumeId(rBody.data[0].id);
    } catch { /* ignore */ }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  let filtered = templates.filter(t =>
    (t.name.toLowerCase().includes(search.toLowerCase()) ||
     t.description.toLowerCase().includes(search.toLowerCase())) &&
    (!category || t.category === category)
  );

  filtered.sort((a, b) => {
    switch (sort) {
      case 'ats': return b.ats_score - a.ats_score;
      case 'name': return a.name.localeCompare(b.name);
      default: return 0;
    }
  });

  const categories = [...new Set(templates.map(t => t.category))];

  return (
    <Box sx={{ maxWidth: 1200, mx: 'auto', py: 4, px: 2 }}>
      <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>Choose Your Template</Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Select a professionally designed template for your resume.
      </Typography>

      <Box sx={{ display: 'flex', gap: 2, mb: 4, flexWrap: 'wrap' }}>
        <TextField size="small" placeholder="Search templates..." value={search}
          onChange={(e) => setSearch(e.target.value)} sx={{ minWidth: 250 }} />
        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel>Category</InputLabel>
          <Select value={category} label="Category" onChange={(e) => setCategory(e.target.value)}>
            <MenuItem value="">All</MenuItem>
            {categories.map(c => <MenuItem key={c} value={c}>{c}</MenuItem>)}
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel>Sort By</InputLabel>
          <Select value={sort} label="Sort By" onChange={(e) => setSort(e.target.value)}>
            <MenuItem value="name">Name</MenuItem>
            <MenuItem value="ats">ATS Score</MenuItem>
          </Select>
        </FormControl>
      </Box>

      {/* New layout engine previews (structure-changing layouts) */}
      <Card sx={{ mb: 4, p: 2 }}>
        <Typography variant="h6" sx={{ fontWeight: 600, mb: 0.5 }}>New Engine Layouts</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
          Materially different resume structures from the layout engine.
        </Typography>
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          {['executive', 'modern', 'sidebar', 'timeline', 'classic', 'minimal'].map((id) => (
            <Button key={id} variant="outlined" size="small" color="primary"
              onClick={() => navigate(`/designer?layout=${id}${resumeId ? `&resume=${resumeId}` : ''}`)}>
              {id.charAt(0).toUpperCase() + id.slice(1)}
            </Button>
          ))}
        </Box>
      </Card>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}><CircularProgress /></Box>
      ) : (
        <Grid container spacing={3}>
          {filtered.map(t => (
            <Grid key={t.id} size={{ xs: 12, sm: 6, md: 4 }}>
              <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column',
                transition: 'all 0.2s', '&:hover': { transform: 'translateY(-4px)', boxShadow: 8 } }}>
                <Box sx={{ height: 180, bgcolor: 'grey.100', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Typography variant="h3" sx={{ opacity: 0.15, fontWeight: 700 }}>{t.name[0]}</Typography>
                </Box>
                <CardContent sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                    <Typography variant="h6" sx={{ fontWeight: 600 }}>{t.name}</Typography>
                    <Chip size="small" label={t.category} variant="outlined" />
                  </Box>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1, flex: 1 }}>
                    {t.description}
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                    <Typography variant="caption">ATS:</Typography>
                    <Rating value={t.ats_score / 20} readOnly size="small" precision={0.5} />
                    <Typography variant="caption">{t.ats_score}%</Typography>
                  </Box>
                  <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 2 }}>
                    {t.tags.slice(0, 3).map(tag => (
                      <Chip key={tag} label={tag} size="small" variant="outlined" />
                    ))}
                  </Box>
                  <Box sx={{ display: 'flex', gap: 1, mt: 'auto' }}>
                    <Button size="small" variant="contained" fullWidth
                      onClick={() => navigate(`/designer?template=${t.id}${resumeId ? `&resume=${resumeId}` : ''}`)}>
                      Use Template
                    </Button>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}
    </Box>
  );
}
