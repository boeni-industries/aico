/**
 * Styled Tooltip Component
 * 
 * Provides consistent, beautiful tooltip styling across the application
 */

import React from 'react';
import { Tooltip, TooltipProps, styled } from '@mui/material';

export const StyledTooltip = styled(({ className, ...props }: TooltipProps) => (
  <Tooltip {...props} classes={{ popper: className }} />
))(({ theme }) => ({
  '& .MuiTooltip-tooltip': {
    backgroundColor: 'rgba(17, 24, 39, 0.95)',
    backdropFilter: 'blur(12px)',
    color: '#E5E7EB',
    fontSize: '0.8rem',
    fontWeight: 400,
    lineHeight: 1.6,
    padding: '12px 16px',
    borderRadius: '10px',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4), 0 2px 8px rgba(0, 0, 0, 0.2)',
    maxWidth: 320,
  },
  '& .MuiTooltip-arrow': {
    color: 'rgba(17, 24, 39, 0.95)',
    '&::before': {
      border: '1px solid rgba(255, 255, 255, 0.1)',
      boxShadow: '0 2px 8px rgba(0, 0, 0, 0.2)',
    },
  },
}));
