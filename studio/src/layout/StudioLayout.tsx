import React from 'react';
import {
  Box,
  Button,
  Divider,
  Drawer,
  IconButton,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Typography,
  useMediaQuery,
} from '@mui/material';
import { useTheme } from '@mui/material/styles';
import DashboardIcon from '@mui/icons-material/Dashboard';
import SpeedIcon from '@mui/icons-material/Speed';
import PsychologyIcon from '@mui/icons-material/Psychology';
import AutoStoriesIcon from '@mui/icons-material/AutoStories';
import AutoModeIcon from '@mui/icons-material/AutoMode';
import SecurityIcon from '@mui/icons-material/Shield';
import EmojiEmotionsIcon from '@mui/icons-material/EmojiEmotions';
import SettingsIcon from '@mui/icons-material/Settings';
import MenuIcon from '@mui/icons-material/Menu';
import DarkModeIcon from '@mui/icons-material/DarkMode';
import LightModeIcon from '@mui/icons-material/LightMode';
import AccountCircleIcon from '@mui/icons-material/AccountCircle';
import LogoutIcon from '@mui/icons-material/Logout';
import { OverviewPage } from '../pages/OverviewPage';
import { overviewStubData } from '../data/overview';
import { OperationsPage } from '../pages/OperationsPage';
import { IntelligencePage } from '../pages/IntelligencePage';
import { MemoryAmsPage } from '../pages/MemoryAmsPage';
import { AgencyPage } from '../pages/AgencyPage';
import { SecurityPage } from '../pages/SecurityPage';
import { EmotionPage } from '../pages/EmotionPage';
import { SystemPage } from '../pages/SystemPage';
import { useAuth } from '../auth/AuthContext';

const drawerWidth = 260;

const primaryNav: { key: StudioNavKey; label: string; icon: React.ReactNode }[] = [
  { key: 'overview', label: 'Overview', icon: <DashboardIcon /> },
  { key: 'operations', label: 'Operations', icon: <SpeedIcon /> },
  { key: 'intelligence', label: 'Intelligence', icon: <PsychologyIcon /> },
  { key: 'emotion', label: 'Emotion', icon: <EmojiEmotionsIcon /> },
  { key: 'memory', label: 'Memory & AMS', icon: <AutoStoriesIcon /> },
  { key: 'agency', label: 'Agency', icon: <AutoModeIcon /> },
  { key: 'security', label: 'Security', icon: <SecurityIcon /> },
  { key: 'system', label: 'System', icon: <SettingsIcon /> },
];

type StudioNavKey =
  | 'overview'
  | 'operations'
  | 'intelligence'
  | 'emotion'
  | 'memory'
  | 'agency'
  | 'security'
  | 'system';

type StudioLayoutProps = React.PropsWithChildren<{
  mode: 'light' | 'dark';
  onToggleTheme: () => void;
}>;

export const StudioLayout: React.FC<StudioLayoutProps> = ({ mode, onToggleTheme }) => {
  const theme = useTheme();
  const isDesktop = useMediaQuery(theme.breakpoints.up('lg'));
  const [mobileOpen, setMobileOpen] = React.useState(false);
  const [active, setActive] = React.useState<StudioNavKey>('overview');
  const { user, logout } = useAuth();

  const handleDrawerToggle = () => {
    setMobileOpen((prev) => !prev);
  };

  const drawer = (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Toolbar sx={{ px: 3 }}>
        <Typography variant="subtitle1" fontWeight={600}>
          AICO Studio
        </Typography>
      </Toolbar>
      <Divider />
      <Box sx={{ flex: 1, py: 1 }}>
        <List>
          {primaryNav.map((item) => (
            <ListItemButton
              key={item.label}
              sx={{
                mx: 1.5,
                mb: 0.5,
                borderRadius: 20,
                ...(active === item.key
                  ? {
                      bgcolor: 'rgba(184,161,234,0.12)',
                    }
                  : {}),
              }}
              onClick={() => setActive(item.key)}
            >
              <ListItemIcon sx={{ minWidth: 40 }}>{item.icon}</ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItemButton>
          ))}
        </List>
      </Box>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'background.default' }}>
      {/* Sidebar */}
      {isDesktop ? (
        <Drawer
          variant="permanent"
          sx={{
            width: drawerWidth,
            flexShrink: 0,
            '& .MuiDrawer-paper': {
              width: drawerWidth,
              borderRadius: 0,
              border: 'none',
              boxSizing: 'border-box',
              bgcolor: 'transparent',
              boxShadow: 'none',
              p: 2,
            },
          }}
        >
          {drawer}
        </Drawer>
      ) : (
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{ keepMounted: true }}
          sx={{
            '& .MuiDrawer-paper': {
              width: drawerWidth,
              boxSizing: 'border-box',
            },
          }}
        >
          {drawer}
        </Drawer>
      )}

      {/* Main content */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          px: { xs: 2, md: 4, xl: 6 },
          pt: { xs: 4, md: 6 },
          pb: { xs: 4, md: 6 },
          display: 'flex',
          justifyContent: 'center',
        }}
      >
        <Box
          sx={{
            width: '100%',
            maxWidth: 1440,
            display: 'flex',
            flexDirection: 'column',
            gap: 3,
          }}
        >
          {/* Top row: menu toggle (mobile), title, theme + user controls */}
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 2,
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
              {!isDesktop && (
                <IconButton
                  edge="start"
                  color="inherit"
                  aria-label="open navigation"
                  onClick={handleDrawerToggle}
                  sx={{ mr: 0.5 }}
                >
                  <MenuIcon />
                </IconButton>
              )}
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                {primaryNav.find((n) => n.key === active)?.label ?? 'Studio'}
              </Typography>
            </Box>

            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <IconButton size="small" onClick={onToggleTheme} color="inherit">
                {mode === 'dark' ? <LightModeIcon fontSize="small" /> : <DarkModeIcon fontSize="small" />}
              </IconButton>
              {user && (
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <AccountCircleIcon fontSize="small" />
                  <Typography variant="body2" noWrap sx={{ maxWidth: 160 }}>
                    {user.full_name || user.nickname || user.uuid}
                  </Typography>
                  <Button
                    size="small"
                    variant="outlined"
                    color="inherit"
                    onClick={logout}
                    startIcon={<LogoutIcon fontSize="small" />}
                    sx={{ textTransform: 'none', borderRadius: 999, px: 1.5, py: 0.25, ml: 0.5 }}
                  >
                    Logout
                  </Button>
                </Box>
              )}
            </Box>
          </Box>

          {active === 'overview' && (
            <OverviewPage data={overviewStubData} onOpenDomain={(key) => setActive(key)} />
          )}
          {active === 'operations' && <OperationsPage />}
          {active === 'intelligence' && <IntelligencePage />}
          {active === 'emotion' && <EmotionPage />}
          {active === 'memory' && <MemoryAmsPage />}
          {active === 'agency' && <AgencyPage />}
          {active === 'security' && <SecurityPage />}
          {active === 'system' && <SystemPage />}
        </Box>
      </Box>
    </Box>
  );
};
