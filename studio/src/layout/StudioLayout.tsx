import React from 'react';
import {
  Box,
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
import ShieldIcon from '@mui/icons-material/Shield';
import SettingsIcon from '@mui/icons-material/Settings';
import MenuIcon from '@mui/icons-material/Menu';
import DarkModeIcon from '@mui/icons-material/DarkMode';
import LightModeIcon from '@mui/icons-material/LightMode';
import { OverviewPage } from '../pages/OverviewPage';
import { OperationsPage } from '../pages/OperationsPage';
import { IntelligencePage } from '../pages/IntelligencePage';
import { MemoryAmsPage } from '../pages/MemoryAmsPage';
import { AgencyPage } from '../pages/AgencyPage';
import { SecurityPage } from '../pages/SecurityPage';
import { SystemPage } from '../pages/SystemPage';

const drawerWidth = 260;

const primaryNav: { key: StudioNavKey; label: string; icon: React.ReactNode }[] = [
  { key: 'overview', label: 'Overview', icon: <DashboardIcon /> },
  { key: 'operations', label: 'Operations', icon: <SpeedIcon /> },
  { key: 'intelligence', label: 'Intelligence', icon: <PsychologyIcon /> },
  { key: 'memory', label: 'Memory & AMS', icon: <AutoStoriesIcon /> },
  { key: 'agency', label: 'Agency', icon: <AutoModeIcon /> },
  { key: 'security', label: 'Security', icon: <ShieldIcon /> },
  { key: 'system', label: 'System', icon: <SettingsIcon /> },
];

type StudioNavKey =
  | 'overview'
  | 'operations'
  | 'intelligence'
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
          {active === 'overview' && <OverviewPage />}
          {active === 'operations' && <OperationsPage />}
          {active === 'intelligence' && <IntelligencePage />}
          {active === 'memory' && <MemoryAmsPage />}
          {active === 'agency' && <AgencyPage />}
          {active === 'security' && <SecurityPage />}
          {active === 'system' && <SystemPage />}
        </Box>
      </Box>
    </Box>
  );
};
