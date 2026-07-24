import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Card, CardContent, Typography } from '@mui/material';
import EditOutlined from '@mui/icons-material/EditOutlined';
import Header from '../components/Header';
import UploadZone from '../components/UploadZone';
import FeaturePanel from '../components/FeaturePanel';
import Footer from '../components/Footer';
import { useAuth } from '../contexts/AuthContext';
import { fetchResumes } from '../services/resumeService';

function Home() {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [existingResumeId, setExistingResumeId] = useState<string | null>(null);

  useEffect(() => {
    if (isAuthenticated) {
      fetchResumes()
        .then((res) => {
          if (res.data && res.data.length > 0) {
            setExistingResumeId(res.data[0].id || '');
          }
        })
        .catch(() => {});
    }
  }, [isAuthenticated]);

  return (
    <Box sx={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', position: 'relative', overflow: 'hidden' }}>
      <Box sx={{ position: 'fixed', top: '-20%', left: '-10%', width: '600px', height: '600px', borderRadius: '50%', background: 'radial-gradient(circle, rgba(124,77,255,0.12) 0%, transparent 70%)', pointerEvents: 'none', zIndex: 0 }} />
      <Box sx={{ position: 'fixed', bottom: '-20%', right: '-10%', width: '700px', height: '700px', borderRadius: '50%', background: 'radial-gradient(circle, rgba(0,229,255,0.08) 0%, transparent 70%)', pointerEvents: 'none', zIndex: 0 }} />

      <Header />

      <Box sx={{ flex: 1, display: 'flex', flexDirection: { xs: 'column', md: 'row' }, alignItems: 'center', gap: { xs: 6, md: 8, lg: 12 }, px: { xs: 2, sm: 4, md: 6, lg: 8 }, py: { xs: 4, md: 6 }, maxWidth: 1400, mx: 'auto', width: '100%', position: 'relative', zIndex: 1 }}>
        <Box sx={{ flex: 1, width: '100%', display: 'flex', flexDirection: 'column', gap: 2 }}>
          <UploadZone />

          {isAuthenticated && existingResumeId && (
            <Card
              sx={{
                p: 2,
                cursor: 'pointer',
                animation: 'fadeIn 0.5s ease-out',
                '&:hover': { transform: 'translateY(-2px)', boxShadow: 4 },
                transition: 'all 0.2s ease',
              }}
              onClick={() => navigate(`/review?file=${existingResumeId}`)}
            >
              <CardContent sx={{ p: 0, '&:last-child': { pb: 0 }, display: 'flex', alignItems: 'center', gap: 2 }}>
                <Box sx={{ width: 44, height: 44, borderRadius: 2, display: 'flex', alignItems: 'center', justifyContent: 'center', bgcolor: 'primary.main', color: 'primary.contrastText' }}>
                  <EditOutlined />
                </Box>
                <Box>
                  <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>Continue Editing</Typography>
                  <Typography variant="caption" sx={{ color: 'text.secondary' }}>Resume your previous work</Typography>
                </Box>
              </CardContent>
            </Card>
          )}
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
