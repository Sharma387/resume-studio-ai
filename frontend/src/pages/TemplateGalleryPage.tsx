import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box, Grid, Card, CardContent, Typography, Button,
  CircularProgress, Alert,
} from '@mui/material';
import { authFetch } from '../services/authFetch';
import API_URL from '../config';

interface TemplateInfo {
  id: string; name: string; description: string; category: string;
  ats_score: number; colour_themes: string[]; tags: string[];
  has_preview: boolean; has_thumbnail: boolean; layout_id?: string | null;
}

interface LayoutInfo {
  layout_id: string; name: string; description: string;
}

const PRIMARY_ORDER: Record<string, number> = {
  executive: 0, sidebar: 1, modern: 2, classic: 3,
};
const FALLBACK_LAYOUTS: LayoutInfo[] = [
  { layout_id: 'executive', name: 'Executive', description: '' },
  { layout_id: 'sidebar', name: 'Sidebar', description: '' },
  { layout_id: 'modern', name: 'Modern', description: '' },
  { layout_id: 'classic', name: 'Classic', description: '' },
];

export default function TemplateGalleryPage() {
  const navigate = useNavigate();
  const [layouts, setLayouts] = useState<LayoutInfo[]>(FALLBACK_LAYOUTS);
  const [legacyTemplates, setLegacyTemplates] = useState<TemplateInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [resumeId, setResumeId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [lRes, tRes, rRes] = await Promise.all([
        authFetch(`${API_URL}/resume/layouts`),
        authFetch(`${API_URL}/resume/templates`),
        authFetch(`${API_URL}/resumes`),
      ]);
      const lBody = await lRes.json();
      if (lBody.success && Array.isArray(lBody.data) && lBody.data.length) {
        setLayouts(
          [...lBody.data].sort(
            (a: LayoutInfo, b: LayoutInfo) =>
              (PRIMARY_ORDER[a.layout_id] ?? 99) - (PRIMARY_ORDER[b.layout_id] ?? 99) ||
              a.layout_id.localeCompare(b.layout_id),
          ),
        );
      }
      const tBody = await tRes.json();
      if (tBody.success) setLegacyTemplates(tBody.data);
      const rBody = await rRes.json();
      if (rBody.success && rBody.data?.length) setResumeId(rBody.data[0].id);
    } catch { /* keep fallbacks */ }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const designerUrl = (layoutId: string) =>
    `/designer?layout=${layoutId}${resumeId ? `&resume=${resumeId}` : ''}`;

  return (
    <Box sx={{ maxWidth: 1200, mx: 'auto', py: 4, px: 2 }}>
      <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>Choose Your Layout</Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Select a layout — the same resume content is composed into each structure.
      </Typography>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}><CircularProgress /></Box>
      ) : (
        <>
          <Grid container spacing={3}>
            {layouts.map((layout) => (
              <Grid key={layout.layout_id} size={{ xs: 12, sm: 6, md: 4 }}>
                <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column',
                  transition: 'all 0.2s', '&:hover': { transform: 'translateY(-4px)', boxShadow: 8 } }}>
                  <Box sx={{ height: 160, bgcolor: 'grey.100', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Typography variant="h3" sx={{ opacity: 0.15, fontWeight: 700 }}>{layout.name[0]}</Typography>
                  </Box>
                  <CardContent sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                    <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>{layout.name}</Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2, flex: 1 }}>
                      {layout.description}
                    </Typography>
                    <Button size="small" variant="contained" fullWidth
                      onClick={() => navigate(designerUrl(layout.layout_id))}>
                      Use Layout
                    </Button>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>

          {legacyTemplates.length > 0 && (
            <>
              <Typography variant="h6" sx={{ fontWeight: 600, mt: 5, mb: 0.5 }}>Legacy Templates</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Legacy templates open through their mapped layout (compatibility).
              </Typography>
              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                {legacyTemplates.map((t) => (
                  <Button key={t.id} size="small" variant="outlined"
                    disabled={!t.layout_id}
                    onClick={() => t.layout_id && navigate(designerUrl(t.layout_id))}>
                    {t.name}
                  </Button>
                ))}
              </Box>
            </>
          )}
        </>
      )}

      {!loading && legacyTemplates.length === 0 && layouts.length === 0 && (
        <Alert severity="info">No layouts available.</Alert>
      )}
    </Box>
  );
}
