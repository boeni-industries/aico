import React from 'react';
import { Box, Paper, Typography, Chip, LinearProgress } from '@mui/material';
import { ValueProfileResponse } from '../../types/agency';
import SecurityIcon from '@mui/icons-material/Security';
import TuneIcon from '@mui/icons-material/Tune';

interface ValueProfileProps {
  valueProfile: ValueProfileResponse | null;
  loading?: boolean;
}

const proactiveLevelColors = {
  quiet: { bg: 'rgba(156, 163, 175, 0.12)', text: '#9CA3AF', border: 'rgba(156, 163, 175, 0.3)' },
  balanced: { bg: 'rgba(59, 130, 246, 0.12)', text: '#3B82F6', border: 'rgba(59, 130, 246, 0.3)' },
  proactive: { bg: 'rgba(16, 185, 129, 0.12)', text: '#10B981', border: 'rgba(16, 185, 129, 0.3)' },
};

export const ValueProfile: React.FC<ValueProfileProps> = ({ valueProfile, loading }) => {
  if (loading || !valueProfile) {
    return (
      <Typography variant="body2" color="text.secondary">
        Loading value profile...
      </Typography>
    );
  }

  const proactiveColors = proactiveLevelColors[valueProfile.proactive_behavior_level];
  const curiosityPercentage = Math.round(valueProfile.curiosity_intensity * 100);

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {/* Proactive Behavior Level */}
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
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
          <Box
            sx={{
              width: 48,
              height: 48,
              borderRadius: '16px',
              bgcolor: proactiveColors.bg,
              border: '1.5px solid',
              borderColor: proactiveColors.border,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <TuneIcon sx={{ fontSize: 28, color: proactiveColors.text }} />
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
              Proactive Behavior
            </Typography>
            <Typography
              variant="h5"
              sx={{
                fontWeight: 700,
                fontSize: '1.5rem',
                color: proactiveColors.text,
                textTransform: 'capitalize',
              }}
            >
              {valueProfile.proactive_behavior_level}
            </Typography>
          </Box>
        </Box>
        <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.85rem' }}>
          Controls how proactively AICO initiates conversations and suggestions
        </Typography>
      </Paper>

      {/* Curiosity Intensity */}
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
        <Typography
          variant="caption"
          sx={{
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
            fontWeight: 600,
            color: 'text.secondary',
            fontSize: '0.7rem',
            mb: 2,
            display: 'block',
          }}
        >
          Curiosity Intensity Threshold
        </Typography>

        <Box sx={{ mb: 1 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
            <Typography variant="body2" sx={{ fontWeight: 600 }}>
              Minimum intensity to trigger curiosity
            </Typography>
            <Typography
              variant="body2"
              sx={{
                fontWeight: 700,
                fontFamily: 'monospace',
                color: 'primary.main',
              }}
            >
              {curiosityPercentage}%
            </Typography>
          </Box>
          <LinearProgress
            variant="determinate"
            value={curiosityPercentage}
            sx={{
              height: 8,
              borderRadius: 4,
              bgcolor: 'background.default',
              '& .MuiLinearProgress-bar': {
                bgcolor: 'primary.main',
                borderRadius: 4,
                boxShadow: '0 0 12px rgba(184, 161, 234, 0.4)',
              },
            }}
          />
        </Box>

        <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.75rem' }}>
          Higher values mean AICO will only pursue stronger curiosity signals
        </Typography>
      </Paper>

      {/* Sensitive Life Areas */}
      {valueProfile.sensitive_life_areas.length > 0 && (
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
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2 }}>
            <SecurityIcon sx={{ fontSize: 20, color: 'warning.main' }} />
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
              Sensitive Life Areas
            </Typography>
          </Box>

          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
            {valueProfile.sensitive_life_areas.map((area, index) => (
              <Chip
                key={index}
                label={area}
                sx={{
                  bgcolor: 'rgba(245, 158, 11, 0.12)',
                  color: '#F59E0B',
                  border: '1px solid',
                  borderColor: 'rgba(245, 158, 11, 0.3)',
                  fontWeight: 600,
                  fontSize: '0.8rem',
                }}
              />
            ))}
          </Box>

          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ fontSize: '0.75rem', mt: 2, display: 'block' }}
          >
            These areas require explicit consent before AICO can take action
          </Typography>
        </Paper>
      )}

      {/* Allowed Curiosity Domains */}
      {valueProfile.allowed_curiosity_domains.length > 0 && (
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
          <Typography
            variant="caption"
            sx={{
              textTransform: 'uppercase',
              letterSpacing: '0.1em',
              fontWeight: 600,
              color: 'text.secondary',
              fontSize: '0.7rem',
              mb: 2,
              display: 'block',
            }}
          >
            Allowed Curiosity Domains
          </Typography>

          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
            {valueProfile.allowed_curiosity_domains.map((domain, index) => (
              <Chip
                key={index}
                label={domain}
                sx={{
                  bgcolor: 'rgba(94, 234, 212, 0.12)',
                  color: '#5EEAD4',
                  border: '1px solid',
                  borderColor: 'rgba(94, 234, 212, 0.3)',
                  fontWeight: 600,
                  fontSize: '0.8rem',
                }}
              />
            ))}
          </Box>

          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ fontSize: '0.75rem', mt: 2, display: 'block' }}
          >
            AICO can freely explore curiosity in these domains
          </Typography>
        </Paper>
      )}
    </Box>
  );
};
