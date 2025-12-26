import React from 'react';
import { ThemeProvider } from '@mui/material/styles';
import { CssBaseline } from '@mui/material';
import { studioLightTheme, studioDarkTheme } from './theme';
import { StudioLayout } from './layout/StudioLayout';
import { AuthProvider, useAuth } from './auth/AuthContext';
import { LoginPage } from './auth/LoginPage';

const AppShell: React.FC = () => {
  const { user } = useAuth();
  const [mode, setMode] = React.useState<'light' | 'dark'>('dark');
  const theme = mode === 'dark' ? studioDarkTheme : studioLightTheme;

  const handleToggleTheme = () => {
    setMode((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      {user ? (
        <StudioLayout mode={mode} onToggleTheme={handleToggleTheme} />
      ) : (
        <LoginPage />
      )}
    </ThemeProvider>
  );
};

function App() {
  return (
    <AuthProvider>
      <AppShell />
    </AuthProvider>
  );
}

export default App;
