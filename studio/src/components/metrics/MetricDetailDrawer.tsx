import React, { useState, useEffect } from 'react';
import { Box, Typography, Tabs, Tab, CircularProgress, Alert } from '@mui/material';
import { BarChart3, TrendingUp, AlertCircle } from 'lucide-react';
import { DetailDrawer } from '../common/DetailDrawer';
import { httpJson } from '../../api/http';

interface BreakdownItem {
  name: string;
  value: number;
  count: number;
  percentage: number;
  avg_latency?: number;
  error_rate?: number;
}

interface MetricBreakdown {
  metric_type: string;
  breakdown_by: string;
  time_window: string;
  total_value: number;
  items: BreakdownItem[];
}

interface MetricDetailDrawerProps {
  open: boolean;
  onClose: () => void;
  metricType: 'requests' | 'latency' | 'errors';
  metricLabel: string;
  metricUnit: string;
  metricColor: string;
}

type BreakdownType = 'service' | 'category' | 'endpoint' | 'method' | 'status';
type TimeWindow = '1h' | '24h' | '7d';

export const MetricDetailDrawer: React.FC<MetricDetailDrawerProps> = ({
  open,
  onClose,
  metricType,
  metricLabel,
  metricUnit,
  metricColor,
}) => {
  const [breakdownBy, setBreakdownBy] = useState<BreakdownType>('service');
  const [timeWindow, setTimeWindow] = useState<TimeWindow>('24h');
  const [data, setData] = useState<MetricBreakdown | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Available breakdown types based on metric type
  const getBreakdownOptions = (): BreakdownType[] => {
    switch (metricType) {
      case 'requests':
        return ['service', 'category', 'endpoint', 'method', 'status'];
      case 'latency':
        return ['service', 'category', 'endpoint', 'method'];
      case 'errors':
        return ['service', 'category', 'endpoint', 'status'];
      default:
        return ['service', 'category', 'endpoint'];
    }
  };

  const breakdownOptions = getBreakdownOptions();

  // Fetch breakdown data
  useEffect(() => {
    if (!open) return;

    const fetchData = async () => {
      setLoading(true);
      setError(null);

      try {
        const result = await httpJson<MetricBreakdown>({
          method: 'GET',
          path: `/system/metrics/drilldown/${metricType}?by=${breakdownBy}&window=${timeWindow}`,
        });
        setData(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load breakdown data');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [open, metricType, breakdownBy, timeWindow]);

  // Format value based on metric type
  const formatValue = (value: number): string => {
    switch (metricType) {
      case 'requests':
        return `${value.toFixed(2)} req/s`;
      case 'latency':
        return `${value.toFixed(1)} ms`;
      case 'errors':
        return `${value.toFixed(2)}%`;
      default:
        return value.toFixed(2);
    }
  };

  // Get color for bar based on metric type and value
  const getBarColor = (item: BreakdownItem): string => {
    if (metricType === 'errors') {
      // Red gradient for errors
      return item.error_rate && item.error_rate > 5 ? '#EF4444' : '#F59E0B';
    } else if (metricType === 'latency') {
      // Purple gradient for latency
      return item.value > 500 ? '#A78BFA' : '#C4B5FD';
    } else {
      // Blue gradient for requests
      return '#60A5FA';
    }
  };

  return (
    <DetailDrawer
      open={open}
      onClose={onClose}
      title={`${metricLabel} Breakdown`}
      subtitle={
        <Box sx={{ display: 'flex', gap: 1, mt: 0.5 }}>
          {['1h', '24h', '7d'].map((window) => (
            <Box
              key={window}
              onClick={() => setTimeWindow(window as TimeWindow)}
              sx={{
                px: 1.5,
                py: 0.5,
                borderRadius: '6px',
                fontSize: '0.75rem',
                fontWeight: 600,
                cursor: 'pointer',
                bgcolor: timeWindow === window ? `${metricColor}20` : 'rgba(255, 255, 255, 0.05)',
                border: '1px solid',
                borderColor: timeWindow === window ? `${metricColor}80` : 'rgba(255, 255, 255, 0.1)',
                color: timeWindow === window ? metricColor : 'rgba(255, 255, 255, 0.6)',
                transition: 'all 0.2s',
                '&:hover': {
                  bgcolor: timeWindow === window ? `${metricColor}30` : 'rgba(255, 255, 255, 0.08)',
                },
              }}
            >
              {window}
            </Box>
          ))}
        </Box>
      }
      width={700}
    >
      {/* Breakdown Type Tabs */}
      <Box sx={{ borderBottom: '1px solid rgba(255, 255, 255, 0.08)', mb: 3 }}>
        <Tabs
          value={breakdownBy}
          onChange={(_, newValue) => setBreakdownBy(newValue)}
          sx={{
            '& .MuiTab-root': {
              color: 'rgba(255, 255, 255, 0.6)',
              textTransform: 'capitalize',
              fontSize: '0.875rem',
              fontWeight: 600,
            },
            '& .Mui-selected': {
              color: metricColor,
            },
            '& .MuiTabs-indicator': {
              backgroundColor: metricColor,
            },
          }}
        >
          {breakdownOptions.map((option) => (
            <Tab key={option} label={option} value={option} />
          ))}
        </Tabs>
      </Box>

      {/* Loading State */}
      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress size={40} />
        </Box>
      )}

      {/* Error State */}
      {error && !loading && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* Data Display */}
      {data && !loading && !error && (
        <>
          {/* Summary */}
          <Box
            sx={{
              p: 1.5,
              mb: 2,
              borderRadius: '8px',
              bgcolor: `${metricColor}15`,
              border: `1px solid ${metricColor}40`,
            }}
          >
            <Typography variant="caption" sx={{ color: 'rgba(255, 255, 255, 0.6)', fontSize: '0.7rem' }}>
              Total {metricLabel}
            </Typography>
            <Typography variant="h5" sx={{ fontWeight: 700, color: metricColor, my: 0.5 }}>
              {formatValue(data.total_value)}
            </Typography>
            <Typography variant="caption" sx={{ color: 'rgba(255, 255, 255, 0.5)', fontSize: '0.65rem' }}>
              {data.items.length} {breakdownBy}s • Last {timeWindow}
            </Typography>
          </Box>

          {/* Breakdown Items */}
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {data.items.map((item, index) => {
              const maxValue = Math.max(...data.items.map((i) => i.value));
              const barWidth = (item.value / maxValue) * 100;

              return (
                <Box
                  key={`${item.name}-${index}`}
                  sx={{
                    p: 1.5,
                    borderRadius: '6px',
                    bgcolor: 'rgba(255, 255, 255, 0.03)',
                    border: '1px solid rgba(255, 255, 255, 0.08)',
                    transition: 'all 0.2s',
                    '&:hover': {
                      bgcolor: 'rgba(255, 255, 255, 0.05)',
                      borderColor: `${metricColor}40`,
                    },
                  }}
                >
                  {/* Header */}
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                    <Typography variant="body2" sx={{ fontWeight: 600, fontSize: '0.85rem', color: 'rgba(255, 255, 255, 0.9)' }}>
                      {item.name}
                    </Typography>
                    <Typography variant="h6" sx={{ fontWeight: 700, fontSize: '1.1rem', color: metricColor }}>
                      {formatValue(item.value)}
                    </Typography>
                  </Box>

                  {/* Progress Bar */}
                  <Box
                    sx={{
                      width: '100%',
                      height: '6px',
                      bgcolor: 'rgba(255, 255, 255, 0.05)',
                      borderRadius: '3px',
                      overflow: 'hidden',
                      mb: 1,
                    }}
                  >
                    <Box
                      sx={{
                        width: `${barWidth}%`,
                        height: '100%',
                        bgcolor: metricColor,
                        borderRadius: '3px',
                        transition: 'width 0.3s ease',
                      }}
                    />
                  </Box>

                  {/* Stats */}
                  <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                    <Box>
                      <Typography variant="caption" sx={{ color: 'rgba(255, 255, 255, 0.5)', fontSize: '0.65rem' }}>
                        Requests
                      </Typography>
                      <Typography variant="body2" sx={{ fontWeight: 600, fontSize: '0.8rem', color: 'rgba(255, 255, 255, 0.8)' }}>
                        {item.count.toLocaleString()}
                      </Typography>
                    </Box>
                    <Box>
                      <Typography variant="caption" sx={{ color: 'rgba(255, 255, 255, 0.5)', fontSize: '0.65rem' }}>
                        % of Total
                      </Typography>
                      <Typography variant="body2" sx={{ fontWeight: 600, fontSize: '0.8rem', color: 'rgba(255, 255, 255, 0.8)' }}>
                        {item.percentage.toFixed(1)}%
                      </Typography>
                    </Box>
                    {item.avg_latency !== undefined && item.avg_latency !== null && (
                      <Box>
                        <Typography variant="caption" sx={{ color: 'rgba(255, 255, 255, 0.5)', fontSize: '0.65rem' }}>
                          Avg Latency
                        </Typography>
                        <Typography variant="body2" sx={{ fontWeight: 600, fontSize: '0.8rem', color: 'rgba(255, 255, 255, 0.8)' }}>
                          {item.avg_latency.toFixed(1)}ms
                        </Typography>
                      </Box>
                    )}
                    {item.error_rate !== undefined && item.error_rate !== null && (
                      <Box>
                        <Typography variant="caption" sx={{ color: 'rgba(255, 255, 255, 0.5)', fontSize: '0.65rem' }}>
                          Error Rate
                        </Typography>
                        <Typography
                          variant="body2"
                          sx={{
                            fontWeight: 600,
                            fontSize: '0.8rem',
                            color: item.error_rate > 5 ? '#EF4444' : 'rgba(255, 255, 255, 0.8)',
                          }}
                        >
                          {item.error_rate.toFixed(2)}%
                        </Typography>
                      </Box>
                    )}
                  </Box>
                </Box>
              );
            })}
          </Box>

          {/* Empty State */}
          {data.items.length === 0 && (
            <Box
              sx={{
                py: 8,
                textAlign: 'center',
                color: 'rgba(255, 255, 255, 0.5)',
              }}
            >
              <Typography variant="body1">No data available for this breakdown</Typography>
            </Box>
          )}
        </>
      )}
    </DetailDrawer>
  );
};
