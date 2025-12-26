import React from 'react';
import { Box, Paper, TextField, Typography, Button, Alert } from '@mui/material';
import { useAuth } from './AuthContext';

export const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const [userUuid, setUserUuid] = React.useState('');
  const [pin, setPin] = React.useState('');
  const [submitting, setSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(userUuid.trim(), pin.trim());
    } catch (e) {
      setError((e as Error).message || 'Login failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        p: 2,
      }}
    >
      <Paper
        elevation={8}
        sx={{
          maxWidth: 420,
          width: '100%',
          p: 4,
          backdropFilter: 'blur(18px)',
          backgroundColor: (theme) =>
            theme.palette.mode === 'dark'
              ? 'rgba(15, 17, 26, 0.75)'
              : 'rgba(255, 255, 255, 0.85)',
        }}
      >
        <Typography variant="h5" sx={{ mb: 0.5, fontWeight: 600 }}>
          Studio Login
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          Enter your user UUID and PIN to start a secure Studio session.
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <Box component="form" onSubmit={handleSubmit} sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <TextField
            label="User UUID"
            value={userUuid}
            onChange={(e) => setUserUuid(e.target.value)}
            fullWidth
            size="small"
            autoComplete="username"
            required
          />
          <TextField
            label="PIN"
            value={pin}
            onChange={(e) => setPin(e.target.value)}
            fullWidth
            size="small"
            type="password"
            autoComplete="current-password"
            helperText="Family-aware PIN: 4 digits for parents, 3 for children, 2 for guests."
            required
          />

          <Button
            type="submit"
            variant="contained"
            color="primary"
            disabled={submitting}
            sx={{ mt: 1.5 }}
          >
            {submitting ? 'Signing in…' : 'Sign in'}
          </Button>
        </Box>
      </Paper>
    </Box>
  );
};
