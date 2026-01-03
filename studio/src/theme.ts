import { createTheme } from '@mui/material/styles';
import type { PaletteOptions, ThemeOptions } from '@mui/material';

const lightPalette: PaletteOptions = {
  mode: 'light',
  background: {
    default: '#F5F6FA',
    paper: '#FFFFFF',
  },
  primary: {
    main: '#B8A1EA',
  },
  secondary: {
    main: '#8DD6B8',
  },
  error: {
    main: '#ED7867',
  },
  text: {
    primary: '#111827',
    secondary: '#4B5563',
  },
};

const darkPalette: PaletteOptions = {
  mode: 'dark',
  background: {
    default: '#181A21',
    paper: '#21242E',
  },
  primary: {
    main: '#B8A1EA',
  },
  secondary: {
    main: '#8DD6B8',
  },
  error: {
    main: '#ED7867',
  },
  text: {
    primary: '#F9FAFB',
    secondary: '#9CA3AF',
  },
};

const baseThemeOptions: ThemeOptions = {
  shape: {
    borderRadius: 20,
  },
  typography: {
    fontFamily:
      'Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    h1: { fontSize: '2rem', fontWeight: 700 },
    h2: { fontSize: '1.5rem', fontWeight: 600 },
    subtitle1: { fontSize: '1.125rem', fontWeight: 500 },
    body1: { fontSize: '1rem', fontWeight: 400 },
    button: { textTransform: 'none', fontWeight: 600 },
  },
  components: {
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: 36,
          backdropFilter: 'blur(24px)',
          border: '1.5px solid rgba(255,255,255,0.16)',
          boxShadow: '0 20px 40px rgba(0,0,0,0.28)',
        },
      },
    },
    MuiAppBar: {
      defaultProps: {
        elevation: 0,
      },
      styleOverrides: {
        root: {
          backgroundColor: 'transparent',
          boxShadow: 'none',
          backdropFilter: 'blur(20px)',
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          borderRadius: 36,
          margin: 16,
          backdropFilter: 'blur(24px)',
          border: '1.5px solid rgba(255,255,255,0.18)',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 20,
          paddingInline: 20,
        },
      },
    },
    MuiMenu: {
      styleOverrides: {
        paper: {
          borderRadius: 12, // Medium radius for dropdown menus, not XLarge
          minWidth: 180,
        },
      },
    },
  },
};

export const studioLightTheme = createTheme({
  ...baseThemeOptions,
  palette: lightPalette,
  components: {
    ...baseThemeOptions.components,
    MuiPaper: {
      styleOverrides: {
        root: {
          ...(baseThemeOptions.components?.MuiPaper as any)?.styleOverrides?.root,
          backgroundColor: 'rgba(255,255,255,0.6)',
        },
      },
    },
  },
});

export const studioDarkTheme = createTheme({
  ...baseThemeOptions,
  palette: darkPalette,
  components: {
    ...baseThemeOptions.components,
    MuiPaper: {
      styleOverrides: {
        root: {
          ...(baseThemeOptions.components?.MuiPaper as any)?.styleOverrides?.root,
          backgroundColor: 'rgba(15,23,42,0.75)',
        },
      },
    },
  },
});
