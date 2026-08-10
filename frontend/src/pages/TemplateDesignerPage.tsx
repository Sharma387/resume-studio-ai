import { useState, useEffect, useCallback, useRef } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  Box, Drawer, Typography, Button, Select, MenuItem, FormControl,
  CircularProgress, Alert, IconButton, Divider,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import RefreshIcon from '@mui/icons-material/Refresh';
import { authFetch } from '../services/authFetch';
import { downloadResumeExport, type ExportFormat } from '../services/exportService';
import API_URL from '../config';

// Theme ids match the backend reference themes; layouts load from the
// registry endpoint so the frontend does not duplicate the layout list.
const THEME_IDS = ['blue', 'slate', 'forest', 'gold', 'minimal'];
const EXPORT_FORMATS: ExportFormat[] = ['pdf', 'docx', 'html'];

const titleCase = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

export default function TemplateDesignerPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const templateId = searchParams.get('template');
  const resumeId = searchParams.get('resume');
  // The URL is the single source of truth for layout and theme so that
  // refresh and Back/Forward always preserve the current selection.
  const layout = searchParams.get('layout') || 'executive';
  const theme = searchParams.get('theme') || 'blue';
  const iframeRef = useRef<HTMLIFrameElement>(null);

  const [loading, setLoading] = useState(true);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [layoutOptions, setLayoutOptions] = useState<string[]>([layout]);
  const [exporting, setExporting] = useState<ExportFormat | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const previewSeqRef = useRef(0);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await authFetch(`${API_URL}/resume/layouts`);
        const body = await res.json();
        if (body.success && Array.isArray(body.data) && body.data.length) {
          setLayoutOptions(body.data.map((l: { layout_id: string }) => l.layout_id));
        }
      } catch { /* keep current options */ }
    };
    load();
  }, []);

  const updateSelection = (next: { layout?: string; theme?: string }) => {
    const params = new URLSearchParams();
    if (resumeId) params.set('resume', resumeId);
    params.set('layout', next.layout ?? layout);
    params.set('theme', next.theme ?? theme);
    navigate(`/designer?${params.toString()}`, { replace: true });
  };

  // Legacy template URLs resolve to the canonical layout URL through the
  // backend mapping (the template endpoint exposes the mapped layout_id).
  useEffect(() => {
    if (!templateId) {
      setLoading(false);
      return;
    }
    const resolve = async () => {
      try {
        const tRes = await authFetch(`${API_URL}/resume/templates/${templateId}`);
        const tBody = await tRes.json();
        if (tBody.success && tBody.data?.layout_id) {
          navigate(
            `/designer?layout=${tBody.data.layout_id}${resumeId ? `&resume=${resumeId}` : ''}`,
            { replace: true },
          );
          return;
        }
        setError('This template cannot be opened in the layout designer.');
      } catch {
        setError('Template not found.');
      }
      setLoading(false);
    };
    resolve();
  }, [templateId, resumeId, navigate]);

  const generatePreview = useCallback(async () => {
    if (!resumeId) return;
    const seq = ++previewSeqRef.current;
    setError(null);
    try {
      const res = await authFetch(
        `${API_URL}/resume/${resumeId}/preview?layout_id=${layout}&theme=${theme}`
      );
      const body = await res.json();
      if (seq !== previewSeqRef.current) return; // a newer request superseded this one
      if (body.success && body.data?.preview_url) {
        setPreviewUrl(`${API_URL.replace('/api/v1', '')}${body.data.preview_url}`);
      } else {
        setError(body.detail || 'Preview failed');
      }
    } catch (e) {
      if (seq === previewSeqRef.current) setError(String(e));
    }
  }, [resumeId, layout, theme]);

  useEffect(() => { if (resumeId) generatePreview(); }, [generatePreview]);

  const handleExport = async (format: ExportFormat) => {
    if (!resumeId) return;
    setExporting(format);
    setExportError(null);
    try {
      await downloadResumeExport(resumeId, layout, theme, format);
    } catch (e) {
      const message = e instanceof Error && e.message ? e.message : "We couldn't generate the export. Please try again.";
      setExportError(message);
    } finally {
      setExporting(null);
    }
  };

  if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}><CircularProgress /></Box>;
  if (error && !previewUrl) return <Alert severity="error">{error}</Alert>;

  return (
    <Box sx={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      {/* Preview Area */}
      <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', bgcolor: '#f5f5f5' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, p: 1, bgcolor: 'background.paper', borderBottom: 1, borderColor: 'divider' }}>
          <IconButton onClick={() => navigate(-1)}><ArrowBackIcon /></IconButton>
          <Typography variant="subtitle1" sx={{ fontWeight: 600, flex: 1 }}>{titleCase(layout)}</Typography>
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

      {/* Layout Designer Panel */}
      <Drawer variant="permanent" anchor="right" sx={{
        width: 320, flexShrink: 0, '& .MuiDrawer-paper': { width: 320, p: 2, borderLeft: 1, borderColor: 'divider' }
      }}>
        <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>Layout Designer</Typography>

        {/* Layout */}
        <Typography variant="subtitle2" sx={{ mt: 1, mb: 1 }}>Layout</Typography>
        <FormControl size="small" fullWidth>
          <Select value={layout} onChange={(e) => updateSelection({ layout: String(e.target.value) })}>
            {layoutOptions.map((id) => (
              <MenuItem key={id} value={id}>{titleCase(id)}</MenuItem>
            ))}
          </Select>
        </FormControl>

        {/* Theme */}
        <Typography variant="subtitle2" sx={{ mt: 2, mb: 1 }}>Theme</Typography>
        <FormControl size="small" fullWidth>
          <Select value={theme} onChange={(e) => updateSelection({ theme: String(e.target.value) })}>
            {THEME_IDS.map((id) => (
              <MenuItem key={id} value={id}>{titleCase(id)}</MenuItem>
            ))}
          </Select>
        </FormControl>

        {/* Export */}
        <Divider sx={{ my: 2 }} />
        <Typography variant="subtitle2" sx={{ mb: 1 }}>Export</Typography>
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          {EXPORT_FORMATS.map((fmt) => (
            <Button
              key={fmt}
              size="small"
              variant="outlined"
              disabled={exporting !== null}
              onClick={() => handleExport(fmt)}
            >
              {exporting === fmt ? `Exporting ${fmt.toUpperCase()}...` : fmt.toUpperCase()}
            </Button>
          ))}
        </Box>
        {exportError && <Alert severity="error" sx={{ mt: 1 }}>{exportError}</Alert>}

        {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
      </Drawer>
    </Box>
  );
}
