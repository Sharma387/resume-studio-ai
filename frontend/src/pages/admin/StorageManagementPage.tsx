import { useState, useEffect, useCallback } from 'react';
import {
  Box, Grid, Card, CardContent, Typography, Button, Alert, CircularProgress, Chip,
  Table, TableBody, TableCell, TableContainer, TableRow, Paper,
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import { authFetch } from '../../services/authFetch';
import API_URL from '../../config';

export default function StorageManagementPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [validating, setValidating] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await authFetch(`${API_URL}/admin/storage/manage`);
      const body = await res.json();
      if (body.success) setData(body.data);
    } catch { /* ignore */ }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const runValidation = async () => {
    setValidating(true);
    try {
      const res = await authFetch(`${API_URL}/admin/storage/validate`, { method: 'POST' });
      await res.json();
      await load();
    } catch { /* ignore */ }
    setValidating(false);
  };

  if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}><CircularProgress /></Box>;

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h5" sx={{ fontWeight: 700 }}>Storage</Typography>
        <Button startIcon={<RefreshIcon />} onClick={load}>Refresh</Button>
      </Box>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
            <Typography variant="h6">Runtime Backend</Typography>
            <Chip size="medium" color="primary" label="PostgreSQL" sx={{ fontWeight: 700 }} />
            <Chip size="small" color="success" label="Production" />
          </Box>
          <Typography variant="body2" color="text.secondary">
            PostgreSQL is the only supported runtime storage backend.
          </Typography>
        </CardContent>
      </Card>

      <Grid container spacing={3}>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>Database Status</Typography>
              <TableContainer component={Paper} variant="outlined">
                <Table size="small">
                  <TableBody>
                    <TableRow><TableCell sx={{ fontWeight: 600 }}>Alembic Current</TableCell><TableCell>{data?.alembic_current ?? 'N/A'}</TableCell></TableRow>
                    <TableRow><TableCell sx={{ fontWeight: 600 }}>Alembic Head</TableCell><TableCell>{data?.alembic_head ?? 'N/A'}</TableCell></TableRow>
                    <TableRow><TableCell sx={{ fontWeight: 600 }}>Migration Required</TableCell><TableCell><Chip size="small" color={data?.migration_required ? 'error' : 'success'} label={data?.migration_required ? 'YES' : 'NO'} /></TableCell></TableRow>
                    <TableRow><TableCell sx={{ fontWeight: 600 }}>Pool Size</TableCell><TableCell>{data?.pool_size}</TableCell></TableRow>
                    <TableRow><TableCell sx={{ fontWeight: 600 }}>Pool Overflow</TableCell><TableCell>{data?.pool_overflow}</TableCell></TableRow>
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">Validation</Typography>
                <Button variant="outlined" size="small" startIcon={<PlayArrowIcon />} onClick={runValidation} disabled={validating}>
                  {validating ? 'Validating...' : 'Validate Database'}
                </Button>
              </Box>
              <Alert severity="info" sx={{ mt: 2 }}>
                Storage backend switching is not available. PostgreSQL is the only runtime backend.
              </Alert>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 2 }}>JSON Files (Migration Source Only)</Typography>
          {data?.json_files_available_for_migration ? (
            <Grid container spacing={2}>
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <Card variant="outlined"><CardContent>
                  <Typography variant="caption" color="text.secondary">Total JSON Files</Typography>
                  <Typography variant="h5" sx={{ fontWeight: 700 }}>{data.json_files_available_for_migration}</Typography>
                </CardContent></Card>
              </Grid>
              {Object.entries(data?.dir_counts || {}).map(([dir, count]) => (
                <Grid key={dir} size={{ xs: 6, sm: 4, md: 3 }}>
                  <Card variant="outlined"><CardContent>
                    <Typography variant="caption" color="text.secondary">{dir}</Typography>
                    <Typography variant="h6" sx={{ fontWeight: 700 }}>{count as number}</Typography>
                  </CardContent></Card>
                </Grid>
              ))}
            </Grid>
          ) : (
            <Alert severity="info">No JSON storage files found</Alert>
          )}
        </CardContent>
      </Card>
    </Box>
  );
}
