import React from 'react';
import { Box, Typography, Chip, Paper } from '@mui/material';
import {
  Memory as MemoryIcon,
  Storage as StorageIcon,
  AccountTree as GraphIcon,
  AutoAwesome as AmsIcon,
  PhotoAlbum as AlbumIcon,
  ArrowForward as ArrowIcon,
} from '@mui/icons-material';

interface MemoryTier {
  key: string;
  label: string;
  icon: React.ReactNode;
  count: string;
  lastActivity: string;
  health: 'healthy' | 'degraded' | 'attention';
  color: string;
}

interface MemorySystemMapProps {
  tiers: MemoryTier[];
  onTierClick: (key: string) => void;
}

const healthColors = {
  healthy: { bg: 'rgba(16, 185, 129, 0.12)', text: '#10B981', border: 'rgba(16, 185, 129, 0.3)' },
  degraded: { bg: 'rgba(245, 158, 11, 0.12)', text: '#F59E0B', border: 'rgba(245, 158, 11, 0.3)' },
  attention: { bg: 'rgba(239, 68, 68, 0.12)', text: '#EF4444', border: 'rgba(239, 68, 68, 0.3)' },
};

export const MemorySystemMap: React.FC<MemorySystemMapProps> = ({ tiers, onTierClick }) => {
  return (
    <Box
      sx={{
        p: 3,
        borderRadius: '20px',
        bgcolor: 'rgba(255, 255, 255, 0.02)',
        backdropFilter: 'blur(12px)',
        border: '1px solid',
        borderColor: 'divider',
      }}
    >
      <Typography
        variant="subtitle2"
        sx={{
          fontWeight: 600,
          mb: 3,
          textTransform: 'uppercase',
          fontSize: '0.75rem',
          letterSpacing: '0.1em',
          color: 'text.secondary',
        }}
      >
        Memory Architecture
      </Typography>

      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 2,
          overflowX: 'auto',
          pb: 1,
        }}
      >
        {tiers.map((tier, index) => (
          <React.Fragment key={tier.key}>
            <Paper
              onClick={() => onTierClick(tier.key)}
              sx={{
                p: 2.5,
                minWidth: 200,
                borderRadius: '16px',
                border: '1.5px solid',
                borderColor: tier.color + '40',
                bgcolor: 'background.paper',
                cursor: 'pointer',
                transition: 'all 0.2s ease-in-out',
                '&:hover': {
                  boxShadow: `0 8px 24px ${tier.color}20`,
                  borderColor: tier.color,
                },
              }}
            >
              {/* Icon & Label */}
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2 }}>
                <Box
                  sx={{
                    width: 36,
                    height: 36,
                    borderRadius: '10px',
                    bgcolor: tier.color + '15',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  {tier.icon}
                </Box>
                <Typography variant="subtitle2" sx={{ fontWeight: 600, fontSize: '0.85rem' }}>
                  {tier.label}
                </Typography>
              </Box>

              {/* Count */}
              <Typography variant="h6" sx={{ fontWeight: 700, mb: 1, color: tier.color }}>
                {tier.count}
              </Typography>

              {/* Last Activity */}
              <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', display: 'block', mb: 1.5 }}>
                {tier.lastActivity}
              </Typography>

              {/* Health Badge */}
              <Chip
                label={tier.health.toUpperCase()}
                size="small"
                sx={{
                  bgcolor: healthColors[tier.health].bg,
                  color: healthColors[tier.health].text,
                  border: '1px solid',
                  borderColor: healthColors[tier.health].border,
                  fontWeight: 700,
                  fontSize: '0.65rem',
                  height: 20,
                }}
              />
            </Paper>

            {/* Arrow between tiers */}
            {index < tiers.length - 1 && (
              <ArrowIcon sx={{ color: 'text.disabled', fontSize: 28, flexShrink: 0 }} />
            )}
          </React.Fragment>
        ))}
      </Box>
    </Box>
  );
};
