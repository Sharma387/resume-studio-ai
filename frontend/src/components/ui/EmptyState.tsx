import { Box, Typography, Button } from '@mui/material';
import InboxOutlined from '@mui/icons-material/InboxOutlined';
import type { ReactNode } from 'react';

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
}

function EmptyState({ icon, title, description, actionLabel, onAction }: EmptyStateProps) {
  return (
    <Box sx={{ textAlign: 'center', py: 8, px: 2 }}>
      <Box sx={{ color: 'text.disabled', mb: 2 }}>
        {icon || <InboxOutlined sx={{ fontSize: 64 }} />}
      </Box>
      <Typography variant="h6" sx={{ fontWeight: 600, mb: 1, color: 'text.secondary' }}>
        {title}
      </Typography>
      {description && (
        <Typography variant="body2" sx={{ color: 'text.disabled', mb: 3, maxWidth: 400, mx: 'auto' }}>
          {description}
        </Typography>
      )}
      {actionLabel && onAction && (
        <Button variant="contained" onClick={onAction} sx={{ textTransform: 'none', borderRadius: 2 }}>
          {actionLabel}
        </Button>
      )}
    </Box>
  );
}

export default EmptyState;
