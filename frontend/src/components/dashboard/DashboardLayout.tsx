import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Box, Typography, IconButton, Avatar, Divider, useMediaQuery, useTheme, Drawer,
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import DashboardOutlined from '@mui/icons-material/DashboardOutlined';
import DescriptionOutlined from '@mui/icons-material/DescriptionOutlined';
import MailOutlined from '@mui/icons-material/MailOutlined';
import BusinessCenterOutlined from '@mui/icons-material/BusinessCenterOutlined';
import RecordVoiceOverOutlined from '@mui/icons-material/RecordVoiceOverOutlined';
import SettingsOutlined from '@mui/icons-material/SettingsOutlined';
import type { ReactNode } from 'react';

const SIDEBAR_WIDTH = 260;

interface NavItem {
  path: string;
  label: string;
  icon: React.ReactNode;
}

const navItems: NavItem[] = [
  { path: '/', label: 'Dashboard', icon: <DashboardOutlined /> },
  { path: '/resumes', label: 'Resumes', icon: <DescriptionOutlined /> },
  { path: '/cover-letters', label: 'Cover Letters', icon: <MailOutlined /> },
  { path: '/applications', label: 'Applications', icon: <BusinessCenterOutlined /> },
  { path: '/interview', label: 'Interview Prep', icon: <RecordVoiceOverOutlined /> },
  { path: '/settings', label: 'Settings', icon: <SettingsOutlined /> },
];

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const navigate = useNavigate();
  const location = useLocation();

  const isActive = (path: string) =>
    path === '/' ? location.pathname === '/' : location.pathname.startsWith(path);

  return (
    <Box
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        py: 2,
      }}
    >
      {/* Logo */}
      <Typography
        variant="h6"
        sx={{
          px: 3,
          mb: 3,
          fontWeight: 700,
          background: 'linear-gradient(135deg, #7c4dff, #00e5ff)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          letterSpacing: '-0.5px',
        }}
      >
        Resume Studio AI
      </Typography>

      <Divider sx={{ mb: 2 }} />

      {/* Navigation */}
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5, px: 1.5, flex: 1, overflow: 'auto' }}>
        {navItems.map((item) => {
          const active = isActive(item.path);
          return (
            <Box
              key={item.path}
              onClick={() => { navigate(item.path); onNavigate?.(); }}
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 1.5,
                px: 1.5,
                py: 1.2,
                borderRadius: 2,
                cursor: 'pointer',
                color: active ? 'primary.contrastText' : 'text.secondary',
                bgcolor: active ? 'primary.main' : 'transparent',
                '&:hover': {
                  bgcolor: active ? 'primary.dark' : 'action.hover',
                  color: active ? 'primary.contrastText' : 'text.primary',
                },
                transition: 'all 0.15s ease',
              }}
            >
              <Box sx={{ display: 'flex', fontSize: 20 }}>{item.icon}</Box>
              <Typography variant="body2" sx={{ fontWeight: active ? 600 : 400 }}>
                {item.label}
              </Typography>
            </Box>
          );
        })}
      </Box>

      {/* User/Profile */}
      <Divider sx={{ mt: 2, mb: 1.5 }} />
      <Box sx={{ px: 2.5, display: 'flex', alignItems: 'center', gap: 1.5 }}>
        <Avatar sx={{ width: 32, height: 32, fontSize: 14, bgcolor: 'primary.main' }}>U</Avatar>
        <Box>
          <Typography variant="body2" sx={{ fontWeight: 600, lineHeight: 1.2 }}>User</Typography>
          <Typography variant="caption" sx={{ color: 'text.disabled' }}>Free plan</Typography>
        </Box>
      </Box>
    </Box>
  );
}

function DashboardLayout({ children }: { children: ReactNode }) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <Box sx={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      {/* Sidebar */}
      {isMobile ? (
        <Drawer open={mobileOpen} onClose={() => setMobileOpen(false)}
          slotProps={{ paper: { sx: { width: SIDEBAR_WIDTH } } }}>
          <SidebarContent onNavigate={() => setMobileOpen(false)} />
        </Drawer>
      ) : (
        <Box sx={{ width: SIDEBAR_WIDTH, flexShrink: 0, borderRight: '1px solid', borderColor: 'divider', bgcolor: 'background.paper', overflow: 'auto' }}>
          <SidebarContent />
        </Box>
      )}

      {/* Main area */}
      <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        {/* TopBar */}
        <Box sx={{ height: 64, flexShrink: 0, display: 'flex', alignItems: 'center', px: 3, borderBottom: '1px solid', borderColor: 'divider', bgcolor: 'background.paper', gap: 1 }}>
          {isMobile && (
            <IconButton edge="start" onClick={() => setMobileOpen(true)} sx={{ mr: 0.5 }}>
              <MenuIcon />
            </IconButton>
          )}
          <PageTitle />
        </Box>

        {/* Content */}
        <Box sx={{ flex: 1, overflow: 'auto', p: 4 }}>
          {children}
        </Box>
      </Box>
    </Box>
  );
}

function PageTitle() {
  const location = useLocation();
  const map: Record<string, string> = {
    '/': 'Dashboard',
    '/resumes': 'Resumes',
    '/cover-letters': 'Cover Letters',
    '/applications': 'Applications',
    '/interview': 'Interview Prep',
    '/settings': 'Settings',
  };
  const title = Object.entries(map).find(([k]) => k === '/' ? location.pathname === '/' : location.pathname.startsWith(k))?.[1] || 'Resume Studio AI';
  return <Typography variant="h6" sx={{ fontWeight: 700 }}>{title}</Typography>;
}

export default DashboardLayout;
