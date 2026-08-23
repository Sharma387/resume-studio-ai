import { useState, useEffect, useCallback } from 'react';
import { Box, Grid, Card, CardContent, Typography, Chip, CircularProgress, Alert, Button } from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import { fetchDashboard, fetchConfig } from '../../services/adminService';
import type { AdminDashboard, AdminConfig } from '../../types/admin';

function StatusBadge({ status }: { status: boolean | string }) {
  const ok = status === true || status === 'healthy' || status === 'production';
  const warn = status === 'warning';
  const color = ok ? 'success' : warn ? 'warning' : 'error';
  const label = typeof status === 'boolean' ? (status ? 'Connected' : 'Disconnected') : String(status);
  return <Chip size="small" color={color} label={label} />;
}

function StatCard({ title, value, badge }: { title: string; value: string | number | null | undefined; badge?: React.ReactNode }) {
  return (
    <Card sx={{ height: '100%' }}>
      <CardContent>
        <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 1 }}>{title}</Typography>
        <Typography variant="h5" sx={{ fontWeight: 700, mt: 1 }}>{value ?? '—'}</Typography>
        {badge && <Box sx={{ mt: 1 }}>{badge}</Box>}
      </CardContent>
    </Card>
  );
}

function formatUptime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return `${h}h ${m}m ${s}s`;
}

export default function DashboardPage() {
  const [dashboard, setDashboard] = useState<AdminDashboard | null>(null);
  const [config, setConfig] = useState<AdminConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [dash, cfg] = await Promise.all([fetchDashboard(), fetchConfig()]);
      setDashboard(dash);
      setConfig(cfg);
    } catch (e) {
      setError(String(e));
    }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}><CircularProgress /></Box>;
  if (error) return <Alert severity="error" action={<Button onClick={load}>Retry</Button>}>{error}</Alert>;
  if (!dashboard) return null;

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h5" sx={{ fontWeight: 700 }}>Dashboard</Typography>
        <Button startIcon={<RefreshIcon />} onClick={load}>Refresh</Button>
      </Box>

      <Grid container spacing={3}>
        <Grid size={{ xs: 12, sm: 6, md: 4, lg: 3 }}>
          <StatCard title="Version" value={dashboard.version} badge={<StatusBadge status={dashboard.environment} />} />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 4, lg: 3 }}>
          <StatCard title="Environment" value={dashboard.environment} />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 4, lg: 3 }}>
          <StatCard title="Storage Backend" value={dashboard.storage_backend} />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 4, lg: 3 }}>
          <StatCard title="AI Provider" value={dashboard.ai_provider} badge={<StatusBadge status={dashboard.ai_connected} />} />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 4, lg: 3 }}>
          <StatCard title="AI Model" value={dashboard.ai_model} />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 4, lg: 3 }}>
          <StatCard title="Database" value={dashboard.database_connected ? 'Connected' : 'JSON'} badge={<StatusBadge status={dashboard.database_connected} />} />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 4, lg: 3 }}>
          <StatCard title="Migration" value={dashboard.migration ?? 'N/A'} />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 4, lg: 3 }}>
          <StatCard title="Uptime" value={formatUptime(dashboard.uptime_seconds)} />
        </Grid>
      </Grid>

      <Typography variant="h6" sx={{ mt: 4, mb: 2, fontWeight: 600 }}>Table Counts</Typography>
      <Grid container spacing={2}>
        {Object.entries(dashboard.table_counts).map(([table, count]) => (
          <Grid key={table} size={{ xs: 6, sm: 4, md: 3, lg: 2 }}>
            <Card>
              <CardContent>
                <Typography variant="caption" color="text.secondary">{table}</Typography>
                <Typography variant="h6" sx={{ fontWeight: 700 }}>{count ?? '—'}</Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}
