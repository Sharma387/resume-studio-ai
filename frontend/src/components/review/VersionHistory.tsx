import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  CircularProgress,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import HistoryOutlined from '@mui/icons-material/HistoryOutlined';
import RestoreOutlined from '@mui/icons-material/RestoreOutlined';
import { fetchVersions, restoreVersion } from '../../services/resumeService';
import type { ResumeVersion } from '../../types/version';

interface VersionHistoryProps {
  resumeId: string;
  onRestored: () => void;
}

function VersionHistory({ resumeId, onRestored }: VersionHistoryProps) {
  const [versions, setVersions] = useState<ResumeVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [restoring, setRestoring] = useState<string | null>(null);
  const [confirmId, setConfirmId] = useState<string | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    setLoading(true);
    fetchVersions(resumeId)
      .then((res) => setVersions(res.data))
      .catch(() => setError('Failed to load history'))
      .finally(() => setLoading(false));
  }, [resumeId]);

  const handleRestore = async (versionId: string) => {
    setRestoring(versionId);
    setError('');
    try {
      await restoreVersion(resumeId, versionId);
      setConfirmId(null);
      onRestored();
    } catch {
      setError('Failed to restore version');
    } finally {
      setRestoring(null);
    }
  };

  if (loading) {
    return (
      <Box sx={{ textAlign: 'center', py: 4 }}>
        <CircularProgress size={32} />
      </Box>
    );
  }

  if (versions.length === 0) {
    return (
      <Box sx={{ textAlign: 'center', py: 4 }}>
        <Typography variant="body2" sx={{ color: 'text.secondary' }}>
          No version history yet. Versions are created when you apply AI suggestions.
        </Typography>
      </Box>
    );
  }

  return (
    <Box>
      {error && (
        <Alert severity="error" sx={{ mb: 2, borderRadius: 2 }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}

      <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 2, display: 'flex', alignItems: 'center', gap: 0.5 }}>
        <HistoryOutlined fontSize="small" /> Version History
      </Typography>

      {versions.map((v) => (
        <Card key={v.id} sx={{ p: 1.5, mb: 1 }}>
          <CardContent sx={{ p: 0, '&:last-child': { pb: 0 } }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 1 }}>
              <Box>
                <Typography variant="body2" sx={{ fontWeight: 600, color: 'text.primary' }}>
                  {v.label || `v${versions.indexOf(v) + 1}`}
                </Typography>
                <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                  {new Date(v.created_at).toLocaleString()}
                </Typography>
              </Box>
              <Button
                size="small"
                variant="outlined"
                color="warning"
                startIcon={restoring === v.id ? <CircularProgress size={14} /> : <RestoreOutlined />}
                onClick={() => setConfirmId(v.id)}
                disabled={restoring !== null}
                sx={{ textTransform: 'none', borderRadius: 1.5 }}
              >
                Restore
              </Button>
            </Box>
          </CardContent>
        </Card>
      ))}

      <Dialog open={confirmId !== null} onClose={() => setConfirmId(null)}>
        <DialogTitle sx={{ fontWeight: 700 }}>Restore Version?</DialogTitle>
        <DialogContent>
          <Typography variant="body2" sx={{ color: 'text.secondary' }}>
            This will replace your current resume with this saved version. Current changes will be preserved as a new version.
          </Typography>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setConfirmId(null)} sx={{ textTransform: 'none', borderRadius: 2 }}>
            Cancel
          </Button>
          <Button
            variant="contained"
            color="warning"
            onClick={() => confirmId && handleRestore(confirmId)}
            disabled={restoring !== null}
            sx={{ textTransform: 'none', borderRadius: 2 }}
          >
            Restore
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default VersionHistory;
