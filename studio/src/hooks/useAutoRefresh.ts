/**
 * Custom hook for auto-refresh functionality
 * 
 * Provides centralized auto-refresh logic with:
 * - Configurable interval (default 5 seconds)
 * - Toggle on/off
 * - Manual refresh trigger
 * - Loading state management
 */

import { useState, useEffect, useCallback, useRef } from 'react';

export interface UseAutoRefreshOptions {
  /**
   * Function to call on each refresh
   */
  onRefresh: () => Promise<void>;
  
  /**
   * Refresh interval in milliseconds (default: 5000ms = 5s)
   */
  interval?: number;
  
  /**
   * Whether auto-refresh is enabled by default (default: true)
   */
  defaultEnabled?: boolean;
}

export interface UseAutoRefreshReturn {
  /**
   * Whether auto-refresh is currently enabled
   */
  autoRefreshEnabled: boolean;
  
  /**
   * Toggle auto-refresh on/off
   */
  toggleAutoRefresh: () => void;
  
  /**
   * Manually trigger a refresh
   */
  refresh: () => Promise<void>;
  
  /**
   * Whether a refresh is currently in progress
   */
  isRefreshing: boolean;
}

export function useAutoRefresh({
  onRefresh,
  interval = 5000,
  defaultEnabled = true,
}: UseAutoRefreshOptions): UseAutoRefreshReturn {
  const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(defaultEnabled);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const onRefreshRef = useRef(onRefresh);

  // Keep ref updated without triggering effects
  useEffect(() => {
    onRefreshRef.current = onRefresh;
  }, [onRefresh]);

  // Initial load
  useEffect(() => {
    const loadInitial = async () => {
      setIsRefreshing(true);
      try {
        await onRefreshRef.current();
      } catch (err) {
        console.error('Initial refresh failed:', err);
      } finally {
        setIsRefreshing(false);
      }
    };
    loadInitial();
  }, []); // Only run once on mount

  // Auto-refresh interval
  useEffect(() => {
    if (!autoRefreshEnabled) return;

    const intervalId = setInterval(async () => {
      try {
        await onRefreshRef.current();
      } catch (err) {
        // Silent error during auto-refresh
        console.debug('Auto-refresh failed:', err);
      }
    }, interval);

    return () => clearInterval(intervalId);
  }, [autoRefreshEnabled, interval]);

  const toggleAutoRefresh = useCallback(() => {
    setAutoRefreshEnabled(prev => !prev);
  }, []);

  const refresh = useCallback(async () => {
    setIsRefreshing(true);
    try {
      await onRefreshRef.current();
    } catch (err) {
      console.error('Manual refresh failed:', err);
      throw err;
    } finally {
      setIsRefreshing(false);
    }
  }, []);

  return {
    autoRefreshEnabled,
    toggleAutoRefresh,
    refresh,
    isRefreshing,
  };
}
