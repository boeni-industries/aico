import React from 'react';
import { Box, Typography, Chip } from '@mui/material';
import { TrendingUp as TrendingUpIcon, Brain as PsychologyIcon, GraduationCap as SchoolIcon, Heart as FavoriteIcon } from 'lucide-react';

interface AgencyCardProps {
  activeGoals: number;
  primaryFocus?: string;
  curiosityLevel: 'low' | 'medium' | 'high';
  lessonsLearned: number;
  onClick?: () => void;
}

const curiosityColors = {
  low: { bg: 'rgba(148, 163, 184, 0.12)', text: '#94A3B8', border: 'rgba(148, 163, 184, 0.3)' },
  medium: { bg: 'rgba(245, 158, 11, 0.12)', text: '#F59E0B', border: 'rgba(245, 158, 11, 0.3)' },
  high: { bg: 'rgba(16, 185, 129, 0.12)', text: '#10B981', border: 'rgba(16, 185, 129, 0.3)' },
};

export const AgencyCard: React.FC<AgencyCardProps> = ({
  activeGoals,
  primaryFocus,
  curiosityLevel,
  lessonsLearned,
  onClick,
}) => {
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
              bgcolor: 'rgba(139, 92, 246, 0.12)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <TrendingUpIcon sx={{ color: '#8B5CF6', fontSize: 24 }} />
          </Box>
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 700, fontSize: '1.1rem' }}>
              Agency
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.75rem' }}>
              Autonomous Behavior
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

      {/* Primary Focus */}
      {primaryFocus && (
        <Box
          sx={{
            p: 2,
            mb: 2.5,
            borderRadius: '12px',
            bgcolor: 'rgba(139, 92, 246, 0.08)',
            border: '1px solid',
            borderColor: 'rgba(139, 92, 246, 0.2)',
          }}
        >
          <Typography variant="caption" sx={{ fontSize: '0.7rem', color: 'text.secondary', mb: 0.5, display: 'block' }}>
            PRIMARY FOCUS
          </Typography>
          <Typography variant="body2" sx={{ fontWeight: 600, color: '#8B5CF6', fontSize: '0.9rem' }}>
            {primaryFocus}
          </Typography>
        </Box>
      )}

      {/* Metrics Grid */}
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: 2,
          mb: 2.5,
        }}
      >
        {/* Active Goals */}
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
            <TrendingUpIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
              Goals
            </Typography>
          </Box>
          <Typography variant="h5" sx={{ fontWeight: 700, color: 'text.primary' }}>
            {activeGoals}
          </Typography>
        </Box>

        {/* Curiosity Level */}
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
            <PsychologyIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
              Curiosity
            </Typography>
          </Box>
          <Chip
            label={curiosityLevel.toUpperCase()}
            size="small"
            sx={{
              bgcolor: curiosityColors[curiosityLevel].bg,
              color: curiosityColors[curiosityLevel].text,
              border: '1px solid',
              borderColor: curiosityColors[curiosityLevel].border,
              fontWeight: 700,
              fontSize: '0.7rem',
              height: 22,
              mt: 0.5,
            }}
          />
        </Box>

        {/* Lessons Learned */}
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
            <SchoolIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
              Lessons
            </Typography>
          </Box>
          <Typography variant="h5" sx={{ fontWeight: 700, color: 'text.primary' }}>
            {lessonsLearned}
          </Typography>
        </Box>
      </Box>

      {/* Footer Stats */}
      <Box
        sx={{
          display: 'flex',
          gap: 2,
          mt: 2.5,
          pt: 2.5,
          borderTop: '1px solid',
          borderColor: 'divider',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
          <FavoriteIcon sx={{ fontSize: 14, color: '#EC4899' }} />
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
            Value-aligned
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
          <PsychologyIcon sx={{ fontSize: 14, color: '#3B82F6' }} />
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
            Learning actively
          </Typography>
        </Box>
      </Box>
    </Box>
  );
};
