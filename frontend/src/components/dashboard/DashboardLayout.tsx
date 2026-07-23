import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Box, Drawer, List, ListItemButton, ListItemIcon, ListItemText, AppBar, Toolbar,
  Typography, IconButton, useMediaQuery, useTheme,
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import DashboardOutlined from '@mui/icons-material/DashboardOutlined';
import DescriptionOutlined from '@mui/icons-material/DescriptionOutlined';
import MailOutlined from '@mui/icons-material/MailOutlined';
import BusinessCenterOutlined from '@mui/icons-material/BusinessCenterOutlined';
import RecordVoiceOverOutlined from '@mui/icons-material/RecordVoiceOverOutlined';
import SettingsOutlined from '@mui/icons-material/SettingsOutlined';
import type { ReactNode } from 'react';

const DRAWER_WIDTH = 240;

const navItems = [
  { path: '/', label: 'Dashboard', icon: <DashboardOutlined /> },
  { path: '/resumes', label: 'Resumes', icon: <DescriptionOutlined /> },
  { path: '/cover-letters', label: 'Cover Letters', icon: <MailOutlined /> },
  { path: '/applications', label: 'Applications', icon: <BusinessCenterOutlined /> },
  { path: '/interview', label: 'Interview Prep', icon: <RecordVoiceOverOutlined /> },
  { path: '/settings', label: 'Settings', icon: <SettingsOutlined /> },
];

interface DashboardLayoutProps {
  children: ReactNode;
}

function DashboardLayout({ children }: DashboardLayoutProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [mobileOpen, setMobileOpen] = useState(false);

  const sidebar = (
    <Box sx={{ pt: 2 }}>
      <Typography
        variant="h6"
        sx={{ px: 2, mb: 3, fontWeight: 700, background: 'linear-gradient(135deg, #7c4dff, #00e5ff)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}
      >
        RSAI
      </Typography>
      <List>
        {navItems.map((item) => {
          const active = location.pathname === item.path || (item.path !== '/' && location.pathname.startsWith(item.path));
          return (
            <ListItemButton
              key={item.path}
              selected={active}
              onClick={() => { navigate(item.path); if (isMobile) setMobileOpen(false); }}
              sx={{ mx: 1, borderRadius: 2, mb: 0.5, '&.Mui-selected': { bgcolor: 'primary.main', color: 'primary.contrastText', '&:hover': { bgcolor: 'primary.dark' }, '& .MuiListItemIcon-root': { color: 'inherit' } } }}
            >
              <ListItemIcon sx={{ minWidth: 40, color: active ? 'inherit' : 'text.secondary' }}>{item.icon}</ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItemButton>
          );
        })}
      </List>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      {isMobile ? (
        <Drawer open={mobileOpen} onClose={() => setMobileOpen(false)}
          slotProps={{ paper: { sx: { width: DRAWER_WIDTH } } }}>
          {sidebar}
        </Drawer>
      ) : (
        <Drawer variant="permanent" slotProps={{ paper: { sx: { width: DRAWER_WIDTH, borderRight: '1px solid', borderColor: 'divider' } } }}>
          {sidebar}
        </Drawer>
      )}

      <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <AppBar position="sticky" elevation={0} sx={{ bgcolor: 'background.paper', borderBottom: 1, borderColor: 'divider' }}>
          <Toolbar>
            {isMobile && (
              <IconButton edge="start" onClick={() => setMobileOpen(true)} sx={{ mr: 1 }}>
                <MenuIcon />
              </IconButton>
            )}
            <Typography variant="h6" sx={{ fontWeight: 700, flexGrow: 1, color: 'text.primary' }}>
              {navItems.find((i) => i.path === location.pathname || (i.path !== '/' && location.pathname.startsWith(i.path)))?.label || 'Resume Studio AI'}
            </Typography>
          </Toolbar>
        </AppBar>
        <Box sx={{ flex: 1, overflow: 'auto', p: { xs: 2, md: 3 } }}>
          {children}
        </Box>
      </Box>
    </Box>
  );
}

export default DashboardLayout;
