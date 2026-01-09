import React, { useState, useEffect } from 'react';
import { Box, Typography, Paper, LinearProgress } from '@mui/material';
import { CircularGauge } from '../components/metrics/CircularGauge';
import { DonutChart } from '../components/metrics/DonutChart';
import { MetricCard } from '../components/metrics/MetricCard';
import { MetricsSkeleton } from '../components/metrics/MetricsSkeleton';
import { MetricDetailDrawer } from '../components/metrics/MetricDetailDrawer';
import { httpJson } from '../api/http';

interface MetricsData {
  timestamp: string;
  gateway: any;
  modelservice: any;
  memory: any;
  scheduler: any;
  message_bus: any;
  system_health: any;
}

type DrillDownMetric = {
  type: 'requests' | 'latency' | 'errors';
  label: string;
  unit: string;
  color: string;
} | null;

export const MetricsPage: React.FC = () => {
  const [metrics, setMetrics] = useState<MetricsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [drillDownMetric, setDrillDownMetric] = useState<DrillDownMetric>(null);

  const fetchMetrics = async () => {
    try {
      const startTime = performance.now();
      const data = await httpJson<MetricsData>({
        method: 'GET',
        path: '/system/metrics/all',
      });
      const endTime = performance.now();
      console.log(`[Metrics] Loaded in ${(endTime - startTime).toFixed(0)}ms`);
      
      setMetrics(data);
      setError(null);
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch metrics:', error);
      setError(error instanceof Error ? error.message : 'Failed to load metrics');
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 5000);
    return () => clearInterval(interval);
  }, []);

  // Show skeleton on initial load
  if (loading && !metrics) {
    return <MetricsSkeleton />;
  }

  // Show error state
  if (error && !metrics) {
    return (
      <Box sx={{ p: 4 }}>
        <Paper
          sx={{
            p: 4,
            borderRadius: '16px',
            bgcolor: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
          }}
        >
          <Typography variant="h6" sx={{ color: '#EF4444', mb: 1 }}>
            Failed to Load Metrics
          </Typography>
          <Typography variant="body2" sx={{ color: 'text.secondary' }}>
            {error}
          </Typography>
        </Paper>
      </Box>
    );
  }

  // Ensure all data is present before rendering
  if (!metrics?.gateway || !metrics?.modelservice || !metrics?.memory || !metrics?.scheduler || !metrics?.message_bus || !metrics?.system_health) {
    return <MetricsSkeleton />;
  }

  const { gateway, modelservice, memory, scheduler, message_bus, system_health } = metrics;

  const entityTypeData = memory?.entity_type_distribution 
    ? Object.entries(memory.entity_type_distribution).map(([label, value]) => ({
        label,
        value: value as number,
        color: getEntityColor(label),
      }))
    : [];

  const relationshipTypeData = memory?.relationship_type_distribution
    ? Object.entries(memory.relationship_type_distribution).map(([label, value]) => ({
        label,
        value: value as number,
        color: getRelationshipColor(label),
      }))
    : [];

  return (
    <Box sx={{ p: 4 }}>
      {/* Mock Data Disclaimer */}
      <Paper
        sx={{
          p: 2,
          mb: 3,
          borderRadius: '12px',
          bgcolor: 'rgba(251, 191, 36, 0.1)',
          border: '1px solid rgba(251, 191, 36, 0.3)',
        }}
      >
        <Typography
          variant="body2"
          sx={{
            color: '#F59E0B',
            fontWeight: 500,
            display: 'flex',
            alignItems: 'center',
            gap: 1,
          }}
        >
          <span style={{ fontSize: '18px' }}>⚠️</span>
          <span>
            <strong>Development Notice:</strong> This dashboard currently displays mock data for demonstration purposes. 
            Metrics are being migrated to real telemetry data using OpenTelemetry instrumentation. 
            Real data will be available incrementally as each subsystem is instrumented.
          </span>
        </Typography>
      </Paper>

      {/* Hero Section - System Health */}
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
        <Typography
          variant="h5"
          sx={{
            mb: 3,
            fontWeight: 600,
            background: 'linear-gradient(135deg, #B8A1EA 0%, #00D9FF 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}
        >
          System Health Overview
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 6, flexWrap: 'wrap' }}>
          {/* Health Gauge */}
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <CircularGauge
              value={system_health.health_score}
              max={100}
              size={200}
              thickness={20}
              color={system_health.health_score > 90 ? '#10B981' : system_health.health_score > 70 ? '#F59E0B' : '#EF4444'}
              label="HEALTH"
              unit="%"
            />
            {system_health.critical_alerts > 0 && (
              <Box sx={{ mt: 2, px: 2, py: 0.5, borderRadius: '12px', bgcolor: 'rgba(239, 68, 68, 0.15)', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
                <Typography variant="caption" sx={{ color: '#EF4444', fontWeight: 600, fontSize: '0.7rem' }}>
                  {system_health.critical_alerts} CRITICAL ALERT{system_health.critical_alerts !== 1 ? 'S' : ''}
                </Typography>
              </Box>
            )}
            {system_health.warnings > 0 && system_health.critical_alerts === 0 && (
              <Box sx={{ mt: 2, px: 2, py: 0.5, borderRadius: '12px', bgcolor: 'rgba(245, 158, 11, 0.15)', border: '1px solid rgba(245, 158, 11, 0.3)' }}>
                <Typography variant="caption" sx={{ color: '#F59E0B', fontWeight: 600, fontSize: '0.7rem' }}>
                  {system_health.warnings} WARNING{system_health.warnings !== 1 ? 'S' : ''}
                </Typography>
              </Box>
            )}
          </Box>

          {/* Key Metrics Grid */}
          <Box sx={{ flex: 1, minWidth: 400 }}>
            <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 2, mb: 3 }}>
              <Box>
                <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.7rem', letterSpacing: '0.05em' }}>
                  UPTIME
                </Typography>
                <Typography variant="h6" sx={{ color: '#00D9FF', fontWeight: 700 }}>
                  {Math.floor(system_health.uptime_seconds / 3600)}h {Math.floor((system_health.uptime_seconds % 3600) / 60)}m
                </Typography>
              </Box>
              <Box>
                <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.7rem', letterSpacing: '0.05em' }}>
                  THROUGHPUT
                </Typography>
                <Typography variant="h6" sx={{ color: '#10B981', fontWeight: 700 }}>
                  {system_health.total_throughput.toFixed(1)} req/s
                </Typography>
              </Box>
              <Box>
                <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.7rem', letterSpacing: '0.05em' }}>
                  ERROR RATE
                </Typography>
                <Typography variant="h6" sx={{ color: system_health.system_error_rate < 1 ? '#10B981' : '#F59E0B', fontWeight: 700 }}>
                  {system_health.system_error_rate.toFixed(2)}%
                </Typography>
              </Box>
              <Box>
                <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.7rem', letterSpacing: '0.05em' }}>
                  AVG LATENCY
                </Typography>
                <Typography variant="h6" sx={{ color: '#A78BFA', fontWeight: 700 }}>
                  {system_health.avg_latency_ms.toFixed(1)} ms
                </Typography>
              </Box>
              <Box>
                <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.7rem', letterSpacing: '0.05em' }}>
                  ACTIVE SESSIONS
                </Typography>
                <Typography variant="h6" sx={{ color: '#EC4899', fontWeight: 700 }}>
                  {system_health.active_sessions}
                </Typography>
              </Box>
              <Box>
                <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.7rem', letterSpacing: '0.05em' }}>
                  QUEUE BACKLOG
                </Typography>
                <Typography variant="h6" sx={{ color: system_health.queue_backlog < 100 ? '#10B981' : '#F59E0B', fontWeight: 700 }}>
                  {system_health.queue_backlog}
                </Typography>
              </Box>
            </Box>

            {/* Resource Utilization */}
            <Typography variant="subtitle2" sx={{ mb: 1.5, fontWeight: 600, fontSize: '0.85rem', letterSpacing: '0.05em', textTransform: 'uppercase', color: 'text.secondary' }}>
              Resource Utilization
            </Typography>
            <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
              <Box sx={{ flex: 1 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                  <Typography variant="caption" sx={{ fontSize: '0.75rem' }}>CPU</Typography>
                  <Typography variant="caption" sx={{ fontSize: '0.75rem', fontWeight: 600 }}>
                    {system_health.cpu_percent.toFixed(1)}%
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={system_health.cpu_percent}
                  sx={{
                    height: 6,
                    borderRadius: 3,
                    bgcolor: 'rgba(255, 255, 255, 0.05)',
                    '& .MuiLinearProgress-bar': {
                      bgcolor: system_health.cpu_percent > 80 ? '#EF4444' : system_health.cpu_percent > 60 ? '#F59E0B' : '#10B981',
                      borderRadius: 3,
                    },
                  }}
                />
              </Box>
              <Box sx={{ flex: 1 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                  <Typography variant="caption" sx={{ fontSize: '0.75rem' }}>Memory</Typography>
                  <Typography variant="caption" sx={{ fontSize: '0.75rem', fontWeight: 600 }}>
                    {system_health.memory_percent.toFixed(1)}%
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={system_health.memory_percent}
                  sx={{
                    height: 6,
                    borderRadius: 3,
                    bgcolor: 'rgba(255, 255, 255, 0.05)',
                    '& .MuiLinearProgress-bar': {
                      bgcolor: system_health.memory_percent > 80 ? '#EF4444' : system_health.memory_percent > 60 ? '#F59E0B' : '#10B981',
                      borderRadius: 3,
                    },
                  }}
                />
              </Box>
              <Box sx={{ flex: 1 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                  <Typography variant="caption" sx={{ fontSize: '0.75rem' }}>Disk</Typography>
                  <Typography variant="caption" sx={{ fontSize: '0.75rem', fontWeight: 600 }}>
                    {system_health.disk_percent.toFixed(1)}%
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={system_health.disk_percent}
                  sx={{
                    height: 6,
                    borderRadius: 3,
                    bgcolor: 'rgba(255, 255, 255, 0.05)',
                    '& .MuiLinearProgress-bar': {
                      bgcolor: system_health.disk_percent > 80 ? '#EF4444' : system_health.disk_percent > 60 ? '#F59E0B' : '#10B981',
                      borderRadius: 3,
                    },
                  }}
                />
              </Box>
            </Box>
          </Box>

          {/* Component Status */}
          <Box sx={{ minWidth: 220 }}>
            <Typography variant="subtitle2" sx={{ mb: 1.5, fontWeight: 600, fontSize: '0.85rem', letterSpacing: '0.05em', textTransform: 'uppercase', color: 'text.secondary' }}>
              Components
            </Typography>
            {Object.entries(system_health.component_status).map(([name, status]: [string, any]) => (
              <Box
                key={name}
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  mb: 1,
                  p: 1.5,
                  borderRadius: '8px',
                  bgcolor: status.status === 'healthy' ? 'rgba(16, 185, 129, 0.05)' : status.status === 'warning' ? 'rgba(245, 158, 11, 0.05)' : 'rgba(239, 68, 68, 0.05)',
                  border: '1px solid',
                  borderColor: status.status === 'healthy' ? 'rgba(16, 185, 129, 0.2)' : status.status === 'warning' ? 'rgba(245, 158, 11, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Box
                    sx={{
                      width: 8,
                      height: 8,
                      borderRadius: '50%',
                      bgcolor: status.status === 'healthy' ? '#10B981' : status.status === 'warning' ? '#F59E0B' : '#EF4444',
                    }}
                  />
                  <Typography variant="caption" sx={{ fontSize: '0.75rem', fontWeight: 500 }}>
                    {name}
                  </Typography>
                </Box>
                <Typography variant="caption" sx={{ fontSize: '0.7rem', fontWeight: 700, color: status.status === 'healthy' ? '#10B981' : status.status === 'warning' ? '#F59E0B' : '#EF4444' }}>
                  {status.health}
                </Typography>
              </Box>
            ))}
          </Box>
        </Box>
      </Paper>

      {/* API Gateway Metrics */}
      <Typography
        variant="h6"
        sx={{
          mb: 2,
          fontWeight: 600,
          fontSize: '0.85rem',
          letterSpacing: '0.1em',
          textTransform: 'uppercase',
          color: 'text.secondary',
        }}
      >
        API Gateway Metrics
      </Typography>
      <Box sx={{ display: 'flex', gap: 2, mb: 4, flexWrap: 'wrap' }}>
        <Box sx={{ flex: '1 1 calc(25% - 12px)', minWidth: 200, minHeight: 120 }}>
          <MetricCard
            label="Requests/sec"
            value={gateway.requests_per_second.value.toFixed(1)}
            unit="req/s"
            trend={gateway.requests_per_second.trend}
            color="#00D9FF"
            dataSource="real"
            sparklineData={gateway.requests_per_second.sparkline_data}
            isNeutralMetric={true}
            avg_1h={gateway.requests_per_second.avg_1h}
            avg_24h={gateway.requests_per_second.avg_24h}
            avg_7d={gateway.requests_per_second.avg_7d}
            onClick={() => setDrillDownMetric({ type: 'requests', label: 'Requests/sec', unit: 'req/s', color: '#00D9FF' })}
          />
        </Box>
        <Box sx={{ flex: '1 1 calc(25% - 12px)', minWidth: 200, minHeight: 120 }}>
          <MetricCard
            label="Avg Response Time"
            value={gateway.avg_response_time.value.toFixed(1)}
            unit="ms"
            trend={gateway.avg_response_time.trend}
            color="#A78BFA"
            status={gateway.avg_response_time.status}
            dataSource="real"
            sparklineData={gateway.avg_response_time.sparkline_data}
            lowerIsBetter={true}
            avg_1h={gateway.avg_response_time.avg_1h}
            avg_24h={gateway.avg_response_time.avg_24h}
            avg_7d={gateway.avg_response_time.avg_7d}
            onClick={() => setDrillDownMetric({ type: 'latency', label: 'Avg Response Time', unit: 'ms', color: '#A78BFA' })}
          />
        </Box>
        <Box sx={{ flex: '1 1 calc(25% - 12px)', minWidth: 200, minHeight: 120 }}>
          <MetricCard
            label="Error Rate"
            value={gateway.error_rate.value.toFixed(2)}
            unit="%"
            trend={gateway.error_rate.trend}
            color="#F59E0B"
            status={gateway.error_rate.status}
            dataSource="real"
            sparklineData={gateway.error_rate.sparkline_data}
            lowerIsBetter={true}
            avg_1h={gateway.error_rate.avg_1h}
            avg_24h={gateway.error_rate.avg_24h}
            avg_7d={gateway.error_rate.avg_7d}
            onClick={() => setDrillDownMetric({ type: 'errors', label: 'Error Rate', unit: '%', color: '#F59E0B' })}
          />
        </Box>
        <Box sx={{ flex: '1 1 calc(25% - 12px)', minWidth: 200, minHeight: 120 }}>
          <MetricCard
            label="Success Rate"
            value={gateway.success_rate.value.toFixed(1)}
            unit="%"
            trend={gateway.success_rate.trend}
            color="#10B981"
            dataSource="real"
            sparklineData={gateway.success_rate.sparkline_data}
            avg_1h={gateway.success_rate.avg_1h}
            avg_24h={gateway.success_rate.avg_24h}
            avg_7d={gateway.success_rate.avg_7d}
          />
        </Box>
      </Box>

      {/* LLM Inference Metrics */}
      <Typography
        variant="h6"
        sx={{
          mb: 2,
          fontWeight: 600,
          fontSize: '0.85rem',
          letterSpacing: '0.1em',
          textTransform: 'uppercase',
          color: 'text.secondary',
        }}
      >
        LLM Inference (Ollama)
      </Typography>
      <Box sx={{ display: 'flex', gap: 2, mb: 4, flexWrap: 'wrap' }}>
        <Box sx={{ flex: '1 1 calc(20% - 12px)', minWidth: 180, minHeight: 120 }}>
          <MetricCard
            label="Active Models"
            value={modelservice.llm?.active_models?.value || 0}
            unit="models"
            color="#A78BFA"
            dataSource="real"
          />
        </Box>
        <Box sx={{ flex: '1 1 calc(20% - 12px)', minWidth: 180, minHeight: 120 }}>
          <MetricCard
            label="TTFT"
            value={modelservice.llm?.ttft?.value || 0}
            unit="s"
            trend={modelservice.llm?.ttft?.trend || 0}
            color="#EC4899"
            dataSource="real"
            tooltip="Time to First Token - latency until first token appears"
            lowerIsBetter={true}
          />
        </Box>
        <Box sx={{ flex: '1 1 calc(20% - 12px)', minWidth: 180, minHeight: 120 }}>
          <MetricCard
            label="TPS"
            value={modelservice.llm?.tps?.value || 0}
            unit="t/s"
            trend={modelservice.llm?.tps?.trend || 0}
            color="#00D9FF"
            dataSource="real"
            tooltip="Tokens Per Second - output generation speed"
            avg_1h={modelservice.llm?.tps?.avg_1h}
            avg_24h={modelservice.llm?.tps?.avg_24h}
            avg_7d={modelservice.llm?.tps?.avg_7d}
          />
        </Box>
        <Box sx={{ flex: '1 1 calc(20% - 12px)', minWidth: 180, minHeight: 120 }}>
          <MetricCard
            label="E2E Latency"
            value={modelservice.llm?.e2e_latency?.value || 0}
            unit="s"
            trend={modelservice.llm?.e2e_latency?.trend || 0}
            color="#F59E0B"
            dataSource="real"
            tooltip="End-to-end request completion time"
            lowerIsBetter={true}
            avg_1h={modelservice.llm?.e2e_latency?.avg_1h}
            avg_24h={modelservice.llm?.e2e_latency?.avg_24h}
            avg_7d={modelservice.llm?.e2e_latency?.avg_7d}
          />
        </Box>
        <Box sx={{ flex: '1 1 calc(20% - 12px)', minWidth: 180, minHeight: 120 }}>
          <MetricCard
            label="RPS"
            value={modelservice.llm?.rps?.value || 0}
            unit="req/s"
            trend={modelservice.llm?.rps?.trend || 0}
            color="#10B981"
            dataSource="real"
            tooltip="Requests Per Second - throughput for concurrent users"
            avg_1h={modelservice.llm?.rps?.avg_1h}
            avg_24h={modelservice.llm?.rps?.avg_24h}
            avg_7d={modelservice.llm?.rps?.avg_7d}
          />
        </Box>
      </Box>
      <Box sx={{ display: 'flex', gap: 2, mb: 4, flexWrap: 'wrap' }}>
        <Box sx={{ flex: '1 1 calc(25% - 12px)', minWidth: 180, minHeight: 120 }}>
          <MetricCard
            label="Success Rate"
            value={modelservice.llm?.success_rate?.value || 0}
            unit="%"
            color="#10B981"
            dataSource="real"
          />
        </Box>
        <Box sx={{ flex: '1 1 calc(25% - 12px)', minWidth: 180, minHeight: 120 }}>
          <MetricCard
            label="Tokens (24h)"
            value={modelservice.llm?.total_tokens_24h || 0}
            unit="tokens"
            color="#8B5CF6"
            dataSource="real"
          />
        </Box>
        <Box sx={{ flex: '1 1 calc(25% - 12px)', minWidth: 180, minHeight: 120 }}>
          <MetricCard
            label="Avg Prompt"
            value={modelservice.llm?.avg_prompt_length?.value || 0}
            unit="tokens"
            color="#06B6D4"
            dataSource="real"
          />
        </Box>
        <Box sx={{ flex: '1 1 calc(25% - 12px)', minWidth: 180, minHeight: 120 }}>
          <MetricCard
            label="Avg Response"
            value={modelservice.llm?.avg_response_length?.value || 0}
            unit="tokens"
            color="#14B8A6"
            dataSource="real"
          />
        </Box>
      </Box>

      {/* Specialized Inference Models */}
      <Typography
        variant="h6"
        sx={{
          mb: 2,
          mt: 3,
          fontWeight: 600,
          fontSize: '0.85rem',
          letterSpacing: '0.1em',
          textTransform: 'uppercase',
          color: 'text.secondary',
        }}
      >
        Specialized Inference Models
      </Typography>
      
      {/* NER Metrics */}
      <Typography variant="subtitle2" sx={{ mb: 1, color: 'text.secondary', fontWeight: 500 }}>Named Entity Recognition</Typography>
      <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
        <Box sx={{ flex: '1 1 calc(20% - 12px)', minWidth: 180, minHeight: 120 }}>
          <MetricCard
            label="Rate"
            value={modelservice.ner?.inference_rate?.value || 0}
            unit="req/s"
            trend={modelservice.ner?.inference_rate?.trend || 0}
            color="#F59E0B"
            dataSource="real"
            avg_1h={modelservice.ner?.inference_rate?.avg_1h}
            avg_24h={modelservice.ner?.inference_rate?.avg_24h}
            avg_7d={modelservice.ner?.inference_rate?.avg_7d}
          />
        </Box>
        <Box sx={{ flex: '1 1 calc(20% - 12px)', minWidth: 180, minHeight: 120 }}>
          <MetricCard
            label="Latency"
            value={modelservice.ner?.avg_latency?.value || 0}
            unit="s"
            trend={modelservice.ner?.avg_latency?.trend || 0}
            color="#EF4444"
            dataSource="real"
            lowerIsBetter={true}
            avg_1h={modelservice.ner?.avg_latency?.avg_1h}
            avg_24h={modelservice.ner?.avg_latency?.avg_24h}
            avg_7d={modelservice.ner?.avg_latency?.avg_7d}
          />
        </Box>
        <Box sx={{ flex: '1 1 calc(20% - 12px)', minWidth: 180, minHeight: 120 }}>
          <MetricCard
            label="P99"
            value={modelservice.ner?.p99_latency || 0}
            unit="s"
            color="#DC2626"
            dataSource="real"
            tooltip="99th percentile latency"
            lowerIsBetter={true}
          />
        </Box>
        <Box sx={{ flex: '1 1 calc(20% - 12px)', minWidth: 180, minHeight: 120 }}>
          <MetricCard
            label="Entities (24h)"
            value={modelservice.ner?.total_entities_24h || 0}
            unit="entities"
            color="#F97316"
            dataSource="real"
          />
        </Box>
        <Box sx={{ flex: '1 1 calc(20% - 12px)', minWidth: 180, minHeight: 120 }}>
          <MetricCard
            label="Success Rate"
            value={modelservice.ner?.success_rate?.value || 0}
            unit="%"
            color="#10B981"
            dataSource="real"
          />
        </Box>
      </Box>

      {/* Sentiment Analysis Metrics */}
      <Typography variant="subtitle2" sx={{ mb: 1, color: 'text.secondary', fontWeight: 500 }}>Sentiment Analysis</Typography>
      <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
        <Box sx={{ flex: '1 1 calc(20% - 12px)', minWidth: 180, minHeight: 120 }}>
          <MetricCard
            label="Rate"
            value={modelservice.sentiment?.inference_rate?.value || 0}
            unit="req/s"
            trend={modelservice.sentiment?.inference_rate?.trend || 0}
            color="#8B5CF6"
            dataSource="real"
            avg_1h={modelservice.sentiment?.inference_rate?.avg_1h}
            avg_24h={modelservice.sentiment?.inference_rate?.avg_24h}
            avg_7d={modelservice.sentiment?.inference_rate?.avg_7d}
          />
        </Box>
        <Box sx={{ flex: '1 1 calc(20% - 12px)', minWidth: 180, minHeight: 120 }}>
          <MetricCard
            label="Latency"
            value={modelservice.sentiment?.avg_latency?.value || 0}
            unit="s"
            trend={modelservice.sentiment?.avg_latency?.trend || 0}
            color="#A855F7"
            dataSource="real"
            lowerIsBetter={true}
            avg_1h={modelservice.sentiment?.avg_latency?.avg_1h}
            avg_24h={modelservice.sentiment?.avg_latency?.avg_24h}
            avg_7d={modelservice.sentiment?.avg_latency?.avg_7d}
          />
        </Box>
        <Box sx={{ flex: '1 1 calc(20% - 12px)', minWidth: 180, minHeight: 120 }}>
          <MetricCard
            label="P99"
            value={modelservice.sentiment?.p99_latency || 0}
            unit="s"
            color="#9333EA"
            dataSource="real"
            tooltip="99th percentile latency"
            lowerIsBetter={true}
          />
        </Box>
        <Box sx={{ flex: '1 1 calc(20% - 12px)', minWidth: 180, minHeight: 120 }}>
          <MetricCard
            label="Analyses (24h)"
            value={modelservice.sentiment?.total_analyses_24h || 0}
            unit="analyses"
            color="#C084FC"
            dataSource="real"
          />
        </Box>
        <Box sx={{ flex: '1 1 calc(20% - 12px)', minWidth: 180, minHeight: 120 }}>
          <MetricCard
            label="Avg Confidence"
            value={modelservice.sentiment?.avg_confidence?.value || 0}
            unit=""
            color="#D946EF"
            dataSource="real"
          />
        </Box>
      </Box>

      {/* Embeddings Metrics */}
      <Typography variant="subtitle2" sx={{ mb: 1, color: 'text.secondary', fontWeight: 500 }}>Embeddings</Typography>
      <Box sx={{ display: 'flex', gap: 2, mb: 4, flexWrap: 'wrap' }}>
        <Box sx={{ flex: '1 1 calc(20% - 12px)', minWidth: 180, minHeight: 120 }}>
          <MetricCard
            label="Rate"
            value={modelservice.embeddings?.inference_rate?.value || 0}
            unit="req/s"
            trend={modelservice.embeddings?.inference_rate?.trend || 0}
            color="#06B6D4"
            dataSource="real"
            avg_1h={modelservice.embeddings?.inference_rate?.avg_1h}
            avg_24h={modelservice.embeddings?.inference_rate?.avg_24h}
            avg_7d={modelservice.embeddings?.inference_rate?.avg_7d}
          />
        </Box>
        <Box sx={{ flex: '1 1 calc(20% - 12px)', minWidth: 180, minHeight: 120 }}>
          <MetricCard
            label="Latency"
            value={modelservice.embeddings?.avg_latency?.value || 0}
            unit="s"
            trend={modelservice.embeddings?.avg_latency?.trend || 0}
            color="#0891B2"
            dataSource="real"
            lowerIsBetter={true}
            avg_1h={modelservice.embeddings?.avg_latency?.avg_1h}
            avg_24h={modelservice.embeddings?.avg_latency?.avg_24h}
            avg_7d={modelservice.embeddings?.avg_latency?.avg_7d}
          />
        </Box>
        <Box sx={{ flex: '1 1 calc(20% - 12px)', minWidth: 180, minHeight: 120 }}>
          <MetricCard
            label="P99"
            value={modelservice.embeddings?.p99_latency || 0}
            unit="s"
            color="#0E7490"
            dataSource="real"
            tooltip="99th percentile latency"
            lowerIsBetter={true}
          />
        </Box>
        <Box sx={{ flex: '1 1 calc(20% - 12px)', minWidth: 180, minHeight: 120 }}>
          <MetricCard
            label="Throughput"
            value={modelservice.embeddings?.throughput?.value || 0}
            unit="t/s"
            color="#14B8A6"
            dataSource="real"
            tooltip="Input tokens processed per second"
          />
        </Box>
        <Box sx={{ flex: '1 1 calc(20% - 12px)', minWidth: 180, minHeight: 120 }}>
          <MetricCard
            label="Embeddings (24h)"
            value={modelservice.embeddings?.total_embeddings_24h || 0}
            unit="embeddings"
            color="#2DD4BF"
            dataSource="real"
          />
        </Box>
      </Box>

      {/* Memory System Metrics */}
      <Typography
        variant="h6"
        sx={{
          mb: 2,
          fontWeight: 600,
          fontSize: '0.85rem',
          letterSpacing: '0.1em',
          textTransform: 'uppercase',
          color: 'text.secondary',
        }}
      >
        Memory System Metrics
      </Typography>
      <Box sx={{ display: 'flex', gap: 2, mb: 4, flexWrap: 'wrap' }}>
        <Box sx={{ flex: '1 1 calc(25% - 12px)', minWidth: 200, minHeight: 120 }}>
          <MetricCard
            label="Working Memory"
            value={memory.working_memory_size.value}
            unit="entries"
            trend={memory.working_memory_size.trend}
            color="#00D9FF"
            dataSource="mock"
          />
        </Box>
        <Box sx={{ flex: '1 1 calc(25% - 12px)', minWidth: 200, minHeight: 120 }}>
          <MetricCard
            label="Semantic Queries/s"
            value={memory.semantic_queries_per_second.value.toFixed(1)}
            unit="queries/s"
            trend={memory.semantic_queries_per_second.trend}
            color="#A78BFA"
            dataSource="mock"
          />
        </Box>
        <Box sx={{ flex: '1 1 calc(25% - 12px)', minWidth: 200, minHeight: 120 }}>
          <MetricCard
            label="KG Nodes"
            value={memory.kg_nodes.value}
            unit="nodes"
            trend={memory.kg_nodes.trend}
            color="#EC4899"
            dataSource="mock"
          />
        </Box>
        <Box sx={{ flex: '1 1 calc(25% - 12px)', minWidth: 200, minHeight: 120 }}>
          <MetricCard
            label="KG Relationships"
            value={memory.kg_relationships.value}
            unit="edges"
            trend={memory.kg_relationships.trend}
            color="#10B981"
            dataSource="mock"
          />
        </Box>
      </Box>

      <Box sx={{ display: 'flex', gap: 3, mb: 4, flexWrap: 'wrap', alignItems: 'stretch' }}>
        <Box sx={{ flex: '1 1 calc(50% - 12px)', minWidth: 300, display: 'flex' }}>
          <Paper
            sx={{
              flex: 1,
              p: 3,
              borderRadius: '20px',
              bgcolor: 'rgba(255, 255, 255, 0.02)',
              backdropFilter: 'blur(12px)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
            }}
          >
            <Typography variant="subtitle2" sx={{ mb: 3, fontWeight: 600 }}>
              Entity Type Distribution
            </Typography>
            {entityTypeData.length > 0 && (
              <DonutChart
                data={entityTypeData}
                size={140}
                thickness={24}
                centerLabel="Total"
                centerValue={entityTypeData.reduce((sum, item) => sum + item.value, 0)}
              />
            )}
            {entityTypeData.length === 0 && (
              <Typography variant="body2" sx={{ color: 'text.secondary', textAlign: 'center', py: 4 }}>
                No entity data available
              </Typography>
            )}
          </Paper>
        </Box>
        <Box sx={{ flex: '1 1 calc(50% - 12px)', minWidth: 300, display: 'flex' }}>
          <Paper
            sx={{
              flex: 1,
              p: 3,
              borderRadius: '20px',
              bgcolor: 'rgba(255, 255, 255, 0.02)',
              backdropFilter: 'blur(12px)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
            }}
          >
            <Typography variant="subtitle2" sx={{ mb: 3, fontWeight: 600 }}>
              Relationship Type Distribution
            </Typography>
            {relationshipTypeData.length > 0 && (
              <DonutChart
                data={relationshipTypeData}
                size={140}
                thickness={24}
                centerLabel="Total"
                centerValue={relationshipTypeData.reduce((sum, item) => sum + item.value, 0)}
              />
            )}
            {relationshipTypeData.length === 0 && (
              <Typography variant="body2" sx={{ color: 'text.secondary', textAlign: 'center', py: 4 }}>
                No relationship data available
              </Typography>
            )}
          </Paper>
        </Box>
      </Box>

      {/* Scheduler & Message Bus */}
      <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap', alignItems: 'stretch' }}>
        <Box sx={{ flex: '1 1 calc(50% - 12px)', minWidth: 300, display: 'flex' }}>
          <Paper
            sx={{
              flex: 1,
              p: 3,
              borderRadius: '20px',
              bgcolor: 'rgba(255, 255, 255, 0.02)',
              backdropFilter: 'blur(12px)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
            }}
          >
            <Typography variant="subtitle2" sx={{ mb: 3, fontWeight: 600 }}>
              Task Scheduler
            </Typography>
            <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
              <Box sx={{ flex: '1 1 calc(50% - 8px)', minWidth: 140, minHeight: 100 }}>
                <MetricCard
                  label="Jobs Today"
                  value={scheduler.jobs_today.value}
                  trend={scheduler.jobs_today.trend}
                  color="#00D9FF"
                  size="small"
                  dataSource="mock"
                />
              </Box>
              <Box sx={{ flex: '1 1 calc(50% - 8px)', minWidth: 140, minHeight: 100 }}>
                <MetricCard
                  label="Success Rate"
                  value={scheduler.success_rate.value.toFixed(1)}
                  unit="%"
                  trend={scheduler.success_rate.trend}
                  color="#10B981"
                  size="small"
                  dataSource="mock"
                />
              </Box>
            </Box>
            <Box>
              <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.7rem', mb: 1, display: 'block' }}>
                Queue Utilization
              </Typography>
              {Object.entries(scheduler.queue_utilization).map(([queue, utilization]: [string, any]) => (
                <Box key={queue} sx={{ mb: 1.5 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                    <Typography variant="caption" sx={{ fontSize: '0.75rem' }}>
                      {queue.replace(/_/g, ' ')}
                    </Typography>
                    <Typography variant="caption" sx={{ fontSize: '0.75rem', fontWeight: 600 }}>
                      {utilization.toFixed(1)}%
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={utilization}
                    sx={{
                      height: 6,
                      borderRadius: 3,
                      bgcolor: 'rgba(255, 255, 255, 0.05)',
                      '& .MuiLinearProgress-bar': {
                        bgcolor: utilization > 80 ? '#EF4444' : utilization > 50 ? '#F59E0B' : '#10B981',
                        borderRadius: 3,
                      },
                    }}
                  />
                </Box>
              ))}
            </Box>
          </Paper>
        </Box>
        <Box sx={{ flex: '1 1 calc(50% - 12px)', minWidth: 300, display: 'flex' }}>
          <Paper
            sx={{
              flex: 1,
              p: 3,
              borderRadius: '20px',
              bgcolor: 'rgba(255, 255, 255, 0.02)',
              backdropFilter: 'blur(12px)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
            }}
          >
            <Typography variant="subtitle2" sx={{ mb: 3, fontWeight: 600 }}>
              Message Bus
            </Typography>
            <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
              <Box sx={{ flex: '1 1 calc(50% - 8px)', minWidth: 140, minHeight: 100 }}>
                <MetricCard
                  label="Messages/sec"
                  value={message_bus.messages_per_second.value.toFixed(1)}
                  unit="msg/s"
                  trend={message_bus.messages_per_second.trend}
                  color="#00D9FF"
                  size="small"
                  dataSource="mock"
                />
              </Box>
              <Box sx={{ flex: '1 1 calc(50% - 8px)', minWidth: 140, minHeight: 100 }}>
                <MetricCard
                  label="Backlog Depth"
                  value={message_bus.backlog_depth.value}
                  unit="msgs"
                  trend={message_bus.backlog_depth.trend}
                  color="#F59E0B"
                  status={message_bus.backlog_depth.status}
                  size="small"
                  dataSource="mock"
                />
              </Box>
            </Box>
            <Box>
              <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.7rem', mb: 1, display: 'block' }}>
                Top Topics
              </Typography>
              {message_bus.top_topics.slice(0, 4).map((topic: any, index: number) => (
                <Box
                  key={index}
                  sx={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    mb: 1,
                    p: 1,
                    borderRadius: '8px',
                    bgcolor: 'rgba(255, 255, 255, 0.02)',
                  }}
                >
                  <Typography variant="caption" sx={{ fontSize: '0.75rem', flex: 1 }}>
                    {topic.topic}
                  </Typography>
                  <Typography variant="caption" sx={{ fontSize: '0.75rem', fontWeight: 600, color: '#00D9FF' }}>
                    {topic.msg_per_sec.toFixed(1)} msg/s
                  </Typography>
                </Box>
              ))}
            </Box>
          </Paper>
        </Box>
      </Box>

      {/* Metric Detail Drawer */}
      {drillDownMetric && (
        <MetricDetailDrawer
          open={drillDownMetric !== null}
          onClose={() => setDrillDownMetric(null)}
          metricType={drillDownMetric.type}
          metricLabel={drillDownMetric.label}
          metricUnit={drillDownMetric.unit}
          metricColor={drillDownMetric.color}
        />
      )}
    </Box>
  );
};

// Helper functions
function getEntityColor(type: string): string {
  const colors: Record<string, string> = {
    PERSON: '#EC4899',
    CONCEPT: '#A78BFA',
    ACTIVITY: '#00D9FF',
    GOAL: '#F59E0B',
    DATE: '#10B981',
    ENTITY: '#3B82F6',
    GPE: '#8B5CF6',
  };
  return colors[type] || '#6B7280';
}

function getRelationshipColor(type: string): string {
  const colors: Record<string, string> = {
    BORN_IN: '#3B82F6',
    HAS_GOAL: '#EC4899',
    INTERESTED_IN: '#A78BFA',
    LIVES_IN: '#00D9FF',
    PART_OF: '#F59E0B',
    PRIORITIZES: '#10B981',
  };
  return colors[type] || '#6B7280';
}
