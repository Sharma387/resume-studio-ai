import { useState } from 'react';
import {
  Box,
  Typography,
  TextField,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Alert,
  Chip,
} from '@mui/material';
import TravelExploreOutlined from '@mui/icons-material/TravelExploreOutlined';
import { matchResume } from '../../services/resumeService';
import type { MatchResult } from '../../types/match';
import ATSScoreGauge from './ATSScoreGauge';
import SkillMatchList from './SkillMatchList';
import LoadingOverlay from '../ui/LoadingOverlay';
import RecommendationsList from './RecommendationsList';

interface MatchSectionProps {
  resumeId: string;
  onResumeUpdated?: () => void;
}

function MatchSection({ resumeId, onResumeUpdated }: MatchSectionProps) {
  const [jobDesc, setJobDesc] = useState('');
  const [jobTitle, setJobTitle] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<MatchResult | null>(null);
  const [error, setError] = useState('');

  const handleAnalyze = async () => {
    if (!jobDesc.trim()) return;
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const res = await matchResume(resumeId, jobDesc, jobTitle || undefined);
      setResult(res.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Match analysis failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box>
      <Typography variant="h6" sx={{ fontWeight: 600, mb: 0.5, color: 'text.primary' }}>
        ATS Job Match
      </Typography>
      <Typography variant="body2" sx={{ color: 'text.secondary', mb: 3 }}>
        Paste a job description to see how well your resume matches. Get AI-powered recommendations to improve your ATS score.
      </Typography>

      <Card sx={{ p: 2.5, mb: 3 }}>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <TextField
            label="Job Title (optional)"
            value={jobTitle}
            onChange={(e) => setJobTitle(e.target.value)}
            size="small"
            fullWidth
          />
          <TextField
            label="Job Description"
            value={jobDesc}
            onChange={(e) => setJobDesc(e.target.value)}
            multiline
            rows={6}
            fullWidth
            placeholder="Paste the full job description here..."
          />
          <Button
            variant="contained"
            size="large"
            startIcon={loading ? <CircularProgress size={18} /> : <TravelExploreOutlined />}
            onClick={handleAnalyze}
            disabled={loading || !jobDesc.trim()}
            sx={{
              py: 1.2,
              borderRadius: 2,
              textTransform: 'none',
              fontWeight: 600,
              alignSelf: 'flex-start',
            }}
          >
            {loading ? 'Analyzing...' : 'Analyze Match'}
          </Button>
        </Box>
      </Card>

      {error && (
        <Alert severity="error" sx={{ mb: 2, borderRadius: 2 }}>
          {error}
        </Alert>
      )}

      {loading && <LoadingOverlay message="Analyzing resume against job description..." />}

      {result && !loading && (
        <Box>
          <Card sx={{ p: 2.5, mb: 2.5 }}>
            <CardContent sx={{ p: 0, '&:last-child': { pb: 0 } }}>
              <Box sx={{ display: 'flex', flexDirection: { xs: 'column', md: 'row' }, gap: 3, alignItems: { md: 'center' } }}>
                <Box sx={{ flexShrink: 0 }}>
                  <ATSScoreGauge score={result.overall_score} />
                </Box>
                <Box sx={{ flex: 1 }}>
                  {result.job_title && (
                    <Chip
                      label={result.job_title}
                      size="small"
                      color="primary"
                      variant="outlined"
                      sx={{ mb: 1, borderRadius: 1 }}
                    />
                  )}
                  <Typography variant="body2" sx={{ color: 'text.secondary', lineHeight: 1.6 }}>
                    {result.summary}
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>

          {result.skill_matches.length > 0 && (
            <Card sx={{ p: 2.5, mb: 2.5 }}>
              <CardContent sx={{ p: 0, '&:last-child': { pb: 0 } }}>
                <SkillMatchList skillMatches={result.skill_matches} />
              </CardContent>
            </Card>
          )}

          {result.recommendations.length > 0 && (
            <Card sx={{ p: 2.5, mb: 2.5 }}>
              <CardContent sx={{ p: 0, '&:last-child': { pb: 0 } }}>
                <RecommendationsList recommendations={result.recommendations} resumeId={resumeId} onApplied={() => onResumeUpdated?.()} />
              </CardContent>
            </Card>
          )}
        </Box>
      )}
    </Box>
  );
}

export default MatchSection;
