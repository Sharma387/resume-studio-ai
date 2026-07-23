import { Box, Typography, Button } from '@mui/material';
import type { ReactNode } from 'react';

interface SectionHeaderProps {
  icon?: ReactNode;
  title: string;
  subtitle?: string;
  actionLabel?: string;
  onAction?: () => void;
}

function SectionHeader({ icon, title, subtitle, actionLabel, onAction }: SectionHeaderProps) {
  return (
    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2, flexWrap: 'wrap', gap: 1 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        {icon && <Box sx={{ color: 'primary.main', display: 'flex' }}>{icon}</Box>}
        <Box>
          <Typography variant="h6" sx={{ fontWeight: 600, lineHeight: 1.2 }}>{title}</Typography>
          {subtitle && <Typography variant="caption" sx={{ color: 'text.secondary' }}>{subtitle}</Typography>}
        </Box>
      </Box>
      {actionLabel && onAction && (
        <Button variant="outlined" size="small" onClick={onAction} sx={{ textTransform: 'none', borderRadius: 2 }}>
          {actionLabel}
        </Button>
      )}
    </Box>
  );
}

export default SectionHeader;
