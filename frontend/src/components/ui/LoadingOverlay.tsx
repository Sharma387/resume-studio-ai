import { Box, CircularProgress, Typography } from '@mui/material';

interface LoadingOverlayProps {
  message?: string;
}

function LoadingOverlay({ message }: LoadingOverlayProps) {
  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        py: 8,
        gap: 2,
      }}
    >
      <CircularProgress size={40} />
      {message && (
        <Typography variant="body2" sx={{ color: 'text.secondary' }}>
          {message}
        </Typography>
      )}
    </Box>
  );
}

export default LoadingOverlay;
