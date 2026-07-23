import { Chip } from '@mui/material';
import CheckCircleOutlined from '@mui/icons-material/CheckCircleOutlined';
import ScheduleOutlined from '@mui/icons-material/ScheduleOutlined';
import CancelOutlined from '@mui/icons-material/CancelOutlined';
import HourglassEmptyOutlined from '@mui/icons-material/HourglassEmptyOutlined';

interface StatusBadgeProps {
  status: string;
  label?: string;
}

const statusConfig: Record<string, { color: 'success' | 'warning' | 'error' | 'info' | 'default'; icon: React.ReactElement }> = {
  applied: { color: 'info', icon: <ScheduleOutlined /> },
  interviewing: { color: 'warning', icon: <HourglassEmptyOutlined /> },
  offered: { color: 'success', icon: <CheckCircleOutlined /> },
  rejected: { color: 'error', icon: <CancelOutlined /> },
  accepted: { color: 'success', icon: <CheckCircleOutlined /> },
  draft: { color: 'default', icon: <HourglassEmptyOutlined /> },
  active: { color: 'success', icon: <CheckCircleOutlined /> },
  pending: { color: 'warning', icon: <ScheduleOutlined /> },
  archived: { color: 'default', icon: <CancelOutlined /> },
};

function StatusBadge({ status, label }: StatusBadgeProps) {
  const config = statusConfig[status.toLowerCase()] || { color: 'default' as const, icon: undefined };
  return (
    <Chip
      icon={config.icon}
      label={label || status}
      size="small"
      color={config.color}
      variant="outlined"
      sx={{ borderRadius: 1, textTransform: 'capitalize' }}
    />
  );
}

export default StatusBadge;
