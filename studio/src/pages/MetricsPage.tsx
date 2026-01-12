import React, { useState, useEffect } from 'react';
import { Box, Typography, Paper, LinearProgress } from '@mui/material';
import { CircularGauge } from '../components/metrics/CircularGauge';
import { DonutChart } from '../components/metrics/DonutChart';
import { MetricCard } from '../components/metrics/MetricCard';
import { ActiveModelsCard } from '../components/metrics/ActiveModelsCard';
import { MetricsSkeleton } from '../components/metrics/MetricsSkeleton';
import { MetricDetailDrawer } from '../components/metrics/MetricDetailDrawer';
import { StyledTooltip } from '../components/common/StyledTooltip';
import { Info } from 'lucide-react';
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
              <StyledTooltip 
                key={name}
                title={status.explanation || 'No details available'}
                arrow
                placement="left"
              >
                <Box
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
                    cursor: 'help',
                    transition: 'all 0.2s ease',
                    '&:hover': {
                      bgcolor: status.status === 'healthy' ? 'rgba(16, 185, 129, 0.1)' : status.status === 'warning' ? 'rgba(245, 158, 11, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                      borderColor: status.status === 'healthy' ? 'rgba(16, 185, 129, 0.4)' : status.status === 'warning' ? 'rgba(245, 158, 11, 0.4)' : 'rgba(239, 68, 68, 0.4)',
                    },
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
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    <Typography variant="caption" sx={{ fontSize: '0.7rem', fontWeight: 700, color: status.status === 'healthy' ? '#10B981' : status.status === 'warning' ? '#F59E0B' : '#EF4444' }}>
                      {status.health}
                    </Typography>
                    {status.status !== 'healthy' && (
                      <Info size={12} style={{ color: status.status === 'warning' ? '#F59E0B' : '#EF4444' }} />
                    )}
                  </Box>
                </Box>
              </StyledTooltip>
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
            sparklineData={gateway.requests_per_second.sparkline_data}
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
      {/* Row 1: Throughput & Performance Metrics */}
      <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap' }}>
        <Box sx={{ flex: '1 1 calc(20% - 12px)', minWidth: 180, minHeight: 120 }}>
          <MetricCard
            label="RPS"
            value={modelservice.llm?.rps?.value || 0}
            unit="req/s"
            trend={modelservice.llm?.rps?.trend || 0}
            color="#10B981"
            tooltip="Requests Per Second - throughput for concurrent users"
            avg_1h={modelservice.llm?.rps?.avg_1h}
            avg_24h={modelservice.llm?.rps?.avg_24h}
            avg_7d={modelservice.llm?.rps?.avg_7d}
          />
        </Box>
        <Box sx={{ flex: '1 1 calc(20% - 12px)', minWidth: 180, minHeight: 120 }}>
          <MetricCard
            label="Total Requests"
            value={modelservice.llm?.total_requests_24h || 0}
            unit="req"
            color="#8B5CF6"
            tooltip="Total LLM requests in the last 24 hours"
          />
        </Box>
        <Box sx={{ flex: '1 1 calc(20% - 12px)', minWidth: 180, minHeight: 120 }}>
          <MetricCard
            label="TPS"
            value={modelservice.llm?.tps?.value || 0}
            unit="t/s"
            trend={modelservice.llm?.tps?.trend || 0}
            color="#00D9FF"
            tooltip="Tokens Per Second - output generation speed"
            avg_1h={modelservice.llm?.tps?.avg_1h}
            avg_24h={modelservice.llm?.tps?.avg_24h}
            avg_7d={modelservice.llm?.tps?.avg_7d}
          />
        </Box>
        <Box sx={{ flex: '1 1 calc(20% - 12px)', minWidth: 180, minHeight: 120 }}>
          <MetricCard
            label="TTFT"
            value={modelservice.llm?.ttft?.value || 0}
            unit="s"
            trend={modelservice.llm?.ttft?.trend || 0}
            color="#EC4899"
            tooltip="Time to First Token - latency until first token appears"
            lowerIsBetter={true}
          />
        </Box>
        <Box sx={{ flex: '1 1 calc(20% - 12px)', minWidth: 180, minHeight: 120 }}>
          <MetricCard
            label="E2E Latency"
            value={modelservice.llm?.e2e_latency?.value || 0}
            unit="s"
            trend={modelservice.llm?.e2e_latency?.trend || 0}
            color="#F59E0B"
            tooltip="End-to-end request completion time (24h trend)"
            lowerIsBetter={true}
            size="large"
            sparklineData={modelservice.llm?.e2e_latency?.sparkline_data}
            invertSparkline={true}
            avg_1h={modelservice.llm?.e2e_latency?.avg_1h}
            avg_24h={modelservice.llm?.e2e_latency?.avg_24h}
            avg_7d={modelservice.llm?.e2e_latency?.avg_7d}
          />
        </Box>
      </Box>
      {/* Row 2: Quality & Resource Metrics */}
      <Box sx={{ display: 'flex', gap: 2, mb: 4, flexWrap: 'wrap' }}>
        <Box sx={{ flex: '1 1 calc(20% - 12px)', minWidth: 180, minHeight: 120 }}>
          <MetricCard
            label="Success Rate"
            value={modelservice.llm?.success_rate?.value || 0}
            unit="%"
            color="#10B981"
          />
        </Box>
        <Box sx={{ flex: '1 1 calc(20% - 12px)', minWidth: 180, minHeight: 120 }}>
          <MetricCard
            label="Tokens (24h)"
            value={modelservice.llm?.total_tokens_24h || 0}
            unit="tokens"
            color="#8B5CF6"
          />
        </Box>
        <Box sx={{ flex: '1 1 calc(20% - 12px)', minWidth: 180, minHeight: 120 }}>
          <MetricCard
            label="Avg Prompt"
            value={modelservice.llm?.avg_prompt_length?.value || 0}
            unit="tokens"
            color="#06B6D4"
            tooltip="Includes user message, system instructions, memory context, and knowledge graph information"
          />
        </Box>
        <Box sx={{ flex: '1 1 calc(20% - 12px)', minWidth: 180, minHeight: 120 }}>
          <MetricCard
            label="Avg Response"
            value={modelservice.llm?.avg_response_length?.value || 0}
            unit="tokens"
            color="#14B8A6"
          />
        </Box>
        <Box sx={{ flex: '1 1 calc(20% - 12px)', minWidth: 180, minHeight: 120 }}>
          <ActiveModelsCard
            modelCount={modelservice.llm?.active_models?.value || 0}
            modelUsage={modelservice.llm?.model_usage || {}}
            tooltip="Models with inference activity in the last 24 hours"
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
            tooltip="NER inference requests per second. Shows how frequently named entities are being extracted from text."
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
            tooltip="Average time to extract named entities from text. Lower is better. Includes model inference and post-processing."
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
            tooltip="99th percentile latency - 99% of NER requests complete faster than this. Useful for identifying worst-case performance."
            lowerIsBetter={true}
          />
        </Box>
        <Box sx={{ flex: '1 1 calc(20% - 12px)', minWidth: 180, minHeight: 120 }}>
          <MetricCard
            label="Entities (24h)"
            value={modelservice.ner?.total_entities_24h || 0}
            unit="entities"
            color="#F97316"
            tooltip="Total named entities extracted in the last 24 hours. Includes PERSON, ORG, LOC, DATE, and other entity types."
          />
        </Box>
        <Box sx={{ flex: '1 1 calc(20% - 12px)', minWidth: 180, minHeight: 120 }}>
          <MetricCard
            label="Success Rate"
            value={modelservice.ner?.success_rate?.value || 0}
            unit="%"
            color="#10B981"
            tooltip="Percentage of NER requests that completed successfully without errors. Target: >95%."
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
            tooltip="Sentiment analysis requests per second. Shows how frequently text sentiment is being analyzed."
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
            tooltip="Average time to analyze text sentiment. Lower is better. Includes model inference and confidence scoring."
            lowerIsBetter={true}
            avg_1h={modelservice.sentiment?.avg_latency?.avg_1h}
            avg_24h={modelservice.sentiment?.avg_latency?.avg_24h}
            avg_7d={modelservice.sentiment?.avg_7d}
          />
        </Box>
        <Box sx={{ flex: '1 1 calc(20% - 12px)', minWidth: 180, minHeight: 120 }}>
          <MetricCard
            label="P99"
            value={modelservice.sentiment?.p99_latency || 0}
            unit="s"
            color="#9333EA"
            tooltip="99th percentile latency - 99% of sentiment analyses complete faster than this. Useful for SLA monitoring."
            lowerIsBetter={true}
          />
        </Box>
        <Box sx={{ flex: '1 1 calc(20% - 12px)', minWidth: 180, minHeight: 120 }}>
          <MetricCard
            label="Analyses (24h)"
            value={modelservice.sentiment?.total_analyses_24h || 0}
            unit="analyses"
            color="#C084FC"
            tooltip="Total sentiment analyses performed in the last 24 hours. Each analysis classifies text as positive, negative, or neutral."
          />
        </Box>
        <Box sx={{ flex: '1 1 calc(20% - 12px)', minWidth: 180, minHeight: 120 }}>
          <MetricCard
            label="Avg Confidence"
            value={modelservice.sentiment?.avg_confidence?.value || 0}
            unit=""
            color="#D946EF"
            tooltip="Average confidence score (0-1) of sentiment predictions. Higher values indicate more certain classifications. Target: >0.7."
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
            unit={modelservice.embeddings?.inference_rate?.unit || "emb/s"}
            trend={modelservice.embeddings?.inference_rate?.trend || 0}
            color="#06B6D4"
            avg_1h={modelservice.embeddings?.inference_rate?.avg_1h}
            avg_24h={modelservice.embeddings?.inference_rate?.avg_24h}
            avg_7d={modelservice.embeddings?.inference_rate?.avg_7d}
          />
        </Box>
        <Box sx={{ flex: '1 1 calc(20% - 12px)', minWidth: 180, minHeight: 120 }}>
          <MetricCard
            label="Latency"
            value={modelservice.embeddings?.avg_latency?.value || 0}
            unit="ms"
            trend={modelservice.embeddings?.avg_latency?.trend || 0}
            color="#0891B2"
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
            unit="ms"
            color="#0E7490"
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
            tooltip="Input tokens processed per second"
          />
        </Box>
        <Box sx={{ flex: '1 1 calc(20% - 12px)', minWidth: 180, minHeight: 120 }}>
          <MetricCard
            label="Embeddings (24h)"
            value={modelservice.embeddings?.total_embeddings_24h || 0}
            unit="embeddings"
            color="#2DD4BF"
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
          />
        </Box>
        <Box sx={{ flex: '1 1 calc(25% - 12px)', minWidth: 200, minHeight: 120 }}>
          <MetricCard
            label="Semantic Queries/s"
            value={memory.semantic_queries_per_second.value.toFixed(1)}
            unit="queries/s"
            trend={memory.semantic_queries_per_second.trend}
            color="#A78BFA"
          />
        </Box>
        <Box sx={{ flex: '1 1 calc(25% - 12px)', minWidth: 200, minHeight: 120 }}>
          <MetricCard
            label="KG Nodes"
            value={memory.kg_nodes.value}
            unit="nodes"
            trend={memory.kg_nodes.trend}
            color="#EC4899"
          />
        </Box>
        <Box sx={{ flex: '1 1 calc(25% - 12px)', minWidth: 200, minHeight: 120 }}>
          <MetricCard
            label="KG Relationships"
            value={memory.kg_relationships.value}
            unit="edges"
            trend={memory.kg_relationships.trend}
            color="#10B981"
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

      {/* Scheduler & Message Bus Metrics */}
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
        Scheduler & Message Bus
      </Typography>
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
                />
              </Box>
            </Box>
            <Box>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1.5 }}>
                <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.7rem', letterSpacing: '0.05em' }}>
                  ACTIVE TOPICS ({message_bus.top_topics.length})
                </Typography>
                <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'center' }}>
                  {[
                    { label: 'model', color: '#00D9FF' },
                    { label: 'system', color: '#A78BFA' },
                    { label: 'emotion', color: '#EC4899' },
                    { label: 'conversation', color: '#10B981' },
                    { label: 'proactive', color: '#F59E0B' },
                  ].map(({ label, color }) => (
                    <Box key={label} sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      <Box sx={{ width: 5, height: 5, borderRadius: '50%', bgcolor: color }} />
                      <Typography variant="caption" sx={{ fontSize: '0.65rem', color: 'text.secondary' }}>
                        {label}
                      </Typography>
                    </Box>
                  ))}
                </Box>
              </Box>
              <Box sx={{ maxHeight: 400, overflowY: 'auto', pr: 1, '&::-webkit-scrollbar': { width: '4px' }, '&::-webkit-scrollbar-track': { bgcolor: 'rgba(255,255,255,0.02)' }, '&::-webkit-scrollbar-thumb': { bgcolor: 'rgba(255,255,255,0.1)', borderRadius: '2px' } }}>
                {message_bus.top_topics.map((topic: any, index: number) => {
                  const isHighVolume = topic.msg_per_sec > 1;
                  const category = topic.topic.split('/')[0];
                  const categoryColors: Record<string, string> = {
                    'modelservice': '#00D9FF',
                    'system': '#A78BFA',
                    'emotion': '#EC4899',
                    'conversation': '#10B981',
                    'proactive': '#F59E0B',
                  };
                  const color = categoryColors[category] || '#6B7280';
                  
                  // Truncate long topics with ellipsis
                  const displayTopic = topic.topic.length > 60 
                    ? topic.topic.substring(0, 57) + '...' 
                    : topic.topic;
                  
                  return (
                    <Box
                      key={index}
                      sx={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 1,
                        mb: 0.75,
                        p: 1,
                        borderRadius: '6px',
                        bgcolor: isHighVolume ? 'rgba(0, 217, 255, 0.05)' : 'rgba(255, 255, 255, 0.02)',
                        border: '1px solid',
                        borderColor: isHighVolume ? 'rgba(0, 217, 255, 0.15)' : 'rgba(255, 255, 255, 0.05)',
                        transition: 'all 0.15s ease',
                        '&:hover': {
                          bgcolor: 'rgba(255, 255, 255, 0.05)',
                          borderColor: color,
                          transform: 'translateX(2px)',
                        },
                      }}
                      title={topic.topic}
                    >
                      <Box
                        sx={{
                          width: 5,
                          height: 5,
                          borderRadius: '50%',
                          bgcolor: color,
                          flexShrink: 0,
                        }}
                      />
                      <Typography 
                        variant="caption" 
                        sx={{ 
                          fontSize: '0.7rem', 
                          flex: 1,
                          fontFamily: 'monospace',
                          color: 'text.primary',
                          fontWeight: isHighVolume ? 600 : 400,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {displayTopic}
                      </Typography>
                      <Typography 
                        variant="caption" 
                        sx={{ 
                          fontSize: '0.7rem',
                          fontWeight: 700,
                          color: color,
                          minWidth: '60px',
                          textAlign: 'right',
                          flexShrink: 0,
                        }}
                      >
                        {topic.msg_per_sec >= 1 
                          ? topic.msg_per_sec.toFixed(1) 
                          : topic.msg_per_sec >= 0.01 
                            ? topic.msg_per_sec.toFixed(2)
                            : topic.msg_per_sec.toFixed(4)
                        } msg/s
                      </Typography>
                    </Box>
                  );
                })}
              </Box>
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
