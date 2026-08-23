import { useState, useEffect, useCallback } from 'react';
import {
  Box, Grid, Card, CardContent, Typography, CircularProgress, Alert,
  Table, TableBody, TableCell, TableContainer, TableRow, Paper, Chip,
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import { IconButton } from '@mui/material';
import { fetchStorageStatus } from '../../services/adminService';
import type { StorageStatus } from '../../types/admin';

export default function StoragePage() {
  const [status, setStatus] = useState<StorageStatus | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const s = await fetchStorageStatus();
      setStatus(s);
    } catch { /* ignore */ }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}><CircularProgress /></Box>;

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h5" sx={{ fontWeight: 700 }}>Storage</Typography>
        <IconButton onClick={load}><RefreshIcon /></IconButton>
      </Box>

      <Grid container spacing={3}>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>Current Configuration</Typography>
              <TableContainer component={Paper} variant="outlined">
                <Table size="small">
                  <TableBody>
                    <TableRow><TableCell sx={{ fontWeight: 600 }}>Backend</TableCell><TableCell><Chip size="small" label={status?.backend} color={status?.backend === 'postgres' ? 'primary' : 'default'} /></TableCell></TableRow>
                    <TableRow><TableCell sx={{ fontWeight: 600 }}>JSON Files</TableCell><TableCell>{status?.json_files ?? 0}</TableCell></TableRow>
                    <TableRow><TableCell sx={{ fontWeight: 600 }}>Migrated to PG</TableCell><TableCell><Chip size="small" color={status?.migrated ? 'success' : 'warning'} label={status?.migrated ? 'Yes' : 'No'} /></TableCell></TableRow>
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>JSON Directory Breakdown</Typography>
              {status && Object.keys(status.dir_counts).length > 0 ? (
                <TableContainer component={Paper} variant="outlined">
                  <Table size="small">
                    <TableBody>
                      {Object.entries(status.dir_counts).map(([dir, count]) => (
                        <TableRow key={dir}>
                          <TableCell sx={{ fontWeight: 600 }}>{dir}</TableCell>
                          <TableCell>{count} files</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              ) : (
                <Alert severity="info">No JSON storage directories found</Alert>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
