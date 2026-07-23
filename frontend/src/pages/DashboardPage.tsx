import { useState, useEffect } from 'react';
import { Box, Typography, Card, CardContent, Chip, CircularProgress } from '@mui/material';
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
    <Card sx={{ p: 2.5 }}>
      <CardContent sx={{ p: 0, '&:last-child': { pb: 0 }, display: 'flex', alignItems: 'center', gap: 2 }}>
        <Box sx={{ width: 48, height: 48, minWidth: 48, borderRadius: 2, display: 'flex', alignItems: 'center', justifyContent: 'center', bgcolor: `${color || 'primary.main'}15`, color: color || 'primary.main' }}>
          {icon}
        </Box>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 700, lineHeight: 1.2, mb: 0.25 }}>{value}</Typography>
          <Typography variant="body2" sx={{ color: 'text.secondary', whiteSpace: 'nowrap' }}>{label}</Typography>
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
    return <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}><CircularProgress /></Box>;
  }

  if (!data) {
    return <Typography sx={{ color: 'text.secondary', py: 4, textAlign: 'center' }}>Unable to load dashboard</Typography>;
  }

  return (
    <Box sx={{ animation: 'fadeIn 0.3s ease-out' }}>
      <Typography variant="h5" sx={{ fontWeight: 700, mb: 0.5 }}>Dashboard</Typography>
      <Typography variant="body2" sx={{ color: 'text.secondary', mb: 4 }}>Your career workspace at a glance</Typography>

      {/* Stat cards grid */}
      <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 3, mb: 4 }}>
        <StatCard icon={<DescriptionOutlined />} label="Resumes" value={data.resumes.total} color="#7c4dff" />
        <StatCard icon={<BusinessCenterOutlined />} label="Active Apps" value={data.applications.active} color="#00b894" />
        <StatCard icon={<RecordVoiceOverOutlined />} label="Interviews" value={data.interviews.total} color="#fdcb6e" />
        <StatCard icon={<MailOutlined />} label="Cover Letters" value={data.cover_letters.total} color="#e17055" />
        <StatCard icon={<AnalyticsOutlined />} label="ATS Avg" value={data.ats.average_score} color="#00cec9" />
        <StatCard icon={<AutoAwesomeOutlined />} label="Suggestions" value={data.ai_suggestions.pending} color="#6c5ce7" />
      </Box>

      {/* Bottom widgets grid */}
      <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: 3 }}>
        {/* Application Status */}
        <Card sx={{ p: 2.5 }}>
          <CardContent sx={{ p: 0, '&:last-child': { pb: 0 } }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 2 }}>Application Status</Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              {Object.entries(data.applications.by_status).map(([status, count]) => (
                <Box key={status} sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Chip label={status} size="small" variant="outlined" sx={{ borderRadius: 1, textTransform: 'capitalize' }} />
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>{count}</Typography>
                </Box>
              ))}
            </Box>
          </CardContent>
        </Card>

        {/* Resume Health */}
        <Card sx={{ p: 2.5 }}>
          <CardContent sx={{ p: 0, '&:last-child': { pb: 0 } }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 2 }}>Resume Health</Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
              <Row label="Total Resumes" value={data.resumes.total} />
              <Row label="With Summary" value={data.resumes.with_summary} />
              <Row label="ATS Matches" value={data.ats.total_matches} />
              <Row label="Pending Suggestions" value={data.ai_suggestions.pending} />
            </Box>
          </CardContent>
        </Card>
      </Box>
    </Box>
  );
}

function Row({ label, value }: { label: string; value: string | number }) {
  return (
    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
      <Typography variant="body2" sx={{ color: 'text.secondary' }}>{label}</Typography>
      <Typography variant="body2" sx={{ fontWeight: 600 }}>{value}</Typography>
    </Box>
  );
}

export default DashboardPage;
