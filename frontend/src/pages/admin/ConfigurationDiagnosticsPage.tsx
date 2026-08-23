import { useState, useEffect, useCallback } from 'react';
import {
  Box, Grid, Card, CardContent, Typography, Chip, CircularProgress, Alert, Button,
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import { authFetch } from '../../services/authFetch';
import API_URL from '../../config';

interface Diagnostics {
  jwt: { configured: boolean; secure: boolean; length_requirement: number; algorithm: string; access_token_expiry_minutes: number; refresh_token_expiry_days: number };
  database: { configured: boolean; connected: boolean; migration_current: string | null };
  ai: { configured: boolean; connected: boolean; model: string; mock_mode: boolean };
  storage: { backend: string; json_backend_available: boolean; postgres_backend_available: boolean };
  environment: { debug: boolean; allow_mock_ai_data: boolean; development_mode: boolean; storage_backend: string };
}

function HealthCard({ title, checks, actions }: { title: string; checks: { label: string; healthy: boolean; warn?: boolean; message?: string }[]; actions?: React.ReactNode }) {
  const ok = checks.every(c => c.healthy);
  const warn = !ok && checks.some(c => c.warn);
  const color = ok ? 'success' : warn ? 'warning' : 'error';
  return (
    <Card sx={{ height: '100%', borderTop: 4, borderColor: `${color}.main` }}>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>{title}</Typography>
          <Chip size="small" color={color} label={ok ? 'Healthy' : warn ? 'Warning' : 'Critical'} />
        </Box>
        {checks.map(c => (
          <Box key={c.label} sx={{ display: 'flex', justifyContent: 'space-between', py: 0.5 }}>
            <Typography variant="body2" color="text.secondary">{c.label}</Typography>
            <Chip size="small" color={c.healthy ? 'success' : c.warn ? 'warning' : 'error'}
              label={c.healthy ? 'OK' : c.message || 'FAIL'} variant="outlined" />
          </Box>
        ))}
        {actions && <Box sx={{ mt: 2 }}>{actions}</Box>}
      </CardContent>
    </Card>
  );
}

export default function ConfigurationDiagnosticsPage() {
  const [data, setData] = useState<Diagnostics | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await authFetch(`${API_URL}/admin/configuration/diagnostics`);
      const body = await res.json();
      if (body.success) setData(body.data);
    } catch { /* ignore */ }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}><CircularProgress /></Box>;
  if (!data) return <Alert severity="error">Failed to load diagnostics</Alert>;

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h5" sx={{ fontWeight: 700 }}>Configuration Diagnostics</Typography>
        <Button startIcon={<RefreshIcon />} onClick={load}>Refresh</Button>
      </Box>

      <Grid container spacing={3}>
        {/* JWT */}
        <Grid size={{ xs: 12, md: 6, lg: 4 }}>
          <HealthCard title="JWT Security" checks={[
            { label: 'Secret Configured', healthy: data.jwt.configured, message: 'Missing JWT_SECRET_KEY' },
            { label: 'Secret Length', healthy: data.jwt.secure, message: `Min ${data.jwt.length_requirement} chars` },
            { label: 'Algorithm', healthy: true },
            { label: 'Access Token Expiry', healthy: true, message: `${data.jwt.access_token_expiry_minutes}m` },
            { label: 'Refresh Token Expiry', healthy: true, message: `${data.jwt.refresh_token_expiry_days}d` },
          ]} />
        </Grid>

        {/* Database */}
        <Grid size={{ xs: 12, md: 6, lg: 4 }}>
          <HealthCard title="Database" checks={[
            { label: 'DATABASE_URL Configured', healthy: data.database.configured },
            { label: 'Connected', healthy: data.database.connected, message: 'Disconnected' },
            { label: 'Migration Current', healthy: !!data.database.migration_current, warn: !data.database.migration_current && data.database.configured, message: data.database.migration_current || 'No migration' },
          ]} />
        </Grid>

        {/* AI */}
        <Grid size={{ xs: 12, md: 6, lg: 4 }}>
          <HealthCard title="AI Connection" checks={[
            { label: 'Endpoint Configured', healthy: data.ai.configured },
            { label: 'Connected', healthy: data.ai.connected, message: 'Disconnected' },
            { label: 'Model', healthy: true, message: data.ai.model },
            { label: 'Mock Mode', healthy: !data.ai.mock_mode, warn: data.ai.mock_mode, message: data.ai.mock_mode ? 'Active (debug)' : 'Disabled' },
          ]} />
        </Grid>

        {/* Storage */}
        <Grid size={{ xs: 12, md: 6, lg: 4 }}>
          <HealthCard title="Storage Backend" checks={[
            { label: 'Active Backend', healthy: true, message: data.storage.backend },
            { label: 'JSON Available', healthy: data.storage.json_backend_available },
            { label: 'PostgreSQL Available', healthy: data.storage.postgres_backend_available, warn: !data.storage.postgres_backend_available },
          ]} />
        </Grid>

        {/* Environment */}
        <Grid size={{ xs: 12, md: 6, lg: 4 }}>
          <HealthCard title="Environment" checks={[
            { label: 'Debug Mode', healthy: !data.environment.debug, warn: data.environment.debug, message: data.environment.debug ? 'ACTIVE' : 'Inactive' },
            { label: 'Mock AI Data', healthy: !data.environment.allow_mock_ai_data, warn: data.environment.allow_mock_ai_data },
            { label: 'Development Mode', healthy: !data.environment.development_mode, warn: data.environment.development_mode },
            { label: 'Storage Backend', healthy: true, message: data.environment.storage_backend },
          ]} />
        </Grid>
      </Grid>
    </Box>
  );
}
