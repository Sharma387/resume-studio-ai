import { createContext, useMemo, useState, type ReactNode } from 'react';
import { createTheme, ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import useMediaQuery from '@mui/material/useMediaQuery';

type ThemeMode = 'dark' | 'light';

interface ThemeContextValue {
  mode: ThemeMode;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

export { ThemeContext };

export function ThemeModeProvider({ children }: { children: ReactNode }) {
  const prefersDark = useMediaQuery('(prefers-color-scheme: dark)');
  const [mode, setMode] = useState<ThemeMode>(prefersDark ? 'dark' : 'light');

  const toggleTheme = () => {
    setMode((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  const theme = useMemo(
    () =>
      createTheme({
        palette: {
          mode,
          primary: {
            main: '#7c4dff',
            light: '#b47cff',
            dark: '#3f1dcb',
          },
          secondary: {
            main: '#00e5ff',
          },
          ...(mode === 'dark'
            ? {
                background: {
                  default: '#0a0a1a',
                  paper: 'rgba(255, 255, 255, 0.05)',
                },
              }
            : {
                background: {
                  default: '#f5f5f7',
                  paper: 'rgba(255, 255, 255, 0.8)',
                },
              }),
        },
        typography: {
          fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
          h1: {
            fontSize: '3.5rem',
            fontWeight: 700,
            letterSpacing: '-0.02em',
            background: 'linear-gradient(135deg, #7c4dff 0%, #00e5ff 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          },
        },
        shape: {
          borderRadius: 16,
        },
        components: {
          MuiCard: {
            styleOverrides: {
              root: {
                background: mode === 'dark' ? 'rgba(255, 255, 255, 0.05)' : 'rgba(255, 255, 255, 0.8)',
                backdropFilter: 'blur(20px)',
                border: mode === 'dark' ? '1px solid rgba(255, 255, 255, 0.1)' : '1px solid rgba(0, 0, 0, 0.08)',
                borderRadius: 24,
              },
            },
          },
        },
      }),
    [mode],
  );

  return (
    <ThemeContext.Provider value={{ mode, toggleTheme }}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        {children}
      </ThemeProvider>
    </ThemeContext.Provider>
  );
}
