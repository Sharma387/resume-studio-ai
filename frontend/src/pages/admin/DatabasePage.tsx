import { useState, useEffect, useCallback } from 'react';
import {
  Box, Grid, Card, CardContent, Typography, Button, Alert, CircularProgress,
  Table, TableBody, TableCell, TableContainer, TableRow, Paper, Chip, Divider,
} from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import RefreshIcon from '@mui/icons-material/Refresh';
import { fetchDatabaseStatus, validateDatabase } from '../../services/adminService';
import type { DatabaseStatus, DatabaseValidation } from '../../types/admin';

export default function DatabasePage() {
  const [status, setStatus] = useState<DatabaseStatus | null>(null);
  const [validation, setValidation] = useState<DatabaseValidation | null>(null);
  const [loading, setLoading] = useState(true);
  const [validating, setValidating] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const s = await fetchDatabaseStatus();
      setStatus(s);
    } catch { /* ignore */ }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const runValidation = async () => {
    setValidating(true);
    setValidation(null);
    try {
      const v = await validateDatabase();
      setValidation(v);
    } catch { /* ignore */ }
    setValidating(false);
  };

  if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}><CircularProgress /></Box>;

  return (
    <Box>
      <Typography variant="h5" sx={{ fontWeight: 700, mb: 3 }}>Database Diagnostics</Typography>

      <Grid container spacing={3}>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>Status</Typography>
              <TableContainer component={Paper} variant="outlined">
                <Table size="small">
                  <TableBody>
                    <TableRow><TableCell sx={{ fontWeight: 600 }}>Backend</TableCell><TableCell><Chip size="small" label={status?.backend ?? 'N/A'} color={status?.backend === 'postgres' ? 'primary' : 'default'} /></TableCell></TableRow>
                    <TableRow><TableCell sx={{ fontWeight: 600 }}>Migration</TableCell><TableCell>{status?.migration ?? 'N/A'}</TableCell></TableRow>
                    <TableRow><TableCell sx={{ fontWeight: 600 }}>Pool Size</TableCell><TableCell>{status?.pool.size}</TableCell></TableRow>
                    <TableRow><TableCell sx={{ fontWeight: 600 }}>Pool Overflow</TableCell><TableCell>{status?.pool.overflow}</TableCell></TableRow>
                    <TableRow><TableCell sx={{ fontWeight: 600 }}>Pool Timeout</TableCell><TableCell>{status?.pool.timeout}s</TableCell></TableRow>
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
                <Button variant="contained" startIcon={<PlayArrowIcon />} onClick={runValidation} disabled={validating}>
                  {validating ? 'Validating...' : 'Validate Database'}
                </Button>
              </Box>
              {validation && (
                <Box>
                  <Chip size="small" color={validation.valid ? 'success' : 'error'} label={validation.valid ? 'All Checks Passed' : 'Some Checks Failed'} sx={{ mb: 2 }} />
                  <TableContainer component={Paper} variant="outlined">
                    <Table size="small">
                      <TableBody>
                        {validation.checks.map((c) => (
                          <TableRow key={c.name}>
                            <TableCell sx={{ fontWeight: 600 }}>{c.name}</TableCell>
                            <TableCell><Chip size="small" color={c.status === 'ok' ? 'success' : c.status === 'warn' ? 'warning' : 'error'} label={c.status} /></TableCell>
                            <TableCell>{c.detail ?? ''}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 2 }}>Table Counts</Typography>
          <Grid container spacing={2}>
            {Object.entries(status?.table_counts ?? {}).map(([table, count]) => (
              <Grid key={table} size={{ xs: 6, sm: 4, md: 3 }}>
                <Card variant="outlined">
                  <CardContent>
                    <Typography variant="caption" color="text.secondary">{table}</Typography>
                    <Typography variant="h6" sx={{ fontWeight: 700 }}>{count ?? '—'}</Typography>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </CardContent>
      </Card>
    </Box>
  );
}
