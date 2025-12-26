import React from 'react';
import { Box, Paper, Typography, CircularProgress, Alert } from '@mui/material';
import { fetchEmotionHistory, EmotionHistoryItemDto } from '../api/emotion';

export const EmotionPage: React.FC = () => {
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [history, setHistory] = React.useState<EmotionHistoryItemDto[]>([]);

  React.useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const response = await fetchEmotionHistory({ limit: 200, hours: 24 });
        if (!cancelled) {
          setHistory(response.history ?? []);
        }
      } catch (e) {
        if (!cancelled) {
          setError((e as Error).message ?? 'Failed to load emotion history');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Typography variant="h1" sx={{ fontSize: '1.4rem', fontWeight: 600 }}>
        Emotion
      </Typography>

      {error && (
        <Alert severity="error" sx={{ maxWidth: 640 }}>
          {error}
        </Alert>
      )}

      <Paper sx={{ p: 3, minHeight: 160 }}>
        {loading ? (
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', py: 6 }}>
            <CircularProgress size={24} />
          </Box>
        ) : history.length === 0 ? (
          <Typography variant="body1" color="text.secondary">
            No emotion history available yet. Once AICO is running and the emotion engine
            records states, this page will show the full emotion timeline and
            visualizations.
          </Typography>
        ) : (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
              History snapshot
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Loaded {history.length} emotion states from the last 24 hours. The
              visualization layer will render these as a valence–arousal strip,
              circumplex plot, and label distribution according to the
              <code>emotion-design.md</code> spec.
            </Typography>
            <Typography variant="body2" sx={{ mt: 1 }}>
              Most recent: <strong>{history[0].feeling}</strong> (valence{' '}
              {history[0].valence.toFixed(2)}, arousal {history[0].arousal.toFixed(2)},
              intensity {history[0].intensity.toFixed(2)}) at {history[0].timestamp}.
            </Typography>
          </Box>
        )}
      </Paper>
    </Box>
  );
};
