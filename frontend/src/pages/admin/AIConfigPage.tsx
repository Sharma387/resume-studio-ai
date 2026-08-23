import { useState, useEffect, useCallback } from 'react';
import {
  Box, Grid, Card, CardContent, Typography, Button, Alert, CircularProgress,
  Table, TableBody, TableCell, TableContainer, TableRow, Paper, Chip,
  TextField, Select, MenuItem, FormControl, InputLabel, Dialog,
  DialogTitle, DialogContent, DialogActions, Snackbar,
} from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import RefreshIcon from '@mui/icons-material/Refresh';
import SaveIcon from '@mui/icons-material/Save';
import DescriptionOutlined from '@mui/icons-material/DescriptionOutlined';
import { fetchAiConfig, testAiConnection, testAiParseSnippet, fetchModels } from '../../services/adminService';
import { authFetch } from '../../services/authFetch';
import API_URL from '../../config';
import type { AiConfig, AiTestResult, DiscoveredModel, AiParseSnippetResult } from '../../types/admin';

export default function AIConfigPage() {
  const [config, setConfig] = useState<AiConfig | null>(null);
  const [testResult, setTestResult] = useState<AiTestResult | null>(null);
  const [models, setModels] = useState<DiscoveredModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [snack, setSnack] = useState<string | null>(null);

  // Editable fields
  const [editModel, setEditModel] = useState('');
  const [editEndpoint, setEditEndpoint] = useState('');
  const [editTimeout, setEditTimeout] = useState(60);
  const [editRetries, setEditRetries] = useState(1);
  const [modelDialogOpen, setModelDialogOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [cfg, mdls] = await Promise.all([fetchAiConfig(), fetchModels()]);
      setConfig(cfg);
      setModels(mdls);
      setEditModel(cfg.model);
      setEditEndpoint(cfg.endpoint);
      setEditTimeout(cfg.timeout);
      setEditRetries(cfg.max_retries);
    } catch (e) {
      setError(String(e));
    }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const [testParseResult, setTestParseResult] = useState<AiParseSnippetResult | null>(null);
  const [testingParse, setTestingParse] = useState(false);

  const runTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await testAiConnection();
      setTestResult(result);
    } catch (e) {
      setTestResult({ endpoint: '', model: '', reachable: false, response_time_ms: null, http_status: null, error: String(e), retry_count: 0 });
    }
    setTesting(false);
  };

  const runParseTest = async () => {
    setTestingParse(true);
    setTestParseResult(null);
    try {
      const result = await testAiParseSnippet();
      setTestParseResult(result);
    } catch (e) {
      setTestParseResult({ success: false, latency_ms: null, error: String(e), parsed: null });
    }
    setTestingParse(false);
  };

  const saveConfig = async () => {
    setSaving(true);
    setError(null);
    try {
      const res = await authFetch(`${API_URL}/admin/ai`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: editModel,
          endpoint: editEndpoint,
          timeout: editTimeout,
          max_retries: editRetries,
        }),
      });
      const body = await res.json();
      if (body.success) {
        setSnack('AI configuration saved. Restart may be required.');
        await load();
      } else {
        setError(body.detail || 'Save failed');
      }
    } catch (e) {
      setError(String(e));
    }
    setSaving(false);
  };

  const selectModel = (modelId: string) => {
    setEditModel(modelId);
    setModelDialogOpen(false);
    setSnack(`Model selected: ${modelId}. Click Save to persist.`);
  };

  if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}><CircularProgress /></Box>;
  if (error) return <Alert severity="error">{error}</Alert>;

  return (
    <Box>
      <Typography variant="h5" sx={{ fontWeight: 700, mb: 3 }}>AI Configuration</Typography>

      <Grid container spacing={3}>
        {/* Configuration Editor */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>Configuration</Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <TextField label="Endpoint" size="small" value={editEndpoint}
                  onChange={(e) => setEditEndpoint(e.target.value)} fullWidth />
                <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                  <TextField label="Model" size="small" value={editModel}
                    onChange={(e) => setEditModel(e.target.value)} fullWidth />
                  <Button variant="outlined" size="small" onClick={() => setModelDialogOpen(true)}
                    sx={{ whiteSpace: 'nowrap', minWidth: 100 }}>
                    Browse Models
                  </Button>
                </Box>
                <Box sx={{ display: 'flex', gap: 2 }}>
                  <TextField label="Timeout (s)" size="small" type="number"
                    value={editTimeout} onChange={(e) => setEditTimeout(Number(e.target.value))}
                    sx={{ width: 120 }} />
                  <TextField label="Max Retries" size="small" type="number"
                    value={editRetries} onChange={(e) => setEditRetries(Number(e.target.value))}
                    sx={{ width: 120 }} />
                </Box>
                <Button variant="contained" startIcon={<SaveIcon />} onClick={saveConfig}
                  disabled={saving} sx={{ alignSelf: 'flex-start' }}>
                  {saving ? 'Saving...' : 'Save Configuration'}
                </Button>
              </Box>

              <Typography variant="subtitle2" sx={{ mt: 3, mb: 1 }}>Current Values</Typography>
              <TableContainer component={Paper} variant="outlined">
                <Table size="small">
                  <TableBody>
                    <TableRow><TableCell sx={{ fontWeight: 600 }}>Provider</TableCell><TableCell>{config?.connectivity.provider}</TableCell></TableRow>
                    <TableRow><TableCell sx={{ fontWeight: 600 }}>Endpoint</TableCell><TableCell sx={{ maxWidth: 300, wordBreak: 'break-all' }}>{config?.endpoint}</TableCell></TableRow>
                    <TableRow><TableCell sx={{ fontWeight: 600 }}>Model</TableCell><TableCell><Chip size="small" label={config?.model} color="primary" /></TableCell></TableRow>
                    <TableRow><TableCell sx={{ fontWeight: 600 }}>Timeout</TableCell><TableCell>{config?.timeout}s</TableCell></TableRow>
                    <TableRow><TableCell sx={{ fontWeight: 600 }}>Max Retries</TableCell><TableCell>{config?.max_retries}</TableCell></TableRow>
                    <TableRow><TableCell sx={{ fontWeight: 600 }}>API Key</TableCell><TableCell>{config?.key_configured ? '✅ Configured' : '❌ Not set'}</TableCell></TableRow>
                    <TableRow><TableCell sx={{ fontWeight: 600 }}>Reachable</TableCell><TableCell><Chip size="small" color={config?.connectivity.reachable ? 'success' : 'error'} label={config?.connectivity.reachable ? 'Yes' : 'No'} /></TableCell></TableRow>
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* Connection Test */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">Connection Test</Typography>
                <Button variant="contained" startIcon={<PlayArrowIcon />} onClick={runTest} disabled={testing}>
                  {testing ? 'Testing...' : 'Test Connection'}
                </Button>
              </Box>
              {testing && <CircularProgress size={24} sx={{ display: 'block', mx: 'auto', my: 2 }} />}
              {testResult && (
                <TableContainer component={Paper} variant="outlined">
                  <Table size="small">
                    <TableBody>
                      <TableRow><TableCell sx={{ fontWeight: 600 }}>Status</TableCell><TableCell><Chip size="small" color={testResult.reachable ? 'success' : 'error'} label={testResult.reachable ? 'Connected' : 'Failed'} /></TableCell></TableRow>
                      <TableRow><TableCell sx={{ fontWeight: 600 }}>Response Time</TableCell><TableCell>{testResult.response_time_ms ? `${testResult.response_time_ms}ms` : '—'}</TableCell></TableRow>
                      <TableRow><TableCell sx={{ fontWeight: 600 }}>HTTP Status</TableCell><TableCell>{testResult.http_status ?? '—'}</TableCell></TableRow>
                      <TableRow><TableCell sx={{ fontWeight: 600 }}>Response</TableCell><TableCell sx={{ maxWidth: 250, wordBreak: 'break-all' }}>{testResult.content ?? testResult.error ?? '—'}</TableCell></TableRow>
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Parse Test Card */}
      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6">Resume Parse Test</Typography>
            <Button variant="contained" startIcon={testingParse ? <CircularProgress size={18} /> : <DescriptionOutlined />}
              onClick={runParseTest} disabled={testingParse}>
              {testingParse ? 'Parsing...' : 'Test with Sample Resume'}
            </Button>
          </Box>
          {testParseResult && (
            <TableContainer component={Paper} variant="outlined">
              <Table size="small">
                <TableBody>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600 }}>Status</TableCell>
                    <TableCell><Chip size="small" color={testParseResult.success ? 'success' : 'error'}
                      label={testParseResult.success ? 'Success' : 'Failed'} /></TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600 }}>Latency</TableCell>
                    <TableCell>{testParseResult.latency_ms ? `${testParseResult.latency_ms}ms` : '—'}</TableCell>
                  </TableRow>
                  {testParseResult.parsed && (
                    <>
                      <TableRow><TableCell sx={{ fontWeight: 600 }}>Name</TableCell><TableCell>{testParseResult.parsed.name}</TableCell></TableRow>
                      <TableRow><TableCell sx={{ fontWeight: 600 }}>Email</TableCell><TableCell>{testParseResult.parsed.email}</TableCell></TableRow>
                      <TableRow><TableCell sx={{ fontWeight: 600 }}>Skills</TableCell><TableCell>{testParseResult.parsed.skills_count} categories</TableCell></TableRow>
                      <TableRow><TableCell sx={{ fontWeight: 600 }}>Experience</TableCell><TableCell>{testParseResult.parsed.experience_count} entries</TableCell></TableRow>
                    </>
                  )}
                  {testParseResult.error && (
                    <TableRow><TableCell sx={{ fontWeight: 600 }}>Error</TableCell><TableCell sx={{ color: 'error.main' }}>{testParseResult.error}</TableCell></TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </CardContent>
      </Card>

      {/* Available Models Card with inline selection */}
      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6">Available Models</Typography>
            <Button startIcon={<RefreshIcon />} onClick={load}>Refresh</Button>
          </Box>
          {models.length === 0 ? (
            <Alert severity="info">No models discovered. Ensure the OmniRoute endpoint is reachable.</Alert>
          ) : (
            <TableContainer component={Paper} variant="outlined">
              <Table size="small">
                <TableBody>
                  {models.map((m) => (
                    <TableRow key={m.id}
                      hover sx={{ cursor: 'pointer' }}
                      onClick={() => selectModel(m.id)}
                      selected={m.id === editModel}>
                      <TableCell>{m.id === editModel ? '✓' : ''}</TableCell>
                      <TableCell sx={{ fontWeight: m.id === editModel ? 700 : 400 }}>{m.id}</TableCell>
                      <TableCell>{m.owned_by}</TableCell>
                      <TableCell>
                        {m.id === editModel ? <Chip size="small" color="primary" label="Selected" /> : null}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </CardContent>
      </Card>

      <Snackbar open={!!snack} autoHideDuration={4000} onClose={() => setSnack(null)}
        message={snack} anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }} />
    </Box>
  );
}
