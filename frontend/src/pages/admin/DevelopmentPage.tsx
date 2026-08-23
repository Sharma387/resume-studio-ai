import { useState, useEffect, useCallback } from 'react';
import {
  Box, Grid, Card, CardContent, Typography, Chip, CircularProgress, Alert, Button,
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import { authFetch } from '../../services/authFetch';
import API_URL from '../../config';

interface DevStatus {
  development_mode: boolean;
  mock_authentication: boolean;
  mock_ai: boolean;
  mock_matching: boolean;
  runtime_storage_switch: boolean;
  runtime_feature_flags: boolean;
  configured: {
    debug: boolean;
    allow_mock_ai_data: boolean;
    storage_backend: string;
  };
}

function DevCard({ title, enabled }: { title: string; enabled: boolean }) {
  return (
    <Card sx={{ height: '100%' }}>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="body2" color="text.secondary">{title}</Typography>
          <Chip size="small" color={enabled ? 'warning' : 'default'} label={enabled ? 'Enabled' : 'Disabled'} />
        </Box>
      </CardContent>
    </Card>
  );
}

export default function DevelopmentPage() {
  const [status, setStatus] = useState<DevStatus | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await authFetch(`${API_URL}/admin/development`);
      const body = await res.json();
      if (body.success) setStatus(body.data);
    } catch { /* ignore */ }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}><CircularProgress /></Box>;

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h5" sx={{ fontWeight: 700 }}>Development Mode</Typography>
        <Button startIcon={<RefreshIcon />} onClick={load}>Refresh</Button>
      </Box>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Typography variant="h6">Development Mode</Typography>
            <Chip size="medium" color={status?.development_mode ? 'warning' : 'default'}
              label={status?.development_mode ? 'ACTIVE' : 'INACTIVE'} sx={{ fontWeight: 700 }} />
          </Box>
        </CardContent>
      </Card>

      <Typography variant="h6" sx={{ mb: 2 }}>Features</Typography>
      <Grid container spacing={2} sx={{ mb: 4 }}>
        <Grid size={{ xs: 12, sm: 6, md: 4 }}>
          <DevCard title="Mock Authentication" enabled={!!status?.mock_authentication} />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 4 }}>
          <DevCard title="Mock AI Parsing" enabled={!!status?.mock_ai} />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 4 }}>
          <DevCard title="Mock ATS Matching" enabled={!!status?.mock_matching} />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 4 }}>
          <DevCard title="Runtime Storage Switch" enabled={!!status?.runtime_storage_switch} />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 4 }}>
          <DevCard title="Runtime Feature Flags" enabled={!!status?.runtime_feature_flags} />
        </Grid>
      </Grid>

      <Typography variant="h6" sx={{ mb: 2 }}>Configuration</Typography>
      <Card>
        <CardContent>
          {status?.configured && (
            <Grid container spacing={2}>
              {Object.entries(status.configured).map(([key, value]) => (
                <Grid key={key} size={{ xs: 12, sm: 6, md: 4 }}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="caption" color="text.secondary">{key}</Typography>
                      <Typography variant="body1" sx={{ fontWeight: 600 }}>{String(value)}</Typography>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          )}
        </CardContent>
      </Card>
    </Box>
  );
}
