import { Box, Skeleton, Card } from '@mui/material';

interface SkeletonLoaderProps {
  type?: 'card' | 'text' | 'form' | 'list';
  count?: number;
}

function SkeletonLoader({ type = 'card', count = 1 }: SkeletonLoaderProps) {
  if (type === 'text') {
    return (
      <Box>
        {Array.from({ length: count }).map((_, i) => (
          <Box key={i} sx={{ mb: 1 }}>
            <Skeleton variant="text" width={`${60 + Math.random() * 40}%`} />
            <Skeleton variant="text" width="100%" />
            <Skeleton variant="text" width="80%" />
          </Box>
        ))}
      </Box>
    );
  }

  if (type === 'form') {
    return (
      <Box>
        {Array.from({ length: count }).map((_, i) => (
          <Box key={i} sx={{ mb: 2 }}>
            <Skeleton variant="text" width={120} sx={{ mb: 0.5 }} />
            <Skeleton variant="rounded" height={40} />
          </Box>
        ))}
      </Box>
    );
  }

  if (type === 'list') {
    return (
      <Box>
        {Array.from({ length: count }).map((_, i) => (
          <Card key={i} sx={{ p: 2, mb: 1 }}>
            <Skeleton variant="text" width="60%" />
            <Skeleton variant="text" width="40%" />
          </Card>
        ))}
      </Box>
    );
  }

  return (
    <Box>
      {Array.from({ length: count }).map((_, i) => (
        <Card key={i} sx={{ p: 2, mb: 2 }}>
          <Skeleton variant="rounded" height={16} sx={{ mb: 1, width: '40%' }} />
          <Skeleton variant="rounded" height={12} sx={{ mb: 0.5 }} />
          <Skeleton variant="rounded" height={12} width="80%" />
        </Card>
      ))}
    </Box>
  );
}

export default SkeletonLoader;
