import type { ReactNode } from 'react';
import { Card, CardContent, Typography, Box } from '@mui/material';

interface FeatureCardProps {
  icon: ReactNode;
  title: string;
  description: string;
}

function FeatureCard({ icon, title, description }: FeatureCardProps) {
  return (
    <Card
      sx={{
        p: 2.5,
        transition: 'all 0.3s ease',
        animation: 'fadeIn 0.6s ease-out both',
        '&:hover': {
          transform: 'translateY(-4px)',
          boxShadow: '0 20px 60px rgba(124, 77, 255, 0.15)',
          borderColor: 'primary.main',
        },
      }}
    >
      <CardContent sx={{ p: 0, '&:last-child': { pb: 0 } }}>
        <Box
          sx={{
            width: 44,
            height: 44,
            borderRadius: 2,
            background: 'linear-gradient(135deg, rgba(124,77,255,0.15) 0%, rgba(0,229,255,0.15) 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            mb: 1.5,
          }}
        >
          {icon}
        </Box>
        <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 0.5, color: 'text.primary' }}>
          {title}
        </Typography>
        <Typography variant="body2" sx={{ color: 'text.secondary', lineHeight: 1.6 }}>
          {description}
        </Typography>
      </CardContent>
    </Card>
  );
}

export default FeatureCard;
