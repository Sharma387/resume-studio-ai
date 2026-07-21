import { useState } from 'react';
import {
  Box,
  Typography,
  Card,
  Chip,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  CircularProgress,
  Alert,
  Divider,
} from '@mui/material';
import LightbulbOutlined from '@mui/icons-material/LightbulbOutlined';
import PreviewOutlined from '@mui/icons-material/PreviewOutlined';
import CheckCircleOutlined from '@mui/icons-material/CheckCircleOutlined';
import type { Recommendation } from '../../types/match';
import type { Resume } from '../../types/resume';
import { previewSuggestion, applySuggestion } from '../../services/resumeService';

interface RecommendationsListProps {
  recommendations: Recommendation[];
  resumeId: string;
  onApplied: () => void;
}

const priorityColor: Record<string, 'error' | 'warning' | 'default'> = {
  high: 'error',
  medium: 'warning',
  low: 'default',
};

function RecommendationsList({ recommendations, resumeId, onApplied }: RecommendationsListProps) {
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewData, setPreviewData] = useState<{ original: Resume; modified: Resume } | null>(null);
  const [activeRec, setActiveRec] = useState<Recommendation | null>(null);
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState('');

  const handlePreview = async (r: Recommendation) => {
    setLoading(`preview-${r.message}`);
    setError('');
    setActiveRec(r);
    try {
      const res = await previewSuggestion(resumeId, r.section, r.message, r.suggestion);
      setPreviewData(res.data);
      setPreviewOpen(true);
    } catch {
      setError('Failed to preview suggestion');
    } finally {
      setLoading(null);
    }
  };

  const handleApply = async (r: Recommendation) => {
    setLoading(`apply-${r.message}`);
    setError('');
    try {
      await applySuggestion(resumeId, r.section, r.message, r.suggestion);
      setPreviewOpen(false);
      setActiveRec(null);
      onApplied();
    } catch {
      setError('Failed to apply suggestion');
    } finally {
      setLoading(null);
    }
  };

  if (recommendations.length === 0) return null;

  const changedFields = previewData
    ? (Object.keys(previewData.modified) as (keyof Resume)[]).filter(
        (k) => JSON.stringify(previewData.modified[k]) !== JSON.stringify(previewData.original[k]),
      )
    : [];

  return (
    <Box>
      <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1.5, display: 'flex', alignItems: 'center', gap: 0.5 }}>
        <LightbulbOutlined fontSize="small" /> AI Recommendations
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 1.5, borderRadius: 2 }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}

      {recommendations.map((r, i) => (
        <Card key={i} sx={{ p: 2, mb: 1.5 }}>
          <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}>
            <Box sx={{ flex: 1 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5, flexWrap: 'wrap' }}>
                <Chip label={r.priority} size="small" color={priorityColor[r.priority]} sx={{ borderRadius: 1, textTransform: 'capitalize', fontSize: '0.7rem' }} />
                <Typography variant="caption" sx={{ color: 'text.secondary', textTransform: 'uppercase', fontWeight: 600 }}>
                  {r.section}
                </Typography>
              </Box>
              <Typography variant="body2" sx={{ color: 'text.primary', lineHeight: 1.5 }}>
                {r.message}
              </Typography>
              {r.suggestion && (
                <Typography variant="caption" sx={{ color: 'text.secondary', mt: 0.5, display: 'block', fontStyle: 'italic' }}>
                  💡 {r.suggestion}
                </Typography>
              )}
              <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
                <Button
                  size="small"
                  variant="outlined"
                  startIcon={loading === `preview-${r.message}` ? <CircularProgress size={14} /> : <PreviewOutlined />}
                  onClick={() => handlePreview(r)}
                  disabled={loading !== null}
                  sx={{ textTransform: 'none', borderRadius: 1.5 }}
                >
                  Preview
                </Button>
                <Button
                  size="small"
                  variant="contained"
                  startIcon={loading === `apply-${r.message}` ? <CircularProgress size={14} /> : <CheckCircleOutlined />}
                  onClick={() => handleApply(r)}
                  disabled={loading !== null}
                  sx={{ textTransform: 'none', borderRadius: 1.5 }}
                >
                  Apply
                </Button>
              </Box>
            </Box>
          </Box>
        </Card>
      ))}

      <Dialog open={previewOpen} onClose={() => setPreviewOpen(false)} maxWidth="md" fullWidth
        slotProps={{
          paper: {
            sx: { bgcolor: (t) => (t.palette.mode === 'dark' ? '#1e1e2e' : '#ffffff') },
          },
        }}>
        <DialogTitle sx={{ fontWeight: 700 }}>Preview Changes</DialogTitle>
        <DialogContent>
          {previewData && (
            <Box>
              <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1, color: 'warning.main' }}>
                Fields to be changed ({changedFields.length})
              </Typography>
              <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mb: 2 }}>
                {changedFields.map((f) => (
                  <Chip key={f} label={f} size="small" color="warning" variant="outlined" sx={{ borderRadius: 1 }} />
                ))}
              </Box>
              <Divider sx={{ mb: 2 }} />
              <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>Current</Typography>
              <Box
                sx={{
                  bgcolor: 'rgba(244,67,54,0.05)',
                  borderRadius: 2,
                  p: 1.5,
                  mb: 2,
                  fontFamily: 'monospace',
                  fontSize: '0.8rem',
                  whiteSpace: 'pre-wrap',
                  maxHeight: 200,
                  overflow: 'auto',
                }}
              >
                {JSON.stringify(
                  Object.fromEntries(changedFields.map((f: string) => [f, previewData!.original[f as keyof Resume]])),
                  null,
                  2,
                )}
              </Box>
              <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>Proposed</Typography>
              <Box
                sx={{
                  bgcolor: 'rgba(76,175,80,0.05)',
                  borderRadius: 2,
                  p: 1.5,
                  fontFamily: 'monospace',
                  fontSize: '0.8rem',
                  whiteSpace: 'pre-wrap',
                  maxHeight: 200,
                  overflow: 'auto',
                }}
              >
                {JSON.stringify(
                  Object.fromEntries(changedFields.map((f: string) => [f, previewData!.modified[f as keyof Resume]])),
                  null,
                  2,
                )}
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setPreviewOpen(false)} sx={{ textTransform: 'none', borderRadius: 2 }}>
            Cancel
          </Button>
          <Button
            variant="contained"
            color="success"
            startIcon={loading?.startsWith('apply') ? <CircularProgress size={16} /> : <CheckCircleOutlined />}
            onClick={() => activeRec && handleApply(activeRec)}
            disabled={loading !== null || !activeRec}
            sx={{ textTransform: 'none', borderRadius: 2 }}
          >
            Accept Changes
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default RecommendationsList;
