import { useState } from 'react';
import {
  Box, Card, CardContent, Typography, Button, TextField, CircularProgress, Alert,
  Table, TableBody, TableCell, TableContainer, TableRow, Paper, Chip, Divider,
} from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import { testParseResume } from '../../services/adminService';
import type { ParseTestResult } from '../../types/admin';

export default function ParseTestPage() {
  const [text, setText] = useState('');
  const [result, setResult] = useState<ParseTestResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runParse = async () => {
    if (!text.trim()) return;
    setLoading(true);
    setResult(null);
    setError(null);
    try {
      const r = await testParseResume(text);
      setResult(r);
    } catch (e) {
      setError(String(e));
    }
    setLoading(false);
  };

  return (
    <Box>
      <Typography variant="h5" sx={{ fontWeight: 700, mb: 3 }}>Resume Parsing Test</Typography>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Paste resume text below to test parsing. No data is persisted.
          </Typography>
          <TextField
            multiline
            rows={8}
            fullWidth
            placeholder="Paste resume text here..."
            value={text}
            onChange={(e) => setText(e.target.value)}
            variant="outlined"
          />
          <Box sx={{ mt: 2, display: 'flex', gap: 2 }}>
            <Button variant="contained" startIcon={loading ? <CircularProgress size={18} /> : <PlayArrowIcon />} onClick={runParse} disabled={loading || !text.trim()}>
              {loading ? 'Parsing...' : 'Parse'}
            </Button>
          </Box>
        </CardContent>
      </Card>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {result && (
        <Card>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 2 }}>Result</Typography>
            <TableContainer component={Paper} variant="outlined" sx={{ mb: 2 }}>
              <Table size="small">
                <TableBody>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600 }}>Status</TableCell>
                    <TableCell><Chip size="small" color={result.success ? 'success' : 'error'} label={result.success ? 'Success' : 'Failed'} /></TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600 }}>Latency</TableCell>
                    <TableCell>{result.latency_ms ? `${result.latency_ms}ms` : '—'}</TableCell>
                  </TableRow>
                  {result.error && (
                    <TableRow>
                      <TableCell sx={{ fontWeight: 600 }}>Error</TableCell>
                      <TableCell sx={{ color: 'error.main' }}>{result.error}</TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>

            {result.parsed_resume && (
              <>
                <Typography variant="subtitle2" sx={{ mb: 1 }}>Parsed Resume (JSON)</Typography>
                <Paper variant="outlined" sx={{ p: 2, maxHeight: 400, overflow: 'auto', bgcolor: 'background.paper' }}>
                  <Typography component="pre" variant="caption" sx={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: 11 }}>
                    {JSON.stringify(result.parsed_resume, null, 2)}
                  </Typography>
                </Paper>
              </>
            )}
          </CardContent>
        </Card>
      )}
    </Box>
  );
}
