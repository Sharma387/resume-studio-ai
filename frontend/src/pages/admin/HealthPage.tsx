import { useState, useEffect, useCallback } from 'react';
import {
  Box, Grid, Card, CardContent, Typography, Chip, CircularProgress, Alert, Button,
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import { fetchSystemHealth } from '../../services/adminService';
import type { SystemHealth } from '../../types/admin';

function HealthSection({ title, data }: { title: string; data: Record<string, unknown> }) {
  const status = String(data.status ?? 'unknown');
  const color = status === 'healthy' ? 'success' : status === 'warning' ? 'warning' : 'error';

  return (
    <Card sx={{ height: '100%', borderLeft: 4, borderColor: `${color}.main` }}>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>{title}</Typography>
          <Chip size="small" color={color as 'success' | 'warning' | 'error'} label={status} />
        </Box>
        {Object.entries(data).filter(([k]) => k !== 'status').map(([key, value]) => (
          <Box key={key} sx={{ display: 'flex', justifyContent: 'space-between', py: 0.5 }}>
            <Typography variant="body2" color="text.secondary" sx={{ textTransform: 'capitalize' }}>{key.replace(/_/g, ' ')}</Typography>
            <Typography variant="body2" sx={{ fontWeight: 600 }}>{String(value ?? '—')}</Typography>
          </Box>
        ))}
      </CardContent>
    </Card>
  );
}

export default function HealthPage() {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const h = await fetchSystemHealth();
      setHealth(h);
    } catch { /* ignore */ }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}><CircularProgress /></Box>;

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h5" sx={{ fontWeight: 700 }}>System Health</Typography>
        <Button startIcon={<RefreshIcon />} onClick={load}>Refresh</Button>
      </Box>
      {health ? (
        <Grid container spacing={3}>
          {Object.entries(health).map(([key, data]) => (
            <Grid key={key} size={{ xs: 12, sm: 6, lg: 3 }}>
              <HealthSection title={key.charAt(0).toUpperCase() + key.slice(1)} data={data as Record<string, unknown>} />
            </Grid>
          ))}
        </Grid>
      ) : (
        <Alert severity="info">Unable to load system health</Alert>
      )}
    </Box>
  );
}
