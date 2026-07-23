import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AppBar,
  Toolbar,
  Typography,
  IconButton,
  Button,
  Box,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  useMediaQuery,
  useTheme,
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import DarkModeOutlined from '@mui/icons-material/DarkModeOutlined';
import LightModeOutlined from '@mui/icons-material/LightModeOutlined';
import GitHubIcon from '@mui/icons-material/GitHub';
import SettingsOutlined from '@mui/icons-material/SettingsOutlined';
import LogoutOutlined from '@mui/icons-material/LogoutOutlined';
import LoginOutlined from '@mui/icons-material/LoginOutlined';
import { useThemeMode } from '../contexts/useThemeMode';
import { useAuth } from '../contexts/AuthContext';

const navItems = ['Features', 'Pricing', 'About'];

function Header() {
  const { mode, toggleTheme } = useThemeMode();
  const { isAuthenticated, user, logout } = useAuth();
  const navigate = useNavigate();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleDrawerToggle = () => {
    setMobileOpen((prev) => !prev);
  };

  const drawer = (
    <Box onClick={handleDrawerToggle} sx={{ textAlign: 'center', pt: 2 }}>
      <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>
        Resume Studio AI
      </Typography>
      <List>
        {navItems.map((item) => (
          <ListItem key={item} disablePadding>
            <ListItemButton sx={{ textAlign: 'center' }}>
              <ListItemText primary={item} />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
    </Box>
  );

  return (
    <>
      <AppBar
        position="fixed"
        elevation={0}
        sx={{
          background: 'transparent',
          backdropFilter: 'blur(16px)',
          WebkitBackdropFilter: 'blur(16px)',
          borderBottom: '1px solid',
          borderColor: mode === 'dark' ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)',
        }}
      >
        <Toolbar sx={{ maxWidth: 1400, width: '100%', mx: 'auto', px: { xs: 2, md: 4 } }}>
          {isMobile && (
            <IconButton edge="start" onClick={handleDrawerToggle} aria-label="Open navigation menu" sx={{ mr: 1 }}>
              <MenuIcon />
            </IconButton>
          )}

          <Typography
            variant="h6"
            sx={{
              fontWeight: 700,
              background: 'linear-gradient(135deg, #7c4dff 0%, #00e5ff 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              flexShrink: 0,
            }}
          >
            Resume Studio AI
          </Typography>

          {!isMobile && (
            <Box sx={{ ml: 6, display: 'flex', gap: 1 }}>
              {navItems.map((item) => (
                <Button
                  key={item}
                  sx={{
                    color: 'text.secondary',
                    textTransform: 'none',
                    fontWeight: 500,
                    '&:hover': { color: 'text.primary' },
                  }}
                >
                  {item}
                </Button>
              ))}
            </Box>
          )}

          <Box sx={{ flexGrow: 1 }} />

          {isAuthenticated ? (
            <>
              <Typography variant="caption" sx={{ color: 'text.secondary', mr: 1, display: { xs: 'none', sm: 'block' } }}>
                {user?.full_name}
              </Typography>
              <IconButton onClick={logout} aria-label="Logout" sx={{ color: 'text.secondary' }}>
                <LogoutOutlined />
              </IconButton>
            </>
          ) : (
            <Button onClick={() => navigate('/login')} startIcon={<LoginOutlined />}
              sx={{ textTransform: 'none', borderRadius: 2 }} size="small">
              Login
            </Button>
          )}

          <IconButton onClick={toggleTheme} aria-label="Toggle theme" sx={{ color: 'text.secondary' }}>
            {mode === 'dark' ? <LightModeOutlined /> : <DarkModeOutlined />}
          </IconButton>

          <IconButton
            component="a"
            href="https://github.com/Sharma387/resume-studio-ai"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="View project on GitHub"
            sx={{ color: 'text.secondary' }}
          >
            <GitHubIcon />
          </IconButton>

          <IconButton aria-label="Settings" disabled sx={{ color: 'text.secondary' }}>
            <SettingsOutlined />
          </IconButton>
        </Toolbar>
      </AppBar>

      <Drawer
        anchor="left"
        open={mobileOpen}
        onClose={handleDrawerToggle}
        ModalProps={{ keepMounted: true }}
        slotProps={{
          paper: {
            sx: {
              background: mode === 'dark' ? 'rgba(10, 10, 26, 0.95)' : 'rgba(245, 245, 247, 0.95)',
              backdropFilter: 'blur(20px)',
              width: 280,
            },
          },
        }}
      >
        {drawer}
      </Drawer>

      <Toolbar />
    </>
  );
}

export default Header;
