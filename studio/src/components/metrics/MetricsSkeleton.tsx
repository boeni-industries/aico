import React from 'react';
import { Box, Paper, Typography } from '@mui/material';

export const MetricsSkeleton: React.FC = () => {
  return (
    <Box sx={{ p: 4 }}>
      {/* Hero Section Skeleton */}
      <Paper
        sx={{
          p: 4,
          mb: 4,
          borderRadius: '24px',
          bgcolor: 'rgba(255, 255, 255, 0.02)',
          backdropFilter: 'blur(12px)',
          border: '1px solid',
          borderColor: 'rgba(255, 255, 255, 0.08)',
          background: 'linear-gradient(135deg, rgba(184, 161, 234, 0.05) 0%, rgba(0, 0, 0, 0) 100%)',
        }}
      >
        <Box
          sx={{
            width: '200px',
            height: '24px',
            borderRadius: '8px',
            bgcolor: 'rgba(255, 255, 255, 0.05)',
            mb: 3,
            animation: 'pulse 1.5s ease-in-out infinite',
            '@keyframes pulse': {
              '0%, 100%': { opacity: 0.4 },
              '50%': { opacity: 0.8 },
            },
          }}
        />
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
          {/* Gauge Skeleton */}
          <Box
            sx={{
              width: 200,
              height: 200,
              borderRadius: '50%',
              bgcolor: 'rgba(255, 255, 255, 0.03)',
              border: '12px solid rgba(255, 255, 255, 0.05)',
              animation: 'pulse 1.5s ease-in-out infinite',
            }}
          />
          <Box sx={{ flex: 1, minWidth: 300 }}>
            {[1, 2, 3].map((i) => (
              <Box
                key={i}
                sx={{
                  height: '40px',
                  borderRadius: '8px',
                  bgcolor: 'rgba(255, 255, 255, 0.03)',
                  mb: 1.5,
                  animation: 'pulse 1.5s ease-in-out infinite',
                  animationDelay: `${i * 0.1}s`,
                }}
              />
            ))}
          </Box>
        </Box>
      </Paper>

      {/* Metric Cards Section */}
      <Box
        sx={{
          width: '180px',
          height: '16px',
          borderRadius: '6px',
          bgcolor: 'rgba(255, 255, 255, 0.05)',
          mb: 2,
          animation: 'pulse 1.5s ease-in-out infinite',
        }}
      />
      <Box sx={{ display: 'flex', gap: 2, mb: 4, flexWrap: 'wrap' }}>
        {[1, 2, 3, 4].map((i) => (
          <Box
            key={i}
            sx={{
              flex: '1 1 calc(25% - 12px)',
              minWidth: 200,
              height: '120px',
              borderRadius: '16px',
              bgcolor: 'rgba(255, 255, 255, 0.02)',
              backdropFilter: 'blur(12px)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              p: 2.5,
              animation: 'pulse 1.5s ease-in-out infinite',
              animationDelay: `${i * 0.1}s`,
            }}
          >
            <Box
              sx={{
                width: '80px',
                height: '12px',
                borderRadius: '4px',
                bgcolor: 'rgba(255, 255, 255, 0.1)',
                mb: 2,
              }}
            />
            <Box
              sx={{
                width: '120px',
                height: '32px',
                borderRadius: '6px',
                bgcolor: 'rgba(255, 255, 255, 0.15)',
              }}
            />
          </Box>
        ))}
      </Box>

      {/* Another Section */}
      <Box
        sx={{
          width: '200px',
          height: '16px',
          borderRadius: '6px',
          bgcolor: 'rgba(255, 255, 255, 0.05)',
          mb: 2,
          animation: 'pulse 1.5s ease-in-out infinite',
        }}
      />
      <Box sx={{ display: 'flex', gap: 2, mb: 4, flexWrap: 'wrap' }}>
        {[1, 2, 3, 4].map((i) => (
          <Box
            key={i}
            sx={{
              flex: '1 1 calc(25% - 12px)',
              minWidth: 200,
              height: '120px',
              borderRadius: '16px',
              bgcolor: 'rgba(255, 255, 255, 0.02)',
              backdropFilter: 'blur(12px)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              animation: 'pulse 1.5s ease-in-out infinite',
              animationDelay: `${i * 0.1}s`,
            }}
          />
        ))}
      </Box>

      {/* Charts Section */}
      <Box sx={{ display: 'flex', gap: 3, mb: 4, flexWrap: 'wrap' }}>
        {[1, 2].map((i) => (
          <Box
            key={i}
            sx={{
              flex: '1 1 calc(50% - 12px)',
              minWidth: 300,
              height: '280px',
              borderRadius: '20px',
              bgcolor: 'rgba(255, 255, 255, 0.02)',
              backdropFilter: 'blur(12px)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              p: 3,
              animation: 'pulse 1.5s ease-in-out infinite',
              animationDelay: `${i * 0.15}s`,
            }}
          >
            <Box
              sx={{
                width: '140px',
                height: '140px',
                borderRadius: '50%',
                bgcolor: 'rgba(255, 255, 255, 0.05)',
                mx: 'auto',
                mt: 2,
              }}
            />
          </Box>
        ))}
      </Box>
    </Box>
  );
};
