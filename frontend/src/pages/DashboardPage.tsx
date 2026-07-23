import { useState, useEffect } from 'react';
import { Box, Typography, Card, CardContent, Grid, Chip, CircularProgress } from '@mui/material';
import DescriptionOutlined from '@mui/icons-material/DescriptionOutlined';
import BusinessCenterOutlined from '@mui/icons-material/BusinessCenterOutlined';
import RecordVoiceOverOutlined from '@mui/icons-material/RecordVoiceOverOutlined';
import AutoAwesomeOutlined from '@mui/icons-material/AutoAwesomeOutlined';
import AnalyticsOutlined from '@mui/icons-material/AnalyticsOutlined';
import MailOutlined from '@mui/icons-material/MailOutlined';
import type { DashboardSummary } from '../types/workspace';

const API_URL = 'http://localhost:8000/api/v1';

function StatCard({ icon, label, value, color }: { icon: React.ReactNode; label: string; value: string | number; color?: string }) {
  return (
    <Card sx={{ p: 2, animation: 'fadeIn 0.4s ease-out' }}>
      <CardContent sx={{ p: 0, '&:last-child': { pb: 0 }, display: 'flex', alignItems: 'center', gap: 2 }}>
        <Box sx={{ width: 48, height: 48, borderRadius: 2, display: 'flex', alignItems: 'center', justifyContent: 'center', bgcolor: `${color || 'primary.main'}15`, color: color || 'primary.main' }}>
          {icon}
        </Box>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 700, lineHeight: 1.2 }}>{value}</Typography>
          <Typography variant="caption" sx={{ color: 'text.secondary' }}>{label}</Typography>
        </Box>
      </CardContent>
    </Card>
  );
}

function DashboardPage() {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_URL}/dashboard`)
      .then((r) => r.json())
      .then((res) => setData(res.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!data) {
    return <Typography sx={{ color: 'text.secondary', py: 4, textAlign: 'center' }}>Unable to load dashboard</Typography>;
  }

  return (
    <Box sx={{ animation: 'fadeIn 0.3s ease-out' }}>
      <Typography variant="h5" sx={{ fontWeight: 700, mb: 0.5 }}>Dashboard</Typography>
      <Typography variant="body2" sx={{ color: 'text.secondary', mb: 3 }}>Your career workspace at a glance</Typography>

      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid size={{ xs: 6, sm: 4, md: 2 }}>
          <StatCard icon={<DescriptionOutlined />} label="Resumes" value={data.resumes.total} color="#7c4dff" />
        </Grid>
        <Grid size={{ xs: 6, sm: 4, md: 2 }}>
          <StatCard icon={<BusinessCenterOutlined />} label="Active Apps" value={data.applications.active} color="#00b894" />
        </Grid>
        <Grid size={{ xs: 6, sm: 4, md: 2 }}>
          <StatCard icon={<RecordVoiceOverOutlined />} label="Interviews" value={data.interviews.total} color="#fdcb6e" />
        </Grid>
        <Grid size={{ xs: 6, sm: 4, md: 2 }}>
          <StatCard icon={<MailOutlined />} label="Cover Letters" value={data.cover_letters.total} color="#e17055" />
        </Grid>
        <Grid size={{ xs: 6, sm: 4, md: 2 }}>
          <StatCard icon={<AnalyticsOutlined />} label="ATS Avg" value={data.ats.average_score} color="#00cec9" />
        </Grid>
        <Grid size={{ xs: 6, sm: 4, md: 2 }}>
          <StatCard icon={<AutoAwesomeOutlined />} label="AI Suggestions" value={data.ai_suggestions.pending} color="#6c5ce7" />
        </Grid>
      </Grid>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card sx={{ p: 2 }}>
            <CardContent sx={{ p: 0, '&:last-child': { pb: 0 } }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1.5 }}>Application Status</Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                {Object.entries(data.applications.by_status).map(([status, count]) => (
                  <Box key={status} sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Chip label={status} size="small" variant="outlined" sx={{ borderRadius: 1, textTransform: 'capitalize' }} />
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>{count}</Typography>
                  </Box>
                ))}
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card sx={{ p: 2 }}>
            <CardContent sx={{ p: 0, '&:last-child': { pb: 0 } }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1.5 }}>Resume Health</Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="body2" sx={{ color: 'text.secondary' }}>Total Resumes</Typography>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>{data.resumes.total}</Typography>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="body2" sx={{ color: 'text.secondary' }}>With Summary</Typography>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>{data.resumes.with_summary}</Typography>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="body2" sx={{ color: 'text.secondary' }}>ATS Matches</Typography>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>{data.ats.total_matches}</Typography>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="body2" sx={{ color: 'text.secondary' }}>Pending AI Suggestions</Typography>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>{data.ai_suggestions.pending}</Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}

export default DashboardPage;
