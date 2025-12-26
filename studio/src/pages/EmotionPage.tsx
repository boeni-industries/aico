import React from 'react';
import { Box, Paper, Typography, CircularProgress, Alert, Tooltip, Slider } from '@mui/material';
import { fetchEmotionHistory, EmotionHistoryItemDto } from '../api/emotion';

function sortHistory(history: EmotionHistoryItemDto[]): EmotionHistoryItemDto[] {
  return [...history].sort((a, b) => (a.timestamp < b.timestamp ? -1 : a.timestamp > b.timestamp ? 1 : 0));
}

function colorForEmotion(_feeling: string, valence: number, arousal: number): string {
  // Research-inspired quadrant mapping:
  //  - Positive + high arousal   → warm yellow/orange (energetic pleasant)
  //  - Positive + low arousal    → green/teal (calm pleasant)
  //  - Negative + high arousal   → red (energetic unpleasant)
  //  - Negative + low arousal    → blue/indigo (calm unpleasant)
  let hue: number;
  if (valence >= 0 && arousal >= 0.5) {
    hue = 40; // energetic pleasant
  } else if (valence >= 0 && arousal < 0.5) {
    hue = 150; // calm pleasant
  } else if (valence < 0 && arousal >= 0.5) {
    hue = 5; // energetic unpleasant
  } else {
    hue = 215; // calm unpleasant
  }

  const sat = 65 + arousal * 20; // 65-85
  const light = 45 + arousal * 12; // 45-57
  return `hsl(${hue}, ${sat}%, ${light}%)`;
}

const EmotionStrip: React.FC<{ history: EmotionHistoryItemDto[]; windowHours: number }> = ({ history, windowHours }) => {
  const samples = sortHistory(history);
  if (samples.length === 0) return null;

  return (
    <Paper
      sx={{
        p: 2,
        display: 'flex',
        flexDirection: 'column',
        gap: 1.5,
      }}
    >
      <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
        Emotion strip (last {windowHours <= 24 ? `${windowHours}h` : `${Math.round(windowHours / 24)}d`})
      </Typography>
      <Typography variant="body2" color="text.secondary">
        Each segment represents one recorded emotional state. Color encodes valence and arousal; opacity reflects
        intensity.
      </Typography>
      <Box
        sx={{
          mt: 1,
          height: 56,
          borderRadius: 999,
          overflow: 'hidden',
          display: 'grid',
          gridTemplateColumns: `repeat(${samples.length}, 1fr)`,
        }}
      >
        {samples.map((item) => {
          const color = colorForEmotion(item.feeling, item.valence, item.arousal);
          const opacity = 0.3 + item.intensity * 0.7;
          return (
            <Tooltip
              key={item.timestamp}
              title={`${item.timestamp}\n${item.feeling} • v=${item.valence.toFixed(2)}, a=${item.arousal.toFixed(
                2,
              )}, i=${item.intensity.toFixed(2)}`}
              arrow
            >
              <Box sx={{ bgcolor: color, opacity }} />
            </Tooltip>
          );
        })}
      </Box>
    </Paper>
  );
};

