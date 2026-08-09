import { useState, useEffect, useCallback, useRef } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  Box, Drawer, Typography, Button, Select, MenuItem, FormControl, InputLabel,
  Slider, CircularProgress, Alert, IconButton, Chip, Divider, Switch, FormControlLabel,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import RefreshIcon from '@mui/icons-material/Refresh';
import { authFetch } from '../services/authFetch';
import API_URL from '../config';

// New layout-engine ids (match backend reference layouts/themes).
const LAYOUT_IDS = ['executive', 'modern', 'sidebar', 'timeline', 'classic', 'minimal'];
const THEME_IDS = ['blue', 'slate', 'forest', 'gold', 'minimal'];

const titleCase = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

export default function TemplateDesignerPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const templateId = searchParams.get('template') || 'executive-elite';
  const resumeId = searchParams.get('resume');
  const layoutId = searchParams.get('layout');
  const isLayoutMode = Boolean(layoutId);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  const [template, setTemplate] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [theme, setTheme] = useState(isLayoutMode ? 'blue' : 'default');
  const [layout, setLayout] = useState(layoutId || 'executive');
  const [sectionOrder, setSectionOrder] = useState<string[]>([]);

  useEffect(() => {
    if (isLayoutMode) {
      setLoading(false);
      return;
    }
    const load = async () => {
      setLoading(true);
      try {
        const [tRes] = await Promise.all([
          authFetch(`${API_URL}/resume/templates/${templateId}`),
        ]);
        const tBody = await tRes.json();
        if (tBody.success) {
          setTemplate(tBody.data);
          if (tBody.data.colour_themes?.length) {
            setTheme(tBody.data.colour_themes[0]);
          }
        }
      } catch { /* ignore */ }
      setLoading(false);
    };
    load();
  }, [templateId, isLayoutMode]);

  const generatePreview = useCallback(async () => {
    if (!resumeId) return;
    if (!isLayoutMode && !template) return;
    setError(null);
    try {
      const params = isLayoutMode
        ? `layout_id=${layout}&theme=${theme}`
        : `template_id=${templateId}&theme=${theme}`;
      const res = await authFetch(`${API_URL}/resume/${resumeId}/preview?${params}`);
      const body = await res.json();
      if (body.success && body.data?.preview_url) {
        setPreviewUrl(`${API_URL.replace('/api/v1', '')}${body.data.preview_url}`);
      } else {
        setError(body.detail || 'Preview failed');
      }
    } catch (e) {
      setError(String(e));
    }
  }, [resumeId, isLayoutMode, templateId, layout, theme, template]);

  useEffect(() => { if (resumeId) generatePreview(); }, [generatePreview]);

  if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}><CircularProgress /></Box>;
  if (!template && !isLayoutMode) return <Alert severity="error">Template not found</Alert>;

  const displayTitle = isLayoutMode ? titleCase(layout) : template.name;

  return (
    <Box sx={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      {/* Preview Area */}
      <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', bgcolor: '#f5f5f5' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, p: 1, bgcolor: 'background.paper', borderBottom: 1, borderColor: 'divider' }}>
          <IconButton onClick={() => navigate(-1)}><ArrowBackIcon /></IconButton>
          <Typography variant="subtitle1" sx={{ fontWeight: 600, flex: 1 }}>{displayTitle}</Typography>
          {!previewUrl && resumeId && (
            <Button size="small" startIcon={<RefreshIcon />} onClick={generatePreview}>
              Generate Preview
            </Button>
          )}
        </Box>
        <Box sx={{ flex: 1, position: 'relative' }}>
          {previewUrl ? (
            <iframe ref={iframeRef} src={previewUrl} style={{ width: '100%', height: '100%', border: 'none' }} title="Resume Preview" />
          ) : (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', flexDirection: 'column', gap: 2 }}>
              <Alert severity="info" sx={{ maxWidth: 400 }}>
                {resumeId ? 'Click "Generate Preview" to see your resume.' : 'Upload and parse a resume first to see the preview.'}
              </Alert>
            </Box>
          )}
        </Box>
      </Box>

      {/* Designer Panel */}
      <Drawer variant="permanent" anchor="right" sx={{
        width: 320, flexShrink: 0, '& .MuiDrawer-paper': { width: 320, p: 2, borderLeft: 1, borderColor: 'divider' }
      }}>
        <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>Designer</Typography>

        {isLayoutMode ? (
          <>
            {/* Layout */}
            <Typography variant="subtitle2" sx={{ mt: 1, mb: 1 }}>Layout</Typography>
            <FormControl size="small" fullWidth>
              <Select value={layout} onChange={(e) => setLayout(e.target.value)}>
                {LAYOUT_IDS.map((id) => (
                  <MenuItem key={id} value={id}>{titleCase(id)}</MenuItem>
                ))}
              </Select>
            </FormControl>

            {/* Theme */}
            <Typography variant="subtitle2" sx={{ mt: 2, mb: 1 }}>Theme</Typography>
            <FormControl size="small" fullWidth>
              <Select value={theme} onChange={(e) => setTheme(e.target.value)}>
                {THEME_IDS.map((id) => (
                  <MenuItem key={id} value={id}>{titleCase(id)}</MenuItem>
                ))}
              </Select>
            </FormControl>
          </>
        ) : (
          <>
            {/* Theme (legacy template themes) */}
            <Typography variant="subtitle2" sx={{ mt: 1, mb: 1 }}>Theme</Typography>
            <FormControl size="small" fullWidth>
              <Select value={theme} onChange={(e) => setTheme(e.target.value)}>
                {template.colour_themes?.map((t: string) => (
                  <MenuItem key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</MenuItem>
                ))}
              </Select>
            </FormControl>

            <Divider sx={{ my: 2 }} />

            {/* Template info */}
            <Typography variant="subtitle2" sx={{ mb: 1 }}>Template Info</Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
              <Typography variant="caption">ATS Score: {template.ats_score}%</Typography>
              <Typography variant="caption">Category: {template.category}</Typography>
              <Typography variant="caption">Supports: {
                ['photo', 'sidebar', 'two_columns', 'icons'].filter(k => template[`supports_${k}`]).join(', ')
              }</Typography>
            </Box>

            <Divider sx={{ my: 2 }} />

            {/* Tags */}
            <Typography variant="subtitle2" sx={{ mb: 1 }}>Tags</Typography>
            <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
              {template.tags?.map((tag: string) => (
                <Chip key={tag} label={tag} size="small" variant="outlined" />
              ))}
            </Box>
          </>
        )}

        {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
      </Drawer>
    </Box>
  );
}
