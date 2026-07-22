import { Box } from '@mui/material';
import Header from '../components/Header';
import UploadZone from '../components/UploadZone';
import FeaturePanel from '../components/FeaturePanel';
import Footer from '../components/Footer';

function Home() {
  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <Box
        sx={{
          position: 'fixed',
          top: '-20%',
          left: '-10%',
          width: '600px',
          height: '600px',
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(124,77,255,0.12) 0%, transparent 70%)',
          pointerEvents: 'none',
          zIndex: 0,
        }}
      />
      <Box
        sx={{
          position: 'fixed',
          bottom: '-20%',
          right: '-10%',
          width: '700px',
          height: '700px',
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(0,229,255,0.08) 0%, transparent 70%)',
          pointerEvents: 'none',
          zIndex: 0,
        }}
      />

      <Header />

      <Box
        sx={{
          flex: 1,
          display: 'flex',
          flexDirection: { xs: 'column', md: 'row' },
          alignItems: 'center',
          gap: { xs: 6, md: 8, lg: 12 },
          px: { xs: 2, sm: 4, md: 6, lg: 8 },
          py: { xs: 4, md: 6 },
          maxWidth: 1400,
          mx: 'auto',
          width: '100%',
          position: 'relative',
          zIndex: 1,
        }}
      >
        <Box sx={{ flex: 1, width: '100%' }}>
          <UploadZone />
        </Box>

        <Box sx={{ width: { xs: '100%', md: 'auto' }, flexShrink: 0 }}>
          <FeaturePanel />
        </Box>
      </Box>

      <Footer />
    </Box>
  );
}

export default Home;
