import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  TextField,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Alert,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  IconButton,
} from '@mui/material';
import AutoAwesomeOutlined from '@mui/icons-material/AutoAwesomeOutlined';
import EditOutlined from '@mui/icons-material/EditOutlined';
import SaveOutlined from '@mui/icons-material/SaveOutlined';
import DownloadOutlined from '@mui/icons-material/DownloadOutlined';
import ContentCopyOutlined from '@mui/icons-material/ContentCopyOutlined';
import DeleteOutlined from '@mui/icons-material/DeleteOutlined';
import ReplayOutlined from '@mui/icons-material/ReplayOutlined';
import type { CoverLetter, CoverLetterRequest } from '../../types/cover_letter';

import API_URL from "../../config";

interface CoverLetterSectionProps {
  resumeId: string;
}

function CoverLetterSection({ resumeId }: CoverLetterSectionProps) {
  const [jd, setJd] = useState('');
  const [company, setCompany] = useState('');
  const [role, setRole] = useState('');
  const [manager, setManager] = useState('');
  const [tone, setTone] = useState<CoverLetterRequest['tone']>('professional');
  const [generating, setGenerating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);

  const [currentLetter, setCurrentLetter] = useState<CoverLetter | null>(null);
  const [letters, setLetters] = useState<CoverLetter[]>([]);
  const [editMode, setEditMode] = useState(false);
  const [editContent, setEditContent] = useState('');

  useEffect(() => { fetch(`${API_URL}/resume/${resumeId}/cover-letters`)
      .then((r) => r.json())
      .then((data) => setLetters(data.data || []))
      .catch(() => {}); }, [resumeId]);

  const handleGenerate = async () => {
    if (!jd.trim()) return;
    setGenerating(true);
    setError('');
    try {
      const res = await fetch(`${API_URL}/resume/${resumeId}/cover-letter`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_description: jd, company_name: company || null, role_title: role || null, hiring_manager: manager || null, tone }),
      });
      if (!res.ok) throw new Error('Generation failed');
      const data = await res.json();
      setCurrentLetter(data.data);
      setEditContent(data.data.content);
      setEditMode(false);
      refreshLetters();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Cover letter generation failed');
    } finally {
      setGenerating(false);
    }
  };

  const refreshLetters = () => {
    fetch(`${API_URL}/resume/${resumeId}/cover-letters`)
      .then((r) => r.json())
      .then((data) => setLetters(data.data || []))
      .catch(() => {});
  };

  const handleSave = async () => {
    if (!currentLetter) return;
    setSaving(true);
    try {
      const res = await fetch(`${API_URL}/resume/${resumeId}/cover-letter/${currentLetter.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...currentLetter, content: editContent }),
      });
      if (!res.ok) throw new Error('Save failed');
      const data = await res.json();
      setCurrentLetter(data.data);
      setEditMode(false);
      refreshLetters();
    } catch {
      setError('Failed to save');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    await fetch(`${API_URL}/resume/${resumeId}/cover-letter/${id}`, { method: 'DELETE' });
    if (currentLetter?.id === id) setCurrentLetter(null);
    refreshLetters();
  };

  const handleCopy = async () => {
    if (!currentLetter) return;
    try {
      await navigator.clipboard.writeText(currentLetter.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {}
  };

  const handleSelect = (l: CoverLetter) => {
    setCurrentLetter(l);
    setEditContent(l.content);
    setEditMode(false);
  };

  const handleRegenerate = async () => {
    if (!currentLetter) return;
    setGenerating(true);
    try {
      const res = await fetch(`${API_URL}/resume/${resumeId}/cover-letter/${currentLetter.id}/regenerate`, { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        setCurrentLetter(data.data);
        setEditContent(data.data.content);
        refreshLetters();
      }
    } catch {
      setError('Regeneration failed');
    } finally {
      setGenerating(false);
    }
  };

  return (
    <Box>
      <Typography variant="h6" sx={{ fontWeight: 600, mb: 0.5, color: 'text.primary' }}>
        Cover Letter Generator
      </Typography>
      <Typography variant="body2" sx={{ color: 'text.secondary', mb: 3 }}>
        Generate a personalized cover letter from your resume and a job description.
      </Typography>

      <Card sx={{ p: 2.5, mb: 3 }}>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
          <TextField label="Job Description" value={jd} onChange={(e) => setJd(e.target.value)} multiline rows={4} fullWidth required />
          <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap' }}>
            <TextField label="Company (optional)" value={company} onChange={(e) => setCompany(e.target.value)} size="small" sx={{ flex: 1 }} />
            <TextField label="Role (optional)" value={role} onChange={(e) => setRole(e.target.value)} size="small" sx={{ flex: 1 }} />
            <TextField label="Hiring Manager (optional)" value={manager} onChange={(e) => setManager(e.target.value)} size="small" sx={{ flex: 1 }} />
            <FormControl size="small" sx={{ minWidth: 140 }}>
              <InputLabel>Tone</InputLabel>
              <Select value={tone} label="Tone" onChange={(e) => setTone(e.target.value as CoverLetterRequest['tone'])}>
                <MenuItem value="professional">Professional</MenuItem>
                <MenuItem value="enthusiastic">Enthusiastic</MenuItem>
                <MenuItem value="formal">Formal</MenuItem>
                <MenuItem value="concise">Concise</MenuItem>
              </Select>
            </FormControl>
          </Box>
          <Button variant="contained" startIcon={generating ? <CircularProgress size={16} /> : <AutoAwesomeOutlined />}
            onClick={handleGenerate} disabled={generating || !jd.trim()}
            sx={{ textTransform: 'none', borderRadius: 2, alignSelf: 'flex-start' }}>
            {generating ? 'Generating...' : 'Generate Cover Letter'}
          </Button>
        </Box>
      </Card>

      {error && <Alert severity="error" sx={{ mb: 2, borderRadius: 2 }} onClose={() => setError('')}>{error}</Alert>}

      {currentLetter && (
        <Card sx={{ p: 2.5, mb: 2.5 }}>
          <CardContent sx={{ p: 0, '&:last-child': { pb: 0 } }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.5, flexWrap: 'wrap', gap: 1 }}>
              <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                <Chip label={currentLetter.tone} size="small" color="primary" variant="outlined" sx={{ borderRadius: 1 }} />
                {currentLetter.company_name && <Chip label={currentLetter.company_name} size="small" variant="outlined" sx={{ borderRadius: 1 }} />}
              </Box>
              <Box sx={{ display: 'flex', gap: 0.5 }}>
                <IconButton size="small" onClick={() => setEditMode(!editMode)} aria-label="Edit cover letter"><EditOutlined fontSize="small" /></IconButton>
                <IconButton size="small" onClick={handleCopy} aria-label="Copy to clipboard" sx={{ color: copied ? 'success.main' : undefined }}>
                  <ContentCopyOutlined fontSize="small" />
                </IconButton>
                <IconButton size="small" onClick={handleRegenerate} disabled={generating} aria-label="Regenerate"><ReplayOutlined fontSize="small" /></IconButton>
                <IconButton size="small" onClick={() => handleDelete(currentLetter.id)} color="error" aria-label="Delete cover letter"><DeleteOutlined fontSize="small" /></IconButton>
              </Box>
            </Box>

            {currentLetter.subject && (
              <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1, color: 'text.secondary' }}>
                Subject: {currentLetter.subject}
              </Typography>
            )}

            {editMode ? (
              <TextField multiline rows={12} value={editContent} onChange={(e) => setEditContent(e.target.value)} fullWidth sx={{ fontFamily: 'monospace', fontSize: '0.85rem', mb: 1 }} />
            ) : (
              <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', lineHeight: 1.7, color: 'text.primary', mb: 1 }}>
                {currentLetter.content}
              </Typography>
            )}

            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              {editMode && (
                <Button size="small" variant="contained" startIcon={saving ? <CircularProgress size={14} /> : <SaveOutlined />}
                  onClick={handleSave} disabled={saving} sx={{ textTransform: 'none', borderRadius: 1.5 }}>
                  Save
                </Button>
              )}
              <Button size="small" variant="outlined" startIcon={<DownloadOutlined />}
                component="a" href={`${API_URL}/resume/${resumeId}/cover-letter/${currentLetter.id}/pdf`} download
                sx={{ textTransform: 'none', borderRadius: 1.5 }}>
                Download PDF
              </Button>
            </Box>
          </CardContent>
        </Card>
      )}

      {letters.length > 0 && (
        <Box>
          <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>Previous Cover Letters</Typography>
          {letters.map((l) => (
            <Card key={l.id} sx={{ p: 1.5, mb: 1, cursor: 'pointer' }} onClick={() => handleSelect(l)}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Box>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>
                    {l.company_name || l.role_title || 'Cover Letter'} — {new Date(l.created_at).toLocaleDateString()}
                  </Typography>
                  <Typography variant="caption" sx={{ color: 'text.secondary' }}>{l.tone} · {l.content?.length || 0} chars</Typography>
                </Box>
                <IconButton size="small" color="error" aria-label="Delete cover letter" onClick={(e) => { e.stopPropagation(); handleDelete(l.id); }}>
                  <DeleteOutlined fontSize="small" />
                </IconButton>
              </Box>
            </Card>
          ))}
        </Box>
      )}
    </Box>
  );
}

export default CoverLetterSection;
