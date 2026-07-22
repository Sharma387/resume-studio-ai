import { Box, TextField } from '@mui/material';
import type { Resume } from '../../types/resume';

interface SummarySectionProps {
  resume: Resume;
  onChange: (r: Resume) => void;
}

function SummarySection({ resume, onChange }: SummarySectionProps) {
  return (
    <Box>
      <TextField
        label="Professional Summary"
        value={resume.summary || ''}
        onChange={(e) => onChange({ ...resume, summary: e.target.value || undefined })}
        multiline
        rows={6}
        fullWidth
        placeholder="Write a brief professional summary..."
      />
    </Box>
  );
}

export default SummarySection;