const EmotionCircumplex: React.FC<{ history: EmotionHistoryItemDto[] }> = ({ history }) => {
  const samples = sortHistory(history);

  const radius = 120;
  const baseSize = radius * 2 + 16;
  const padding = 80;

  const points = samples.map((item, index) => {
    // valence [-1,1] -> x [-r,r], arousal [0,1] -> y [r,-r]
    const x = (item.valence / 1) * radius;
    const y = radius - item.arousal * radius * 2;
    const color = colorForEmotion(item.feeling, item.valence, item.arousal);
    const opacity = 0.4 + item.intensity * 0.6;
    return { x, y, color, opacity, item, key: `${item.timestamp}-${index}` };
  });

  return (
    <Paper
      sx={{
        p: 2,
        display: 'flex',
        flexDirection: 'column',
        gap: 1.5,
        borderRadius: 1,
      }}
    >
      <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
        Valence–arousal circumplex
      </Typography>
      <Typography variant="body2" color="text.secondary">
        Recent states in valence–arousal space.
      </Typography>
      <Box sx={{ mt: 1, display: 'flex', justifyContent: 'center' }}>
        <svg
          width={baseSize + padding * 2}
          height={baseSize + padding * 2}
          viewBox={`${-radius - padding} ${-radius - padding} ${baseSize + padding * 2} ${baseSize + padding * 2}`}
        >
          <defs>
            <clipPath id="emotionCircClip">
              <circle cx={0} cy={0} r={radius} />
            </clipPath>
          </defs>
          {/* Quadrant backgrounds for quick reading, clipped to the circle */}
          <g clipPath="url(#emotionCircClip)">
            <rect
              x={0}
              y={-radius}
              width={radius}
              height={radius}
              fill="rgba(0, 200, 140, 0.10)" // energetic & pleasant
            />
            <rect
              x={-radius}
              y={-radius}
              width={radius}
              height={radius}
              fill="rgba(220, 70, 90, 0.10)" // energetic & unpleasant
            />
            <rect
              x={0}
              y={0}
              width={radius}
              height={radius}
              fill="rgba(80, 170, 255, 0.08)" // calm & pleasant
            />
            <rect
              x={-radius}
              y={0}
              width={radius}
              height={radius}
              fill="rgba(80, 90, 150, 0.10)" // calm & unpleasant
            />
          </g>
          <circle
            cx={0}
            cy={0}
            r={radius}
            fill="none"
            stroke="rgba(255,255,255,0.12)"
            strokeWidth={1}
          />
          <line x1={-radius} y1={0} x2={radius} y2={0} stroke="rgba(255,255,255,0.16)" strokeWidth={1} />
          <line x1={0} y1={-radius} x2={0} y2={radius} stroke="rgba(255,255,255,0.16)" strokeWidth={1} />
          {/* Axis labels - cardinal points outside circle */}
          <text x={0} y={-radius - 20} fill="rgba(255,255,255,0.9)" fontSize={11} textAnchor="middle">
            high arousal
          </text>
          <text x={0} y={radius + 32} fill="rgba(255,255,255,0.9)" fontSize={11} textAnchor="middle">
            low arousal
          </text>
          <text x={radius + 45} y={5} fill="rgba(255,255,255,0.9)" fontSize={11} textAnchor="middle">
            pleasant
          </text>
          <text x={-radius - 45} y={5} fill="rgba(255,255,255,0.9)" fontSize={11} textAnchor="middle">
            unpleasant
          </text>
          {/* Quadrant descriptions - diagonal positions outside circle */}
          <text
            x={radius * 0.707 + 8}
            y={-radius * 0.707 - 24}
            fill="rgba(255,255,255,0.78)"
            fontSize={10}
            textAnchor="middle"
          >
            energetic
          </text>
          <text
            x={radius * 0.707 + 8}
            y={-radius * 0.707 - 12}
            fill="rgba(255,255,255,0.78)"
            fontSize={10}
            textAnchor="middle"
          >
            pleasant
          </text>
          <text
            x={-radius * 0.707 - 8}
            y={-radius * 0.707 - 24}
            fill="rgba(255,255,255,0.78)"
            fontSize={10}
            textAnchor="middle"
          >
            energetic
          </text>
          <text
            x={-radius * 0.707 - 8}
            y={-radius * 0.707 - 12}
            fill="rgba(255,255,255,0.78)"
            fontSize={10}
            textAnchor="middle"
          >
            unpleasant
          </text>
          <text
            x={radius * 0.707 + 8}
            y={radius * 0.707 + 18}
            fill="rgba(255,255,255,0.78)"
            fontSize={10}
            textAnchor="middle"
          >
            calm
          </text>
          <text
            x={radius * 0.707 + 8}
            y={radius * 0.707 + 30}
            fill="rgba(255,255,255,0.78)"
            fontSize={10}
            textAnchor="middle"
          >
            pleasant
          </text>
          <text
            x={-radius * 0.707 - 8}
            y={radius * 0.707 + 18}
            fill="rgba(255,255,255,0.78)"
            fontSize={10}
            textAnchor="middle"
          >
            calm
          </text>
          <text
            x={-radius * 0.707 - 8}
            y={radius * 0.707 + 30}
            fill="rgba(255,255,255,0.78)"
            fontSize={10}
            textAnchor="middle"
          >
            unpleasant
          </text>
          {points.map((p) => (
            <Tooltip
              key={p.key}
              title={`${p.item.feeling} • v=${p.item.valence.toFixed(2)}, a=${p.item.arousal.toFixed(2)}, i=${p.item.intensity.toFixed(
                2,
              )}`}
              arrow
            >
              <circle cx={p.x} cy={p.y} r={5} fill={p.color} fillOpacity={p.opacity} />
            </Tooltip>
          ))}
        </svg>
      </Box>
    </Paper>
  );
};

