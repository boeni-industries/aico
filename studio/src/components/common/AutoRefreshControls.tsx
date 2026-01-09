/**
 * Auto-Refresh Controls Component
 * 
 * Reusable UI controls for auto-refresh functionality
 */

import React from 'react';
import { IconButton, Tooltip, Stack } from '@mui/material';
import { RefreshCw as RefreshIcon, RotateCw as AutorenewIcon } from 'lucide-react';

export interface AutoRefreshControlsProps {
  /**
   * Whether auto-refresh is currently enabled
   */
  autoRefreshEnabled: boolean;
  
  /**
   * Callback to toggle auto-refresh
   */
  onToggleAutoRefresh: () => void;
  
  /**
   * Callback for manual refresh
   */
  onRefresh: () => void;
  
  /**
   * Whether a refresh is currently in progress
   */
  isRefreshing?: boolean;
  
  /**
   * Refresh interval in seconds (for tooltip display)
   */
  intervalSeconds?: number;
}

export const AutoRefreshControls: React.FC<AutoRefreshControlsProps> = ({
  autoRefreshEnabled,
  onToggleAutoRefresh,
  onRefresh,
  isRefreshing = false,
  intervalSeconds = 5,
}) => {
  return (
    <Stack direction="row" spacing={1} alignItems="center">
      <Tooltip 
        title={autoRefreshEnabled 
          ? `Auto-refresh enabled (${intervalSeconds}s)` 
          : 'Auto-refresh disabled'
        }
      >
        <IconButton
          size="small"
          onClick={onToggleAutoRefresh}
          sx={{
            color: autoRefreshEnabled ? 'primary.main' : 'text.secondary',
            bgcolor: autoRefreshEnabled ? 'primary.lighter' : 'transparent',
            '&:hover': { 
              bgcolor: autoRefreshEnabled ? 'primary.light' : 'action.hover',
            },
            border: autoRefreshEnabled ? '2px solid' : '1px solid',
            borderColor: autoRefreshEnabled ? 'primary.main' : 'divider',
          }}
        >
          <AutorenewIcon fontSize="small" />
        </IconButton>
      </Tooltip>
      
      <Tooltip title={isRefreshing ? "Refreshing..." : "Refresh now"}>
        <span>
          <IconButton
            size="small"
            onClick={onRefresh}
            disabled={isRefreshing}
            sx={{ '&:hover': { bgcolor: 'action.hover' } }}
          >
            <RefreshIcon fontSize="small" />
          </IconButton>
        </span>
      </Tooltip>
    </Stack>
  );
};
