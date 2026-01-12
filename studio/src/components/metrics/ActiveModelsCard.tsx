import React from 'react';
import { Box, Typography, Chip } from '@mui/material';
import { StyledTooltip } from '../common/StyledTooltip';
import { Info } from 'lucide-react';

interface ActiveModelsCardProps {
  modelCount: number;
  modelUsage: Record<string, number>;
  tooltip?: string;
}

export const ActiveModelsCard: React.FC<ActiveModelsCardProps> = ({
  modelCount,
  modelUsage,
  tooltip,
}) => {
  // Extract model names and sort by usage
  const models = Object.entries(modelUsage)
    .sort(([, a], [, b]) => b - a)
    .map(([name, count]) => ({ name, count }));

  return (
    <Box
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        p: 2.5,
        borderRadius: '16px',
        bgcolor: 'rgba(255, 255, 255, 0.02)',
        backdropFilter: 'blur(12px)',
        border: '1px solid',
        borderColor: 'rgba(255, 255, 255, 0.08)',
        transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        '&:hover': {
          borderColor: '#A78BFA40',
          boxShadow: '0 8px 32px #A78BFA20',
        },
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1.5 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <Typography
            variant="caption"
            sx={{
              fontSize: '0.7rem',
              fontWeight: 600,
              letterSpacing: '0.1em',
              textTransform: 'uppercase',
              color: 'text.secondary',
            }}
          >
            Models (24h)
          </Typography>
          {tooltip && (
            <StyledTooltip title={tooltip} arrow>
              <Info size={12} style={{ color: 'rgba(255, 255, 255, 0.3)', cursor: 'help' }} />
            </StyledTooltip>
          )}
        </Box>
      </Box>
      
      <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1, mb: 2 }}>
        <Typography
          variant="h4"
          sx={{
            fontSize: '2rem',
            fontWeight: 700,
            color: '#A78BFA',
            lineHeight: 1,
          }}
        >
          {modelCount}
        </Typography>
        <Typography
          variant="caption"
          sx={{
            fontSize: '0.85rem',
            fontWeight: 600,
            color: 'text.secondary',
          }}
        >
          models
        </Typography>
      </Box>

      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, mt: 'auto' }}>
        {models.map(({ name, count }) => (
          <Box
            key={name}
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              p: 1,
              borderRadius: '8px',
              bgcolor: 'rgba(167, 139, 250, 0.1)',
              border: '1px solid rgba(167, 139, 250, 0.2)',
            }}
          >
            <Typography
              variant="caption"
              sx={{
                fontSize: '0.75rem',
                fontWeight: 600,
                color: '#A78BFA',
                fontFamily: 'monospace',
              }}
            >
              {name}
            </Typography>
            <Typography
              variant="caption"
              sx={{
                fontSize: '0.7rem',
                fontWeight: 500,
                color: 'rgba(255, 255, 255, 0.5)',
              }}
            >
              {count.toLocaleString()} req
            </Typography>
          </Box>
        ))}
      </Box>
    </Box>
  );
};
