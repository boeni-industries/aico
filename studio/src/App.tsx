import React from 'react';
import { ThemeProvider } from '@mui/material/styles';
import { CssBaseline } from '@mui/material';
import { studioLightTheme, studioDarkTheme } from './theme';
import { StudioLayout } from './layout/StudioLayout';

function App() {
  const [mode, setMode] = React.useState<'light' | 'dark'>('dark');
  const theme = mode === 'dark' ? studioDarkTheme : studioLightTheme;

  const handleToggleTheme = () => {
    setMode((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <StudioLayout mode={mode} onToggleTheme={handleToggleTheme} />
    </ThemeProvider>
  );
}

export default App;
