import React from 'react';
import { Box, Paper, Typography, LinearProgress, Chip } from '@mui/material';
import { CuriosityStatusResponse, CuriosityLevel } from '../../types/agency';
import { Lightbulb as LightbulbIcon, Compass as ExploreIcon } from 'lucide-react';

interface CuriosityDashboardProps {
  curiosityStatus: CuriosityStatusResponse | null;
  loading?: boolean;
}

const curiosityLevelColors: Record<CuriosityLevel, { bg: string; text: string; border: string }> = {
  low: {
    bg: 'rgba(156, 163, 175, 0.12)',
    text: '#9CA3AF',
    border: 'rgba(156, 163, 175, 0.3)',
  },
  medium: {
    bg: 'rgba(245, 158, 11, 0.12)',
    text: '#F59E0B',
    border: 'rgba(245, 158, 11, 0.3)',
  },
  high: {
    bg: 'rgba(16, 185, 129, 0.12)',
    text: '#10B981',
    border: 'rgba(16, 185, 129, 0.3)',
  },
};

export const CuriosityDashboard: React.FC<CuriosityDashboardProps> = ({
  curiosityStatus,
  loading,
}) => {
  if (loading || !curiosityStatus) {
    return (
      <Typography variant="body2" color="text.secondary">
        Loading curiosity data...
      </Typography>
    );
  }

  const levelColors = curiosityLevelColors[curiosityStatus.curiosity_level];
  const levelPercentage = {
    low: 33,
    medium: 66,
    high: 100,
  }[curiosityStatus.curiosity_level];

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {/* Curiosity Level Gauge */}
      <Paper
        sx={{
          p: 3,
          borderRadius: '28px',
          border: '1.5px solid',
          borderColor: 'divider',
          bgcolor: 'background.paper',
          backdropFilter: 'blur(20px)',
          boxShadow: '0 8px 32px rgba(0,0,0,0.06)',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
          <Box
            sx={{
              width: 48,
              height: 48,
              borderRadius: '16px',
              bgcolor: levelColors.bg,
              border: '1.5px solid',
              borderColor: levelColors.border,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <ExploreIcon sx={{ fontSize: 28, color: levelColors.text }} />
          </Box>
          <Box sx={{ flexGrow: 1 }}>
            <Typography
              variant="caption"
              sx={{
                textTransform: 'uppercase',
                letterSpacing: '0.1em',
                fontWeight: 600,
                color: 'text.secondary',
                fontSize: '0.7rem',
              }}
            >
              Curiosity Level
            </Typography>
            <Typography
              variant="h4"
              sx={{
                fontWeight: 700,
                fontSize: '1.75rem',
                color: levelColors.text,
                textTransform: 'uppercase',
              }}
            >
              {curiosityStatus.curiosity_level}
            </Typography>
          </Box>
          <Chip
            label={`${curiosityStatus.curiosity_goals_active} active`}
            sx={{
              bgcolor: levelColors.bg,
              color: levelColors.text,
              border: '1px solid',
              borderColor: levelColors.border,
              fontWeight: 600,
              fontSize: '0.8rem',
            }}
          />
        </Box>

        <Box sx={{ mb: 1 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
              Exploration Intensity
            </Typography>
            <Typography
              variant="caption"
              sx={{
                fontSize: '0.7rem',
                fontWeight: 600,
                fontFamily: 'monospace',
                color: levelColors.text,
              }}
            >
              {levelPercentage}%
            </Typography>
          </Box>
          <LinearProgress
            variant="determinate"
            value={levelPercentage}
            sx={{
              height: 8,
              borderRadius: 4,
              bgcolor: 'background.default',
              '& .MuiLinearProgress-bar': {
                bgcolor: levelColors.text,
                borderRadius: 4,
                boxShadow: `0 0 12px ${levelColors.text}40`,
              },
            }}
          />
        </Box>

        <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.75rem' }}>
          Current exploration intensity based on active curiosity-driven goals
        </Typography>
      </Paper>

      {/* Curiosity Opportunities */}
      {curiosityStatus.curiosity_opportunities.length > 0 && (
        <Box>
          <Typography
            variant="h6"
            sx={{
              mb: 2,
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: 1,
            }}
          >
            <LightbulbIcon sx={{ fontSize: 20, color: 'primary.main' }} />
            Curiosity Opportunities
          </Typography>

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {curiosityStatus.curiosity_opportunities.map((opportunity, index) => {
              const intensity = Math.round(opportunity.intensity * 100);
              const intensityColor =
                intensity >= 70
                  ? curiosityLevelColors.high.text
                  : intensity >= 40
                  ? curiosityLevelColors.medium.text
                  : curiosityLevelColors.low.text;

              return (
                <Paper
                  key={index}
                  sx={{
                    p: 2.5,
                    borderRadius: '20px',
                    border: '1.5px solid',
                    borderColor: 'divider',
                    bgcolor: 'background.paper',
                    backdropFilter: 'blur(12px)',
                    boxShadow: '0 4px 16px rgba(0,0,0,0.04)',
                    transition: 'all 0.2s ease-in-out',
                    '&:hover': {
                      transform: 'translateY(-2px)',
                      boxShadow: '0 8px 24px rgba(0,0,0,0.08)',
                    },
                  }}
                >
                  <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2, mb: 1.5 }}>
                    <Box
                      sx={{
                        width: 8,
                        height: 8,
                        borderRadius: '50%',
                        bgcolor: intensityColor,
                        mt: 0.75,
                        flexShrink: 0,
                        boxShadow: `0 0 12px ${intensityColor}40`,
                      }}
                    />
                    <Box sx={{ flexGrow: 1 }}>
                      <Typography
                        variant="subtitle2"
                        sx={{ fontWeight: 600, fontSize: '0.95rem', mb: 0.5 }}
                      >
                        {opportunity.theme}
                      </Typography>
                      <Typography
                        variant="body2"
                        color="text.secondary"
                        sx={{ fontSize: '0.85rem', lineHeight: 1.5 }}
                      >
                        {opportunity.description}
                      </Typography>
                    </Box>
                  </Box>

                  <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                    <Chip
                      label={opportunity.signal_type}
                      size="small"
                      sx={{
                        bgcolor: 'background.default',
                        fontSize: '0.7rem',
                        height: 22,
                        fontWeight: 600,
                      }}
                    />
                    <Box sx={{ flexGrow: 1 }}>
                      <LinearProgress
                        variant="determinate"
                        value={intensity}
                        sx={{
                          height: 4,
                          borderRadius: 2,
                          bgcolor: 'background.default',
                          '& .MuiLinearProgress-bar': {
                            bgcolor: intensityColor,
                            borderRadius: 2,
                          },
                        }}
                      />
                    </Box>
                    <Typography
                      variant="caption"
                      sx={{
                        fontSize: '0.7rem',
                        fontWeight: 600,
                        fontFamily: 'monospace',
                        color: intensityColor,
                      }}
                    >
                      {intensity}%
                    </Typography>
                  </Box>
                </Paper>
              );
            })}
          </Box>
        </Box>
      )}

      {curiosityStatus.curiosity_opportunities.length === 0 && (
        <Paper
          sx={{
            p: 4,
            borderRadius: '20px',
            border: '1.5px solid',
            borderColor: 'divider',
            bgcolor: 'background.paper',
            textAlign: 'center',
          }}
        >
          <Typography variant="body2" color="text.secondary">
            No active curiosity opportunities at the moment
          </Typography>
        </Paper>
      )}
    </Box>
  );
};
