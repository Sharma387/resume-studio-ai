import { Box, Typography, CircularProgress } from '@mui/material';

interface ATSScoreGaugeProps {
  score: number;
}

function getColor(score: number): string {
  if (score >= 80) return '#4caf50';
  if (score >= 60) return '#ff9800';
  return '#f44336';
}

function getLabel(score: number): string {
  if (score >= 80) return 'Strong Match';
  if (score >= 60) return 'Moderate Match';
  if (score >= 40) return 'Weak Match';
  return 'Poor Match';
}

function ATSScoreGauge({ score }: ATSScoreGaugeProps) {
  const color = getColor(score);

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        py: 3,
      }}
    >
      <Box sx={{ position: 'relative', display: 'inline-flex', mb: 1.5 }}>
        <CircularProgress
          variant="determinate"
          value={100}
          size={140}
          thickness={4}
          sx={{ color: 'rgba(0,0,0,0.08)', position: 'absolute' }}
        />
        <CircularProgress
          variant="determinate"
          value={score}
          size={140}
          thickness={4}
          sx={{ color, transform: 'rotate(-90deg)' }}
        />
        <Box
          sx={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Typography variant="h3" sx={{ fontWeight: 700, color, lineHeight: 1 }}>
            {Math.round(score)}
          </Typography>
          <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 500 }}>
            / 100
          </Typography>
        </Box>
      </Box>
      <Typography
        variant="subtitle1"
        sx={{ fontWeight: 600, color, textTransform: 'uppercase', letterSpacing: 1, fontSize: '0.85rem' }}
      >
        {getLabel(score)}
      </Typography>
      <Typography variant="caption" sx={{ color: 'text.secondary', mt: 0.5 }}>
        ATS Readiness Score
      </Typography>
    </Box>
  );
}

export default ATSScoreGauge;
