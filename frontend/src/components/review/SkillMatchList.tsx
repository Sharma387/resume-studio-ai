import { Box, Typography, Chip } from '@mui/material';
import CheckCircleOutlined from '@mui/icons-material/CheckCircleOutlined';
import HighlightOffOutlined from '@mui/icons-material/HighlightOffOutlined';
import type { SkillMatch } from '../../types/match';

interface SkillMatchListProps {
  skillMatches: SkillMatch[];
}

function SkillMatchList({ skillMatches }: SkillMatchListProps) {
  const matched = skillMatches.filter((s) => s.matched);
  const missing = skillMatches.filter((s) => !s.matched);

  return (
    <Box>
      {matched.length > 0 && (
        <Box sx={{ mb: 2.5 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1, color: 'success.main', display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <CheckCircleOutlined fontSize="small" /> Matched Skills ({matched.length})
          </Typography>
          <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
            {matched.map((s) => (
              <Chip
                key={s.skill}
                label={s.skill}
                size="small"
                color="success"
                variant="outlined"
                sx={{ borderRadius: 1 }}
              />
            ))}
          </Box>
        </Box>
      )}

      {missing.length > 0 && (
        <Box>
          <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1, color: 'error.main', display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <HighlightOffOutlined fontSize="small" /> Missing Skills ({missing.length})
          </Typography>
          <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
            {missing.map((s) => (
              <Chip
                key={s.skill}
                label={s.skill}
                size="small"
                color="error"
                variant="outlined"
                sx={{ borderRadius: 1 }}
              />
            ))}
          </Box>
        </Box>
      )}
    </Box>
  );
}

export default SkillMatchList;
