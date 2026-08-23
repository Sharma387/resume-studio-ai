import { Navigate, useSearchParams } from 'react-router-dom';
import { Box, Alert, Button } from '@mui/material';

interface Props {
  children: React.ReactNode;
}

export default function ReviewGuard({ children }: Props) {
  const [searchParams] = useSearchParams();
  const fileParam = searchParams.get('file');

  if (!fileParam) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh', flexDirection: 'column', gap: 2 }}>
        <Alert severity="info" sx={{ maxWidth: 500 }}>
          Please upload and parse a resume before opening the review page.
        </Alert>
        <Button variant="contained" href="/">Go to Home</Button>
      </Box>
    );
  }

  return <>{children}</>;
}
