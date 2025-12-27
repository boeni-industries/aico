import React from 'react';
import { Box, Paper, Typography, Chip, LinearProgress } from '@mui/material';
import SchoolIcon from '@mui/icons-material/School';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import LightbulbIcon from '@mui/icons-material/Lightbulb';
import AutoFixHighIcon from '@mui/icons-material/AutoFixHigh';

interface Lesson {
  lesson_id: string;
  title: string;
  category: string;
  confidence: number;
  applied_count: number;
  created_at: string;
}

interface ReflectionStats {
  total_reflections: number;
  reflections_7d: number;
  lessons_learned: number;
  lessons_applied: number;
  avg_confidence: number;
}

interface LearningDashboardProps {
  reflectionStats?: ReflectionStats;
  recentLessons?: Lesson[];
  loading?: boolean;
}

export const LearningDashboard: React.FC<LearningDashboardProps> = ({
  reflectionStats,
  recentLessons = [],
  loading,
}) => {
  if (loading) {
    return (
      <Typography variant="body2" color="text.secondary">
        Loading learning data...
      </Typography>
    );
  }

  // Default stats if not provided
  const stats: ReflectionStats = reflectionStats || {
    total_reflections: 0,
    reflections_7d: 0,
    lessons_learned: 0,
    lessons_applied: 0,
    avg_confidence: 0,
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {/* Reflection Statistics */}
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', md: 'repeat(4, 1fr)' },
          gap: 3,
        }}
      >
        <Paper
          sx={{
            p: 3,
            borderRadius: '20px',
            border: '1.5px solid',
            borderColor: 'divider',
            bgcolor: 'background.paper',
            backdropFilter: 'blur(20px)',
            boxShadow: '0 8px 32px rgba(0,0,0,0.06)',
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2 }}>
            <Box
              sx={{
                width: 40,
                height: 40,
                borderRadius: '12px',
                bgcolor: 'rgba(184, 161, 234, 0.12)',
                border: '1.5px solid',
                borderColor: 'rgba(184, 161, 234, 0.3)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <AutoFixHighIcon sx={{ fontSize: 20, color: '#B8A1EA' }} />
            </Box>
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
              Reflections
            </Typography>
          </Box>
          <Typography variant="h4" sx={{ fontWeight: 700, fontSize: '2rem', mb: 0.5 }}>
            {stats.reflections_7d}
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.75rem' }}>
            Last 7 days
          </Typography>
        </Paper>

        <Paper
          sx={{
            p: 3,
            borderRadius: '20px',
            border: '1.5px solid',
            borderColor: 'divider',
            bgcolor: 'background.paper',
            backdropFilter: 'blur(20px)',
            boxShadow: '0 8px 32px rgba(0,0,0,0.06)',
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2 }}>
            <Box
              sx={{
                width: 40,
                height: 40,
                borderRadius: '12px',
                bgcolor: 'rgba(16, 185, 129, 0.12)',
                border: '1.5px solid',
                borderColor: 'rgba(16, 185, 129, 0.3)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <SchoolIcon sx={{ fontSize: 20, color: '#10B981' }} />
            </Box>
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
              Lessons
            </Typography>
          </Box>
          <Typography variant="h4" sx={{ fontWeight: 700, fontSize: '2rem', mb: 0.5 }}>
            {stats.lessons_learned}
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.75rem' }}>
            Total learned
          </Typography>
        </Paper>

        <Paper
          sx={{
            p: 3,
            borderRadius: '20px',
            border: '1.5px solid',
            borderColor: 'divider',
            bgcolor: 'background.paper',
            backdropFilter: 'blur(20px)',
            boxShadow: '0 8px 32px rgba(0,0,0,0.06)',
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2 }}>
            <Box
              sx={{
                width: 40,
                height: 40,
                borderRadius: '12px',
                bgcolor: 'rgba(59, 130, 246, 0.12)',
                border: '1.5px solid',
                borderColor: 'rgba(59, 130, 246, 0.3)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <LightbulbIcon sx={{ fontSize: 20, color: '#3B82F6' }} />
            </Box>
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
              Applied
            </Typography>
          </Box>
          <Typography variant="h4" sx={{ fontWeight: 700, fontSize: '2rem', mb: 0.5 }}>
            {stats.lessons_applied}
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.75rem' }}>
            Active insights
          </Typography>
        </Paper>

        <Paper
          sx={{
            p: 3,
            borderRadius: '20px',
            border: '1.5px solid',
            borderColor: 'divider',
            bgcolor: 'background.paper',
            backdropFilter: 'blur(20px)',
            boxShadow: '0 8px 32px rgba(0,0,0,0.06)',
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2 }}>
            <Box
              sx={{
                width: 40,
                height: 40,
                borderRadius: '12px',
                bgcolor: 'rgba(245, 158, 11, 0.12)',
                border: '1.5px solid',
                borderColor: 'rgba(245, 158, 11, 0.3)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <TrendingUpIcon sx={{ fontSize: 20, color: '#F59E0B' }} />
            </Box>
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
              Confidence
            </Typography>
          </Box>
          <Typography variant="h4" sx={{ fontWeight: 700, fontSize: '2rem', mb: 0.5 }}>
            {Math.round(stats.avg_confidence * 100)}%
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.75rem' }}>
            Average
          </Typography>
        </Paper>
      </Box>

      {/* Recent Lessons */}
      {recentLessons.length > 0 && (
        <Box>
          <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
            Recent Lessons
          </Typography>

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {recentLessons.map((lesson) => {
              const confidencePercent = Math.round(lesson.confidence * 100);
              const confidenceColor =
                confidencePercent >= 80
                  ? '#10B981'
                  : confidencePercent >= 60
                  ? '#F59E0B'
                  : '#9CA3AF';

              return (
                <Paper
                  key={lesson.lesson_id}
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
                        bgcolor: confidenceColor,
                        mt: 0.75,
                        flexShrink: 0,
                        boxShadow: `0 0 12px ${confidenceColor}40`,
                      }}
                    />
                    <Box sx={{ flexGrow: 1 }}>
                      <Typography
                        variant="subtitle2"
                        sx={{ fontWeight: 600, fontSize: '0.95rem', mb: 0.5 }}
                      >
                        {lesson.title}
                      </Typography>
                      <Box sx={{ display: 'flex', gap: 1, mb: 1.5 }}>
                        <Chip
                          label={lesson.category}
                          size="small"
                          sx={{
                            bgcolor: 'background.default',
                            fontSize: '0.7rem',
                            height: 22,
                            fontWeight: 600,
                          }}
                        />
                        <Chip
                          label={`Applied ${lesson.applied_count}x`}
                          size="small"
                          sx={{
                            bgcolor: 'rgba(59, 130, 246, 0.12)',
                            color: '#3B82F6',
                            border: '1px solid',
                            borderColor: 'rgba(59, 130, 246, 0.3)',
                            fontSize: '0.7rem',
                            height: 22,
                            fontWeight: 600,
                          }}
                        />
                      </Box>
                    </Box>
                  </Box>

                  <Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                      <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                        Confidence
                      </Typography>
                      <Typography
                        variant="caption"
                        sx={{
                          fontSize: '0.7rem',
                          fontWeight: 600,
                          fontFamily: 'monospace',
                          color: confidenceColor,
                        }}
                      >
                        {confidencePercent}%
                      </Typography>
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={confidencePercent}
                      sx={{
                        height: 4,
                        borderRadius: 2,
                        bgcolor: 'background.default',
                        '& .MuiLinearProgress-bar': {
                          bgcolor: confidenceColor,
                          borderRadius: 2,
                        },
                      }}
                    />
                  </Box>
                </Paper>
              );
            })}
          </Box>
        </Box>
      )}

      {recentLessons.length === 0 && (
        <Paper
          sx={{
            p: 4,
            borderRadius: '20px',
            border: '1.5px solid',
            borderColor: 'divider',
            bgcolor: 'background.paper',
            backdropFilter: 'blur(12px)',
            textAlign: 'center',
          }}
        >
          <SchoolIcon sx={{ fontSize: 48, color: 'text.secondary', opacity: 0.5, mb: 2 }} />
          <Typography variant="body2" color="text.secondary">
            No lessons learned yet. Lessons will appear here as AICO reflects on experiences.
          </Typography>
        </Paper>
      )}
    </Box>
  );
};
