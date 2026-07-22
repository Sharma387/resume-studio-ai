import { Box, Typography, Divider } from '@mui/material';

function Footer() {
  return (
    <Box
      component="footer"
      sx={{
        mt: 'auto',
        py: 3,
        px: { xs: 2, md: 4 },
        maxWidth: 1400,
        mx: 'auto',
        width: '100%',
      }}
    >
      <Divider sx={{ mb: 2.5, borderColor: (t) => (t.palette.mode === 'dark' ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)') }} />
      <Box
        sx={{
          display: 'flex',
          flexDirection: { xs: 'column', sm: 'row' },
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 1,
        }}
      >
        <Typography variant="caption" sx={{ color: 'text.secondary' }}>
          &copy; {new Date().getFullYear()} Resume Studio AI. All rights reserved.
        </Typography>
        <Typography variant="caption" sx={{ color: 'text.secondary' }}>
          v0.1.0
        </Typography>
      </Box>
    </Box>
  );
}

export default Footer;