const EmotionLabelDistribution: React.FC<{ history: EmotionHistoryItemDto[] }> = ({ history }) => {
  const counts = history.reduce<Record<string, number>>((acc, item) => {
    acc[item.feeling] = (acc[item.feeling] || 0) + 1;
    return acc;
  }, {});

  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  const total = history.length || 1;

  return (
    <Paper
      sx={{
        p: 2,
        display: 'flex',
        flexDirection: 'column',
        gap: 1.5,
        borderRadius: 1,
      }}
    >
      <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
        Label distribution
      </Typography>
      <Typography variant="body2" color="text.secondary">
        Frequency of primary emotion labels over the current time window.
      </Typography>
      <Box sx={{ mt: 1, display: 'flex', flexDirection: 'column', gap: 1 }}>
        {entries.map(([label, count]) => {
          const pct = (count / total) * 100;
          return (
            <Box key={label} sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <Box sx={{ minWidth: 90 }}>
                <Typography variant="body2">{label}</Typography>
              </Box>
              <Box sx={{ flex: 1, borderRadius: 999, bgcolor: 'rgba(255,255,255,0.04)', overflow: 'hidden' }}>
                <Box
                  sx={{
                    width: `${pct}%`,
                    minWidth: pct > 0 ? 8 : 0,
                    bgcolor: 'rgba(184,161,234,0.7)',
                    height: 8,
                  }}
                />
              </Box>
              <Typography variant="caption" color="text.secondary" sx={{ minWidth: 60, textAlign: 'right' }}>
                {count} · {pct.toFixed(0)}%
              </Typography>
            </Box>
          );
        })}
        {entries.length === 0 && (
          <Typography variant="body2" color="text.secondary">
            No labeled emotion states in the selected window.
          </Typography>
        )}
      </Box>
    </Paper>
  );
};

export const EmotionPage: React.FC = () => {
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [history, setHistory] = React.useState<EmotionHistoryItemDto[]>([]);
  const [windowHours, setWindowHours] = React.useState<number>(24);

  React.useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        // For windows up to 72h use hours, beyond that switch to days for backend convenience.
        const query: { limit: number; hours?: number; days?: number } = { limit: 200 };
        if (windowHours <= 72) {
          query.hours = windowHours;
        } else {
          query.days = Math.round(windowHours / 24);
        }
        const response = await fetchEmotionHistory(query);
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
  }, [windowHours]);

  const marks = [
    { value: 1, label: '1h' },
    { value: 24, label: '24h' },
    { value: 72, label: '3d' },
    { value: 168, label: '7d' },
  ];

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Paper sx={{ p: 2, display: 'flex', flexDirection: 'column', gap: 1.5, maxWidth: 480, borderRadius: 1 }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
          Lookback window
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Choose how far back to inspect emotional history.
        </Typography>
        <Slider
          size="small"
          value={windowHours}
          min={1}
          max={168}
          step={null}
          marks={marks}
          onChange={(_, value) => {
            if (typeof value === 'number') setWindowHours(value);
          }}
        />
      </Paper>

      {error && (
        <Alert severity="error" sx={{ maxWidth: 640 }}>
          {error}
        </Alert>
      )}

      {loading ? (
        <Paper sx={{ p: 3, borderRadius: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', py: 6 }}>
            <CircularProgress size={24} />
          </Box>
        </Paper>
      ) : history.length === 0 ? (
        <Paper sx={{ p: 3, borderRadius: 1 }}>
          <Typography variant="body1" color="text.secondary">
            No emotion history available yet. Once AICO is running and the emotion engine records states, this page
            will show the full emotion strip, circumplex, and label distribution.
          </Typography>
        </Paper>
      ) : (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          <EmotionStrip history={history} windowHours={windowHours} />
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'minmax(0, 3fr) minmax(0, 2fr)' }, gap: 3 }}>
            <EmotionCircumplex history={history} />
            <EmotionLabelDistribution history={history} />
          </Box>
        </Box>
      )}
    </Box>
  );
};
