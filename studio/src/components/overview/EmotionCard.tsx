import React from 'react';
import { Box, Typography, Chip } from '@mui/material';
import {
  EmojiEmotions as EmojiEmotionsIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
} from '@mui/icons-material';

interface EmotionCardProps {
  currentState: string;
  valence: number;
  arousal: number;
  onClick?: () => void;
}

const emotionColors = {
  calm: { bg: 'rgba(59, 130, 246, 0.12)', text: '#3B82F6', border: 'rgba(59, 130, 246, 0.3)', icon: '#3B82F6' },
  happy: { bg: 'rgba(16, 185, 129, 0.12)', text: '#10B981', border: 'rgba(16, 185, 129, 0.3)', icon: '#10B981' },
  excited: { bg: 'rgba(245, 158, 11, 0.12)', text: '#F59E0B', border: 'rgba(245, 158, 11, 0.3)', icon: '#F59E0B' },
  anxious: { bg: 'rgba(239, 68, 68, 0.12)', text: '#EF4444', border: 'rgba(239, 68, 68, 0.3)', icon: '#EF4444' },
  sad: { bg: 'rgba(139, 92, 246, 0.12)', text: '#8B5CF6', border: 'rgba(139, 92, 246, 0.3)', icon: '#8B5CF6' },
  neutral: { bg: 'rgba(148, 163, 184, 0.12)', text: '#94A3B8', border: 'rgba(148, 163, 184, 0.3)', icon: '#94A3B8' },
};

export const EmotionCard: React.FC<EmotionCardProps> = ({
  currentState,
  valence,
  arousal,
  onClick,
}) => {
  const stateKey = currentState.toLowerCase() as keyof typeof emotionColors;
  const colors = emotionColors[stateKey] || emotionColors.neutral;

  return (
    <Box
      onClick={onClick}
      sx={{
        p: 3,
        borderRadius: '20px',
        border: '1.5px solid',
        borderColor: 'divider',
        bgcolor: 'background.paper',
        backdropFilter: 'blur(12px)',
        boxShadow: '0 4px 16px rgba(0,0,0,0.04)',
        cursor: 'pointer',
        transition: 'all 0.2s ease-in-out',
        '&:hover': {
          transform: 'translateY(-4px)',
          boxShadow: '0 12px 32px rgba(0,0,0,0.12)',
          borderColor: 'primary.main',
        },
      }}
    >
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Box
            sx={{
              width: 40,
              height: 40,
              borderRadius: '12px',
              bgcolor: colors.bg,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <EmojiEmotionsIcon sx={{ color: colors.icon, fontSize: 24 }} />
          </Box>
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 700, fontSize: '1.1rem' }}>
              Emotion
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.75rem' }}>
              Current State
            </Typography>
          </Box>
        </Box>
        <Chip
          label="LIVE"
          size="small"
          sx={{
            bgcolor: 'rgba(16, 185, 129, 0.12)',
            color: '#10B981',
            border: '1px solid',
            borderColor: 'rgba(16, 185, 129, 0.3)',
            fontWeight: 700,
            fontSize: '0.7rem',
            height: 24,
          }}
        />
      </Box>

      {/* Current State */}
      <Box
        sx={{
          p: 2,
          mb: 2.5,
          borderRadius: '12px',
          bgcolor: colors.bg,
          border: '1px solid',
          borderColor: colors.border,
        }}
      >
        <Typography variant="caption" sx={{ fontSize: '0.7rem', color: 'text.secondary', mb: 0.5, display: 'block' }}>
          FEELING
        </Typography>
        <Typography variant="body2" sx={{ fontWeight: 600, color: colors.text, fontSize: '0.9rem', textTransform: 'capitalize' }}>
          {currentState}
        </Typography>
      </Box>

      {/* Metrics Grid */}
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: 'repeat(2, 1fr)',
          gap: 2,
          mb: 2.5,
        }}
      >
        {/* Valence */}
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
            {valence >= 0 ? (
              <TrendingUpIcon sx={{ fontSize: 16, color: '#10B981' }} />
            ) : (
              <TrendingDownIcon sx={{ fontSize: 16, color: '#EF4444' }} />
            )}
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
              Valence
            </Typography>
          </Box>
          <Typography variant="h5" sx={{ fontWeight: 700, color: valence >= 0 ? '#10B981' : '#EF4444' }}>
            {valence >= 0 ? '+' : ''}{valence.toFixed(2)}
          </Typography>
        </Box>

        {/* Arousal */}
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
            <EmojiEmotionsIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
              Arousal
            </Typography>
          </Box>
          <Typography variant="h5" sx={{ fontWeight: 700, color: 'text.primary' }}>
            {arousal.toFixed(2)}
          </Typography>
        </Box>
      </Box>

      {/* Footer Stats */}
      <Box
        sx={{
          display: 'flex',
          gap: 2,
          pt: 2.5,
          borderTop: '1px solid',
          borderColor: 'divider',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
          <Box
            sx={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              bgcolor: colors.icon,
              boxShadow: `0 0 8px ${colors.icon}40`,
            }}
          />
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
            Real-time tracking
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
          <EmojiEmotionsIcon sx={{ fontSize: 14, color: colors.icon }} />
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
            Circumplex model
          </Typography>
        </Box>
      </Box>
    </Box>
  );
};
