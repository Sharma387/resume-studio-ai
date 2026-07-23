import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  TextField,
  Button,
  Chip,
  Card,
  CardContent,
  CircularProgress,
  Alert,
} from '@mui/material';
import AutoAwesomeOutlined from '@mui/icons-material/AutoAwesomeOutlined';
import CheckCircleOutlined from '@mui/icons-material/CheckCircleOutlined';
import HighlightOffOutlined from '@mui/icons-material/HighlightOffOutlined';
import ReplayOutlined from '@mui/icons-material/ReplayOutlined';
import type { ResumeSuggestion, QuickActions } from '../../types/writer';

import API_URL from "../../config";
import { authFetch } from "../../services/authFetch";

interface WriterSectionProps {
  resumeId: string;
  onResumeUpdated: () => void;
}

function WriterSection({ resumeId, onResumeUpdated }: WriterSectionProps) {
  const [prompt, setPrompt] = useState('');
  const [quickActions, setQuickActions] = useState<QuickActions>({});
  const [suggestions, setSuggestions] = useState<ResumeSuggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  useEffect(() => {
    authFetch(`${API_URL}/resume/${resumeId}/writer/quick-actions`)
      .then((r) => r.json())
      .then((data) => setQuickActions(data.data || {}))
      .catch(() => {});
  }, [resumeId]);

  const handleSuggest = async (userPrompt: string) => {
    setPrompt(userPrompt);
    setLoading(true);
    setError('');
    try {
      const res = await authFetch(`${API_URL}/resume/${resumeId}/writer/suggest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: userPrompt }),
      });
      if (!res.ok) throw new Error('Failed to generate suggestions');
      const data = await res.json();
      setSuggestions(data.suggestions || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'AI Writer unavailable');
    } finally {
      setLoading(false);
    }
  };

  const handleAccept = async (s: ResumeSuggestion) => {
    setActionLoading(`accept-${s.id}`);
    try {
      await authFetch(`${API_URL}/resume/${resumeId}/writer/suggestions/${s.id}/accept`, { method: 'POST' });
      setSuggestions((prev) => prev.filter((x) => x.id !== s.id));
      onResumeUpdated();
    } catch {
      setError('Failed to accept suggestion');
    } finally {
      setActionLoading(null);
    }
  };

  const handleReject = async (s: ResumeSuggestion) => {
    setActionLoading(`reject-${s.id}`);
    try {
      await authFetch(`${API_URL}/resume/${resumeId}/writer/suggestions/${s.id}/reject`, { method: 'POST' });
      setSuggestions((prev) => prev.filter((x) => x.id !== s.id));
    } catch {
      setError('Failed to reject suggestion');
    } finally {
      setActionLoading(null);
    }
  };

  const handleRegenerate = async (s: ResumeSuggestion) => {
    setActionLoading(`regen-${s.id}`);
    try {
      const res = await authFetch(`${API_URL}/resume/${resumeId}/writer/suggestions/${s.id}/regenerate`, { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        setSuggestions((prev) => prev.map((x) => (x.id === s.id ? data.data : x)));
      }
    } catch {
      setError('Failed to regenerate');
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <Box>
      <Typography variant="h6" sx={{ fontWeight: 600, mb: 0.5, color: 'text.primary' }}>
        AI Resume Writer
      </Typography>
      <Typography variant="body2" sx={{ color: 'text.secondary', mb: 3 }}>
        Tell the AI what you'd like to improve. Suggestions are previewed before applying.
      </Typography>

      <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mb: 2 }}>
        {Object.entries(quickActions).map(([key, label]) => (
          <Chip
            key={key}
            label={label}
            size="small"
            variant="outlined"
            onClick={() => handleSuggest(label)}
            disabled={loading}
            sx={{ borderRadius: 1.5, cursor: 'pointer' }}
          />
        ))}
      </Box>

      <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
        <TextField
          fullWidth
          size="small"
          placeholder="Describe what you want to improve..."
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && prompt.trim()) handleSuggest(prompt.trim()); }}
          disabled={loading}
        />
        <Button
          variant="contained"
          startIcon={loading ? <CircularProgress size={16} /> : <AutoAwesomeOutlined />}
          onClick={() => handleSuggest(prompt.trim())}
          disabled={loading || !prompt.trim()}
          sx={{ textTransform: 'none', borderRadius: 2, whiteSpace: 'nowrap' }}
        >
          Generate
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2, borderRadius: 2 }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}

      {loading && (
        <Box sx={{ textAlign: 'center', py: 4 }}>
          <CircularProgress size={40} sx={{ mb: 1 }} />
          <Typography variant="body2" sx={{ color: 'text.secondary' }}>Analyzing your resume...</Typography>
        </Box>
      )}

      {suggestions.map((s) => (
        <Card key={s.id} sx={{ p: 2, mb: 1.5 }}>
          <CardContent sx={{ p: 0, '&:last-child': { pb: 0 } }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1, flexWrap: 'wrap' }}>
              <Chip label={s.suggestion_type} size="small" color="primary" variant="outlined" sx={{ borderRadius: 1, fontSize: '0.7rem' }} />
              <Chip label={s.section} size="small" variant="outlined" sx={{ borderRadius: 1, fontSize: '0.7rem' }} />
              <Typography variant="caption" sx={{ color: 'text.disabled' }}>{(s.confidence * 100).toFixed(0)}%</Typography>
            </Box>

            {s.original_text && (
              <Box sx={{ mb: 1 }}>
                <Typography variant="caption" sx={{ color: 'error.main', fontWeight: 600, display: 'block', mb: 0.3 }}>Original</Typography>
                <Box sx={{ bgcolor: 'rgba(244,67,54,0.06)', borderRadius: 1.5, p: 1, fontSize: '0.85rem', color: 'text.secondary', fontFamily: 'monospace' }}>
                  {s.original_text}
                </Box>
              </Box>
            )}

            <Box sx={{ mb: 1 }}>
              <Typography variant="caption" sx={{ color: 'success.main', fontWeight: 600, display: 'block', mb: 0.3 }}>Suggested</Typography>
              <Box sx={{ bgcolor: 'rgba(76,175,80,0.06)', borderRadius: 1.5, p: 1, fontSize: '0.85rem', color: 'text.primary', fontFamily: 'monospace' }}>
                {s.suggested_text}
              </Box>
            </Box>

            {s.reason && (
              <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mb: 1.5, fontStyle: 'italic' }}>
                💡 {s.reason}
              </Typography>
            )}

            <Box sx={{ display: 'flex', gap: 0.5 }}>
              <Button
                size="small"
                variant="contained"
                color="success"
                startIcon={actionLoading === `accept-${s.id}` ? <CircularProgress size={14} /> : <CheckCircleOutlined />}
                onClick={() => handleAccept(s)}
                disabled={actionLoading !== null}
                sx={{ textTransform: 'none', borderRadius: 1.5, fontSize: '0.75rem' }}
              >
                Accept
              </Button>
              <Button
                size="small"
                variant="outlined"
                color="error"
                startIcon={actionLoading === `reject-${s.id}` ? <CircularProgress size={14} /> : <HighlightOffOutlined />}
                onClick={() => handleReject(s)}
                disabled={actionLoading !== null}
                sx={{ textTransform: 'none', borderRadius: 1.5, fontSize: '0.75rem' }}
              >
                Reject
              </Button>
              <Button
                size="small"
                variant="text"
                startIcon={actionLoading === `regen-${s.id}` ? <CircularProgress size={14} /> : <ReplayOutlined />}
                onClick={() => handleRegenerate(s)}
                disabled={actionLoading !== null}
                sx={{ textTransform: 'none', borderRadius: 1.5, fontSize: '0.75rem' }}
              >
                Regenerate
              </Button>
            </Box>
          </CardContent>
        </Card>
      ))}

      {!loading && suggestions.length === 0 && prompt && (
        <Box sx={{ textAlign: 'center', py: 4 }}>
          <Typography variant="body2" sx={{ color: 'text.secondary' }}>
            No suggestions generated. Try a different prompt.
          </Typography>
        </Box>
      )}
    </Box>
  );
}

export default WriterSection;
