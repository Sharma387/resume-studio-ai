import { useState, useEffect, useCallback, useRef, type ChangeEvent } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  Box, Drawer, Typography, Button, Select, MenuItem, FormControl,
  Alert, IconButton, Divider, Paper, FormControlLabel, Switch,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import RefreshIcon from '@mui/icons-material/Refresh';
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward';
import ArrowDownwardIcon from '@mui/icons-material/ArrowDownward';
import { authFetch } from '../services/authFetch';
import {
  downloadResumeExport,
  type ExportFormat,
  type LayoutConfigPayload,
} from '../services/exportService';
import API_URL from '../config';

// Layouts and themes load from the registry endpoints so the frontend does
// not duplicate either list.
const EXPORT_FORMATS: ExportFormat[] = ['pdf', 'docx', 'html'];

// Reference layouts that ship with a supporting rail (two-column capable).
const TWO_COLUMN_LAYOUTS = new Set(['sidebar', 'modern', 'classic']);

// Sections surfaced in the placement panel, in natural reading order.
const SECTION_IDS = ['summary', 'experience', 'education', 'skills', 'projects', 'certifications', 'awards', 'languages'];

const SECTION_LABELS: Record<string, string> = {
  summary: 'Summary',
  experience: 'Experience',
  education: 'Education',
  skills: 'Skills',
  projects: 'Projects',
  certifications: 'Certifications',
  awards: 'Awards',
  languages: 'Languages',
};

const RATIOS = ['30/70', '32/68', '35/65', '40/60'];
const GAPS = ['none', 'compact', 'balanced', 'wide'];
const DENSITIES = ['compact', 'normal', 'spacious'];

const titleCase = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

