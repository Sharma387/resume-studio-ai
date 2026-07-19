import { Box, Typography } from '@mui/material';
import AutoAwesomeOutlined from '@mui/icons-material/AutoAwesomeOutlined';
import AnalyticsOutlined from '@mui/icons-material/AnalyticsOutlined';
import BuildCircleOutlined from '@mui/icons-material/BuildCircleOutlined';
import FeatureCard from './FeatureCard';

const features = [
  {
    icon: <AutoAwesomeOutlined sx={{ color: 'primary.main', fontSize: 22 }} />,
    title: 'AI Resume Parser',
    description: 'Intelligently extracts and analyzes every section of your resume with advanced AI parsing technology.',
  },
  {
    icon: <AnalyticsOutlined sx={{ color: 'primary.main', fontSize: 22 }} />,
    title: 'ATS Optimization',
    description: 'Get real-time feedback to ensure your resume passes Applicant Tracking Systems with top scores.',
  },
  {
    icon: <BuildCircleOutlined sx={{ color: 'primary.main', fontSize: 22 }} />,
    title: 'Professional Resume Builder',
    description: 'Craft stunning, ATS-friendly resumes with AI-powered suggestions and modern templates.',
  },
];

function FeaturePanel() {
  return (
    <Box
      sx={{
        width: '100%',
        maxWidth: 400,
        mx: 'auto',
        animation: 'fadeIn 0.8s ease-out 0.3s both',
      }}
    >
      <Typography
        variant="h6"
        sx={{ fontWeight: 600, mb: 2.5, color: 'text.primary' }}
      >
        Features
      </Typography>

      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        {features.map((f, i) => (
          <Box key={f.title} sx={{ animationDelay: `${0.4 + i * 0.15}s` }}>
            <FeatureCard icon={f.icon} title={f.title} description={f.description} />
          </Box>
        ))}
      </Box>
    </Box>
  );
}

export default FeaturePanel;
