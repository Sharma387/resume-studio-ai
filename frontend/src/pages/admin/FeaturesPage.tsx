import { useState, useEffect, useCallback } from 'react';
import {
  Box, Card, CardContent, Typography, Switch, CircularProgress, Alert,
  Table, TableBody, TableCell, TableContainer, TableRow, Paper, Chip,
} from '@mui/material';
import { fetchFeatures, updateFeature } from '../../services/adminService';
import type { FeatureFlags } from '../../types/admin';

export default function FeaturesPage() {
  const [features, setFeatures] = useState<FeatureFlags | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const f = await fetchFeatures();
      setFeatures(f);
    } catch (e) {
      setError(String(e));
    }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const toggle = async (key: string, current: boolean) => {
    try {
      const updated = await updateFeature(key, !current);
      setFeatures(updated);
    } catch (e) {
      setError(String(e));
    }
  };

  if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}><CircularProgress /></Box>;

  const rows = features ? [
    { key: 'debug', label: 'Debug Mode', value: features.debug, mutable: false },
    { key: 'allow_mock_ai_data', label: 'Allow Mock AI Data', value: features.allow_mock_ai_data, mutable: true },
    { key: 'ai_enabled', label: 'AI Enabled', value: features.ai_enabled, mutable: false },
    { key: 'database_enabled', label: 'Database Enabled', value: features.database_enabled, mutable: false },
    { key: 'mock_mode', label: 'Mock Mode (debug + mock)', value: features.mock_mode, mutable: false },
    { key: 'storage_backend', label: 'Storage Backend', value: features.storage_backend, mutable: false },
  ] : [];

  return (
    <Box>
      <Typography variant="h5" sx={{ fontWeight: 700, mb: 3 }}>Feature Flags</Typography>
      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}

      <Card>
        <CardContent>
          <TableContainer component={Paper} variant="outlined">
            <Table>
              <TableBody>
                {rows.map((row) => (
                  <TableRow key={row.key}>
                    <TableCell sx={{ fontWeight: 600 }}>{row.label}</TableCell>
                    <TableCell>
                      {typeof row.value === 'boolean' ? (
                        <Switch
                          checked={row.value}
                          onChange={() => toggle(row.key, row.value)}
                          disabled={!row.mutable}
                          size="small"
                        />
                      ) : (
                        <Chip size="small" label={row.value} />
                      )}
                    </TableCell>
                    <TableCell>
                      {typeof row.value === 'boolean' ? (
                        <Chip size="small" color={row.value ? 'primary' : 'default'} label={row.value ? 'Enabled' : 'Disabled'} />
                      ) : null}
                    </TableCell>
                    <TableCell>
                      {!row.mutable && <Typography variant="caption" color="text.secondary">Read-only (set via .env)</Typography>}
                      {row.mutable && <Typography variant="caption" color="warning.main">Runtime change — restart not required</Typography>}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>
    </Box>
  );
}