export default function TemplateDesignerPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const resumeId = searchParams.get('resume');
  // The URL is the single source of truth for layout and theme so that
  // refresh and Back/Forward always preserve the current selection.
  const layout = searchParams.get('layout') || 'executive';
  const theme = searchParams.get('theme') || 'blue';
  const iframeRef = useRef<HTMLIFrameElement>(null);

  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [layoutOptions, setLayoutOptions] = useState<string[]>([layout]);
  const [themeOptions, setThemeOptions] = useState<string[]>([theme]);
  const [themesError, setThemesError] = useState<string | null>(null);
  const [configError, setConfigError] = useState<string | null>(null);
  const [exporting, setExporting] = useState<ExportFormat | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const previewSeqRef = useRef(0);

  const [mode, setMode] = useState<'single' | 'two_column'>('single');
  const [sidebar, setSidebar] = useState<'left' | 'right'>('left');
  const [ratio, setRatio] = useState('35/65');
  const [gap, setGap] = useState<'none' | 'compact' | 'balanced' | 'wide'>('balanced');
  const [density, setDensity] = useState<'compact' | 'normal' | 'spacious'>('normal');
  const [autoBalance, setAutoBalance] = useState(false);
  const [balanceRationale, setBalanceRationale] = useState<string | null>(null);
  const [balanceConfig, setBalanceConfig] = useState<LayoutConfigPayload | null>(null);
  const [savingBalance, setSavingBalance] = useState(false);
  const [balanceSaved, setBalanceSaved] = useState(false);
  const [sectionOrder, setSectionOrder] = useState<string[]>(SECTION_IDS);
  const [sectionRegion, setSectionRegion] = useState<Record<string, 'auto' | 'main' | 'sidebar'>>({});

  const twoColumn = mode === 'two_column';

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

  useEffect(() => {
    const load = async () => {
      try {
        const res = await authFetch(`${API_URL}/resume/themes`);
        const body = await res.json();
        if (body.success && Array.isArray(body.data) && body.data.length) {
          setThemeOptions(body.data.map((t: { theme_id: string }) => t.theme_id));
          setThemesError(null);
        } else {
          setThemesError('Themes are temporarily unavailable.');
        }
      } catch {
        setThemesError('Themes are temporarily unavailable.');
      }
    };
    load();
  }, []);

  // Load persisted layout customization when the resume/layout changes.
  useEffect(() => {
    const loadConfig = async () => {
      if (!resumeId) return;
      setConfigError(null);
      try {
        const res = await authFetch(`${API_URL}/resume/${resumeId}/layout-config`);
        const body = await res.json();
        const saved = body.success
          ? (body.data?.layout_config as LayoutConfigPayload | undefined)
          : undefined;
        const fallbackMode: 'single' | 'two_column' = TWO_COLUMN_LAYOUTS.has(layout) ? 'two_column' : 'single';
        setMode(saved?.mode === 'two_column' || saved?.mode === 'single' ? saved.mode : fallbackMode);
        setSidebar(saved?.sidebar === 'right' ? 'right' : 'left');
        if (saved?.ratio && RATIOS.includes(saved.ratio)) setRatio(saved.ratio);
        if (saved?.gap && GAPS.includes(saved.gap)) setGap(saved.gap as typeof gap);
        if (saved?.density && DENSITIES.includes(saved.density)) setDensity(saved.density as typeof density);

        const regions: Record<string, 'auto' | 'main' | 'sidebar'> = {};
        const orders = new Map<string, number>();
        for (const [id, cfg] of Object.entries(saved?.sections ?? {})) {
          if (cfg.region === 'main' || cfg.region === 'sidebar') regions[id] = cfg.region;
          if (typeof cfg.order === 'number') orders.set(id, cfg.order);
        }
        setSectionRegion(regions);
        const ordered = SECTION_IDS.filter((id) => orders.has(id))
          .sort((a, b) => (orders.get(a) ?? 0) - (orders.get(b) ?? 0))
          .concat(SECTION_IDS.filter((id) => !orders.has(id)));
        setSectionOrder(ordered);
      } catch {
        setConfigError('Layout settings could not be loaded.');
      }
    };
    loadConfig();
  }, [resumeId, layout]);

  const updateSelection = (next: { layout?: string; theme?: string }) => {
    const params = new URLSearchParams();
    if (resumeId) params.set('resume', resumeId);
    params.set('layout', next.layout ?? layout);
    params.set('theme', next.theme ?? theme);
    navigate(`/designer?${params.toString()}`, { replace: true });
  };

  // Build the LayoutConfig payload from the current UI state. Section order
  // overrides only include sections the user moved; region overrides only
  // include sections with an explicit region.
  const buildConfig = (next: {
    mode?: 'single' | 'two_column';
    sidebar?: 'left' | 'right';
    ratio?: string;
    gap?: typeof gap;
    density?: typeof density;
    order?: string[];
    region?: Record<string, 'auto' | 'main' | 'sidebar'>;
  }): LayoutConfigPayload => {
    const m = next.mode ?? mode;
    const g = next.gap ?? gap;
    // "Normal" matches the engine default; sending it keeps the config
    // explicit-but-stable while density persists across refreshes.
    const config: LayoutConfigPayload = { mode: m, gap: g, density: next.density ?? density };
    if (m === 'two_column') {
      config.sidebar = next.sidebar ?? sidebar;
      config.ratio = (next.ratio ?? ratio) as LayoutConfigPayload['ratio'];
    }
    const order = next.order ?? sectionOrder;
    const region = next.region ?? sectionRegion;
    const sections: Record<string, { region?: 'main' | 'sidebar'; order?: number }> = {};
    order.forEach((id, idx) => {
      const entry: { region?: 'main' | 'sidebar'; order?: number } = {};
      if (region[id] === 'main' || region[id] === 'sidebar') entry.region = region[id];
      if (idx !== SECTION_IDS.indexOf(id)) entry.order = idx;
      if (entry.region !== undefined || entry.order !== undefined) sections[id] = entry;
    });
    if (Object.keys(sections).length) config.sections = sections;
    return config;
  };

  const generatePreview = useCallback(async () => {
    if (!resumeId) return;
    const seq = ++previewSeqRef.current;
    setError(null);
    try {
      const params = new URLSearchParams({ layout_id: layout, theme });
      if (autoBalance) params.set('auto_balance', 'true');
      const res = await authFetch(
        `${API_URL}/resume/${resumeId}/preview?${params.toString()}`
      );
      const body = await res.json();
      if (seq !== previewSeqRef.current) return; // a newer request superseded this one
      if (body.success && body.data?.preview_url) {
        setPreviewUrl(`${API_URL.replace('/api/v1', '')}${body.data.preview_url}`);
        setBalanceRationale(body.data?.layout_rationale ?? null);
        setBalanceConfig((body.data?.balanced_config as LayoutConfigPayload) ?? null);
        setBalanceSaved(false);
      } else {
        setBalanceRationale(null);
        setBalanceConfig(null);
        setError(body.detail || 'Preview failed');
      }
    } catch (e) {
      if (seq === previewSeqRef.current) {
        setBalanceRationale(null);
        setBalanceConfig(null);
        setError(String(e));
      }
    }
  }, [resumeId, layout, theme, autoBalance]);

  // Persist a config change, then regenerate the preview (which applies the
  // persisted customization via the API's precedence rule).
  const applyChange = async (next: Parameters<typeof buildConfig>[0]) => {
    if (!resumeId) return;
    setConfigError(null);
    try {
      const res = await authFetch(`${API_URL}/resume/${resumeId}/layout-config`, {
        method: 'PUT',
        body: JSON.stringify({ config: buildConfig(next) }),
      });
      const body = await res.json();
      if (!body.success) {
        setConfigError(typeof body.detail === 'string' ? body.detail : 'Could not save layout settings.');
        return;
      }
      generatePreview();
    } catch (e) {
      setConfigError(String(e));
    }
  };

  const handleModeChange = (value: 'single' | 'two_column') => {
    setMode(value);
    if (value === 'single') {
      // Single-column has no rail; drop any sidebar placement overrides.
      const region = { ...sectionRegion };
      for (const id of SECTION_IDS) if (region[id] === 'sidebar') region[id] = 'auto';
      setSectionRegion(region);
      applyChange({ mode: value, region });
    } else {
      applyChange({ mode: value });
    }
  };

  const moveSection = (index: number, dir: -1 | 1) => {
    const target = index + dir;
    if (target < 0 || target >= sectionOrder.length) return;
    const order = [...sectionOrder];
    [order[index], order[target]] = [order[target], order[index]];
    setSectionOrder(order);
    applyChange({ order });
  };

  const handleRegionChange = (id: string, value: 'auto' | 'main' | 'sidebar') => {
    const next = { ...sectionRegion };
    if (value === 'auto') delete next[id];
    else next[id] = value;
    setSectionRegion(next);
    applyChange({ region: next });
  };

  const handleSidebarChange = (value: 'left' | 'right') => {
    setSidebar(value);
    applyChange({ sidebar: value });
  };

  const handleRatioChange = (value: string) => {
    setRatio(value);
    applyChange({ ratio: value });
  };

  const handleGapChange = (value: typeof gap) => {
    setGap(value);
    applyChange({ gap: value });
  };

  const handleDensityChange = (value: typeof density) => {
    setDensity(value);
    applyChange({ density: value });
  };

  const handleAutoBalanceChange = (event: ChangeEvent<HTMLInputElement>) => {
    const next = event.target.checked;
    setAutoBalance(next);
    // Auto-balance is a request-time transformation; regenerate the preview to
    // reflect the new toggle without persisting anything.
    if (resumeId) generatePreview();
  };

  useEffect(() => { if (resumeId) generatePreview(); }, [generatePreview, resumeId]);

  const handleSaveBalance = async () => {
    if (!resumeId || !balanceConfig || savingBalance) return;
    setSavingBalance(true);
    setConfigError(null);
    try {
      const res = await authFetch(`${API_URL}/resume/${resumeId}/layout-config`, {
        method: 'PUT',
        body: JSON.stringify({ config: balanceConfig }),
      });
      const body = await res.json();
      if (!body.success) {
        setConfigError(typeof body.detail === 'string' ? body.detail : 'Could not save balanced layout.');
        return;
      }
      // Reconcile local manual-config state so toggling auto-balance OFF now
      // reflects the saved balanced layout.
      const saved = balanceConfig;
      if (saved.mode === 'single' || saved.mode === 'two_column') setMode(saved.mode);
      if (saved.sidebar === 'left' || saved.sidebar === 'right') setSidebar(saved.sidebar);
      if (saved.ratio && RATIOS.includes(saved.ratio)) setRatio(saved.ratio);
      if (saved.gap && GAPS.includes(saved.gap)) setGap(saved.gap as typeof gap);
      if (saved.density && DENSITIES.includes(saved.density)) setDensity(saved.density as typeof density);
      const regions: Record<string, 'auto' | 'main' | 'sidebar'> = {};
      const orders = new Map<string, number>();
      for (const [id, cfg] of Object.entries(saved.sections ?? {})) {
        if (cfg.region === 'main' || cfg.region === 'sidebar') regions[id] = cfg.region;
        if (typeof cfg.order === 'number') orders.set(id, cfg.order);
      }
      setSectionRegion(regions);
      const ordered = SECTION_IDS.filter((id) => orders.has(id))
        .sort((a, b) => (orders.get(a) ?? 0) - (orders.get(b) ?? 0))
        .concat(SECTION_IDS.filter((id) => !orders.has(id)));
      setSectionOrder(ordered);
      setBalanceSaved(true);
    } catch (e) {
      setConfigError(String(e));
    } finally {
      setSavingBalance(false);
    }
  };

  const handleExport = async (format: ExportFormat) => {
    if (!resumeId) return;
    setExporting(format);
    setExportError(null);
    try {
      await downloadResumeExport(resumeId, layout, theme, format, undefined, autoBalance);
    } catch (e) {
      const message = e instanceof Error && e.message ? e.message : "We couldn't generate the export. Please try again.";
      setExportError(message);
    } finally {
      setExporting(null);
    }
  };

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
        width: 340, flexShrink: 0, '& .MuiDrawer-paper': { width: 340, p: 2, borderLeft: 1, borderColor: 'divider' }
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
            {themeOptions.map((id) => (
              <MenuItem key={id} value={id}>{titleCase(id)}</MenuItem>
            ))}
          </Select>
        </FormControl>
        {themesError && (
          <Typography variant="caption" color="error" sx={{ display: 'block', mt: 0.5 }}>
            {themesError}
          </Typography>
        )}

        {/* Layout Customization */}
        <Divider sx={{ my: 2 }} />
        <Typography variant="subtitle2" sx={{ mb: 1 }}>Layout Settings</Typography>

        <FormControlLabel
          control={<Switch checked={autoBalance} onChange={handleAutoBalanceChange} />}
          label="Auto-balance layout"
          sx={{ mb: 1 }}
        />
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1.5 }}>
          Let the engine pick the layout from your resume content. This is a live preview
          only and does not replace your saved layout settings.
        </Typography>
        {autoBalance && balanceConfig && (
          <Box sx={{ mb: 1.5, p: 1, bgcolor: 'background.default', borderRadius: 1, border: '1px solid', borderColor: 'divider' }}>
            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, display: 'block' }}>
              Why this layout?
            </Typography>
            {balanceRationale && (
              <Typography variant="caption" sx={{ display: 'block', mb: 1 }}>{balanceRationale}</Typography>
            )}
            <Button
              size="small"
              variant="outlined"
              onClick={handleSaveBalance}
              disabled={savingBalance}
            >
              {savingBalance ? 'Saving…' : 'Save balanced layout'}
            </Button>
            {balanceSaved && !savingBalance && (
              <Typography variant="caption" color="success.main" sx={{ display: 'block', mt: 0.5 }}>
                Saved as your layout.
              </Typography>
            )}
          </Box>
        )}

        <Typography variant="caption" color="text.secondary">Mode</Typography>
        <FormControl size="small" fullWidth sx={{ mb: 1.5 }}>
          <Select value={mode} onChange={(e) => handleModeChange(String(e.target.value) as 'single' | 'two_column')}>
            <MenuItem value="single">Single Column</MenuItem>
            <MenuItem value="two_column">Two Column</MenuItem>
          </Select>
        </FormControl>

        <Typography variant="caption" color="text.secondary">Sidebar Side</Typography>
        <FormControl size="small" fullWidth sx={{ mb: 1.5 }} disabled={!twoColumn}>
          <Select value={sidebar} onChange={(e) => handleSidebarChange(e.target.value as 'left' | 'right')}>
            <MenuItem value="left">Left</MenuItem>
            <MenuItem value="right">Right</MenuItem>
          </Select>
        </FormControl>

        <Typography variant="caption" color="text.secondary">Column Ratio</Typography>
        <FormControl size="small" fullWidth sx={{ mb: 1.5 }} disabled={!twoColumn}>
          <Select value={ratio} onChange={(e) => handleRatioChange(String(e.target.value))}>
            {RATIOS.map((r) => <MenuItem key={r} value={r}>{r}</MenuItem>)}
          </Select>
        </FormControl>

        <Typography variant="caption" color="text.secondary">Density</Typography>
        <FormControl size="small" fullWidth sx={{ mb: 1.5 }}>
          <Select value={density} onChange={(e) => handleDensityChange(e.target.value as typeof density)}>
            {DENSITIES.map((d) => <MenuItem key={d} value={d}>{titleCase(d)}</MenuItem>)}
          </Select>
        </FormControl>

        <Typography variant="caption" color="text.secondary">Gap</Typography>
        <FormControl size="small" fullWidth sx={{ mb: 1.5 }}>
          <Select value={gap} onChange={(e) => handleGapChange(e.target.value as typeof gap)}>
            {GAPS.map((g) => <MenuItem key={g} value={g}>{titleCase(g)}</MenuItem>)}
          </Select>
        </FormControl>

        <Typography variant="subtitle2" sx={{ mt: 1, mb: 0.5 }}>Section Placement</Typography>
        <Paper variant="outlined" sx={{ p: 1, mb: 1, bgcolor: 'background.default' }}>
          {SECTION_IDS.map((id, idx) => (
            <Box key={id} sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
              <Typography variant="caption" sx={{ width: 88, flexShrink: 0 }}>{SECTION_LABELS[id] ?? titleCase(id)}</Typography>
              <FormControl size="small" sx={{ flex: 1 }}>
                <Select
                  value={sectionRegion[id] ?? 'auto'}
                  onChange={(e) => handleRegionChange(id, e.target.value as 'auto' | 'main' | 'sidebar')}
                >
                  <MenuItem value="auto">Auto</MenuItem>
                  <MenuItem value="main">Main</MenuItem>
                  <MenuItem value="sidebar" disabled={!twoColumn}>Sidebar</MenuItem>
                </Select>
              </FormControl>
              <IconButton size="small" disabled={idx === 0} onClick={() => moveSection(idx, -1)} aria-label={`Move ${SECTION_LABELS[id]} up`}>
                <ArrowUpwardIcon fontSize="small" />
              </IconButton>
              <IconButton size="small" disabled={idx === SECTION_IDS.length - 1} onClick={() => moveSection(idx, 1)} aria-label={`Move ${SECTION_LABELS[id]} down`}>
                <ArrowDownwardIcon fontSize="small" />
              </IconButton>
            </Box>
          ))}
        </Paper>
        {configError && <Alert severity="error" sx={{ mb: 1 }}>{configError}</Alert>}

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