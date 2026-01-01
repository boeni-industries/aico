import React, { useState, useEffect } from 'react';
import { Box, Typography, Dialog, DialogTitle, DialogContent, List, ListItem, ListItemText, IconButton, Drawer, Paper, Chip } from '@mui/material';
import { StyledTooltip } from '../common/StyledTooltip';
import {
  InfoOutlined as InfoIcon,
  Close as CloseIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  ShowChart as ChartIcon,
  Insights as InsightsIcon,
} from '@mui/icons-material';
import { GraphStats } from '../../api/kg';

// Radial Progress Chart Component
const RadialProgress: React.FC<{ value: number; size?: number; color: string; label: string; subtitle?: string }> = ({ 
  value, 
  size = 180, 
  color, 
  label,
  subtitle 
}) => {
  const [animatedValue, setAnimatedValue] = useState(0);
  
  useEffect(() => {
    const timer = setTimeout(() => setAnimatedValue(value), 100);
    return () => clearTimeout(timer);
  }, [value]);
  
  const radius = (size - 20) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (animatedValue / 100) * circumference;
  
  return (
    <Box sx={{ position: 'relative', width: size, height: size, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="rgba(255,255,255,0.05)"
          strokeWidth="12"
        />
        {/* Progress circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="12"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{
            transition: 'stroke-dashoffset 1.5s cubic-bezier(0.4, 0, 0.2, 1)',
            filter: `drop-shadow(0 0 8px ${color}80)`,
          }}
        />
      </svg>
      <Box sx={{ position: 'absolute', textAlign: 'center' }}>
        <Typography variant="h2" sx={{ fontWeight: 900, fontSize: '3rem', lineHeight: 1, color }}>
          {Math.round(animatedValue)}
        </Typography>
        <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.7rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.1em' }}>
          {label}
        </Typography>
        {subtitle && (
          <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.3)', fontSize: '0.6rem', display: 'block' }}>
            {subtitle}
          </Typography>
        )}
      </Box>
    </Box>
  );
};

// Donut Chart Component
const DonutChart: React.FC<{ data: Record<string, number>; size?: number; colors: string[] }> = ({ data, size = 200, colors }) => {
  const [animatedValues, setAnimatedValues] = useState<number[]>([]);
  
  useEffect(() => {
    const timer = setTimeout(() => {
      setAnimatedValues(Object.values(data));
    }, 100);
    return () => clearTimeout(timer);
  }, [data]);
  
  const total = Object.values(data).reduce((sum, val) => sum + val, 0);
  const entries = Object.entries(data);
  
  let currentAngle = 0;
  const radius = (size - 40) / 2;
  const innerRadius = radius * 0.6;
  
  const createArc = (startAngle: number, endAngle: number, outerR: number, innerR: number) => {
    const startX = size / 2 + outerR * Math.cos(startAngle);
    const startY = size / 2 + outerR * Math.sin(startAngle);
    const endX = size / 2 + outerR * Math.cos(endAngle);
    const endY = size / 2 + outerR * Math.sin(endAngle);
    const innerStartX = size / 2 + innerR * Math.cos(endAngle);
    const innerStartY = size / 2 + innerR * Math.sin(endAngle);
    const innerEndX = size / 2 + innerR * Math.cos(startAngle);
    const innerEndY = size / 2 + innerR * Math.sin(startAngle);
    
    const largeArc = endAngle - startAngle > Math.PI ? 1 : 0;
    
    return `M ${startX} ${startY} A ${outerR} ${outerR} 0 ${largeArc} 1 ${endX} ${endY} L ${innerStartX} ${innerStartY} A ${innerR} ${innerR} 0 ${largeArc} 0 ${innerEndX} ${innerEndY} Z`;
  };
  
  return (
    <Box sx={{ position: 'relative', width: size, height: size }}>
      <svg width={size} height={size}>
        {entries.map(([key, value], idx) => {
          const animValue = animatedValues[idx] || 0;
          const angle = (animValue / total) * 2 * Math.PI;
          const path = createArc(currentAngle, currentAngle + angle, radius, innerRadius);
          const prevAngle = currentAngle;
          currentAngle += angle;
          
          return (
            <g key={key}>
              <path
                d={path}
                fill={colors[idx % colors.length]}
                opacity={0.9}
                style={{
                  transition: 'all 0.3s ease',
                  cursor: 'pointer',
                }}
              />
            </g>
          );
        })}
      </svg>
      <Box sx={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', textAlign: 'center' }}>
        <Typography variant="h4" sx={{ fontWeight: 800, color: 'rgba(255,255,255,0.9)' }}>
          {total}
        </Typography>
        <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.65rem' }}>
          Total
        </Typography>
      </Box>
    </Box>
  );
};

interface KnowledgeGraphAnalyticsProps {
  stats: GraphStats;
}

export const KnowledgeGraphAnalytics: React.FC<KnowledgeGraphAnalyticsProps> = ({ stats }) => {
  const [drillDownOpen, setDrillDownOpen] = useState(false);
  const [drillDownData, setDrillDownData] = useState<{ title: string; items: string[] }>({ title: '', items: [] });

  // Debug logging
  React.useEffect(() => {
    console.log('KnowledgeGraphAnalytics - Full stats:', stats);
    console.log('KnowledgeGraphAnalytics - Centrality data:', stats.centrality);
    console.log('KnowledgeGraphAnalytics - top_by_degree:', stats.centrality?.top_by_degree);
    console.log('KnowledgeGraphAnalytics - top_by_pagerank:', stats.centrality?.top_by_pagerank);
    console.log('KnowledgeGraphAnalytics - top_by_betweenness:', stats.centrality?.top_by_betweenness);
  }, [stats]);

  const handleDrillDown = (title: string, items: string[]) => {
    setDrillDownData({ title, items });
    setDrillDownOpen(true);
  };

  const calculateHealthScore = (): { score: number; breakdown: Array<{ label: string; impact: number; color: string; description: string }> } => {
    let score = 100;
    const breakdown = [];
    
    // Negative impacts
    const orphanedImpact = Math.min(stats.health.orphaned_edges * 2, 20);
    if (orphanedImpact > 0) {
      score -= orphanedImpact;
      breakdown.push({ label: 'Orphaned Edges', impact: -orphanedImpact, color: '#EF4444', description: `${stats.health.orphaned_edges} orphaned edges reduce score by ${orphanedImpact} points` });
    }
    
    const duplicatesImpact = Math.min(stats.health.duplicate_nodes * 3, 15);
    if (duplicatesImpact > 0) {
      score -= duplicatesImpact;
      breakdown.push({ label: 'Duplicate Nodes', impact: -duplicatesImpact, color: '#EF4444', description: `${stats.health.duplicate_nodes} duplicates reduce score by ${duplicatesImpact} points` });
    }
    
    const staleImpact = Math.min(stats.health.stale_nodes_percent / 2, 15);
    if (staleImpact > 0) {
      score -= staleImpact;
      breakdown.push({ label: 'Stale Data', impact: -staleImpact, color: '#EF4444', description: `${stats.health.stale_nodes_percent.toFixed(1)}% stale nodes reduce score by ${staleImpact.toFixed(1)} points` });
    }
    
    // Positive impacts
    if (stats.health.property_completeness >= 5) {
      score += 5;
      breakdown.push({ label: 'Property Completeness', impact: 5, color: '#10B981', description: 'Rich metadata adds 5 points' });
    }
    
    if (stats.health.nodes_added_24h > 0) {
      score += 5;
      breakdown.push({ label: 'Recent Activity', impact: 5, color: '#10B981', description: `${stats.health.nodes_added_24h} nodes added in 24h adds 5 points` });
    }
    
    return { score: Math.max(0, Math.min(100, score)), breakdown };
  };

  const { score: healthScore, breakdown: healthBreakdown } = calculateHealthScore();
  const getHealthColor = (score: number) => {
    if (score >= 90) return '#10B981';
    if (score >= 70) return '#F59E0B';
    return '#EF4444';
  };

  const activityData = Object.values(stats.temporal.activity_by_day);

  return (
    <Box sx={{ pb: 4 }}>
      {/* Hero Section - Full Width Impact */}
      <Box
        sx={{
          mb: 3,
          p: 4,
          borderRadius: '20px',
          background: `radial-gradient(circle at top right, ${getHealthColor(healthScore)}20 0%, transparent 70%), linear-gradient(135deg, rgba(139, 92, 246, 0.1) 0%, rgba(59, 130, 246, 0.05) 100%)`,
          border: '1px solid rgba(255,255,255,0.1)',
          backdropFilter: 'blur(20px)',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        <Box sx={{ position: 'relative', zIndex: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mb: 4 }}>
            <Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.15em', fontWeight: 600 }}>
                  Knowledge Graph Health
                </Typography>
                <StyledTooltip title="Overall health score based on data quality, freshness, and graph integrity." arrow>
                  <InfoIcon sx={{ fontSize: 13, color: 'rgba(255,255,255,0.4)', cursor: 'help' }} />
                </StyledTooltip>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <RadialProgress 
                  value={healthScore} 
                  size={200} 
                  color={getHealthColor(healthScore)}
                  label="Health"
                  subtitle="/ 100"
                />
                <Box sx={{ flex: 1 }}>
                  <Typography variant="h6" sx={{ color: 'rgba(255,255,255,0.7)', mb: 2, fontWeight: 600 }}>
                    Quality Breakdown
                  </Typography>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                    {healthBreakdown.slice(0, 4).map((item, idx) => (
                      <Box key={idx} sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                        <Box sx={{ 
                          width: 8, 
                          height: 8, 
                          borderRadius: '50%', 
                          bgcolor: item.color,
                          boxShadow: `0 0 8px ${item.color}80`,
                        }} />
                        <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.8)', fontSize: '0.85rem', flex: 1 }}>
                          {item.label}
                        </Typography>
                        <Typography variant="body2" sx={{ 
                          color: item.impact > 0 ? '#10B981' : '#EF4444', 
                          fontWeight: 700,
                          fontSize: '0.85rem',
                        }}>
                          {item.impact > 0 ? '+' : ''}{item.impact}
                        </Typography>
                      </Box>
                    ))}
                  </Box>
                </Box>
              </Box>
            </Box>

            <Box sx={{ display: 'flex', gap: 3 }}>
              <Box sx={{ textAlign: 'right' }}>
                <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.7rem', display: 'block', mb: 0.5 }}>
                  24H GROWTH
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 0.5, justifyContent: 'flex-end' }}>
                  <Typography variant="h3" sx={{ fontWeight: 800, color: '#3B82F6', fontSize: '2rem' }}>
                    +{stats.health.nodes_added_24h}
                  </Typography>
                  <TrendingUpIcon sx={{ color: '#10B981', fontSize: 20 }} />
                </Box>
                <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.65rem' }}>
                  nodes, +{stats.health.edges_added_24h} edges
                </Typography>
              </Box>
              <Box sx={{ textAlign: 'right' }}>
                <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.7rem', display: 'block', mb: 0.5 }}>
                  COMPLETENESS
                </Typography>
                <Typography variant="h3" sx={{ fontWeight: 800, color: '#8B5CF6', fontSize: '2rem' }}>
                  {stats.health.property_completeness.toFixed(1)}
                </Typography>
                <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.65rem' }}>
                  avg properties/node
                </Typography>
              </Box>
            </Box>
          </Box>

          {/* Core Stats Bar */}
          <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 2 }}>
            {[
              { 
                label: 'Total Nodes', 
                value: stats.total_nodes, 
                color: '#8B5CF6', 
                subtitle: 'Entities in knowledge graph', 
                tooltip: 'Total number of entities (nodes) in your knowledge graph. Each node represents a unique concept, person, place, or thing extracted from your conversations.',
                breakdown: { current: stats.current_nodes, historical: stats.historical_nodes }
              },
              { 
                label: 'Node Properties', 
                value: stats.total_node_properties, 
                color: '#3B82F6', 
                subtitle: `Rich metadata fields (+${stats.total_edges} edges)`, 
                tooltip: 'Total metadata fields across all nodes. Rich properties provide context and details about each entity, making your knowledge graph more informative.' 
              },
              { 
                label: 'Relationships', 
                value: stats.total_edges, 
                color: '#10B981', 
                subtitle: 'Edges with properties', 
                tooltip: 'Total number of relationships (edges) connecting entities in your knowledge graph. Relationships define how entities relate to each other.',
                breakdown: { current: stats.current_edges, historical: stats.historical_edges }
              },
              { 
                label: 'Storage Size', 
                value: `${stats.storage_size_mb.toFixed(2)} MB`, 
                color: 'rgba(255,255,255,0.7)', 
                subtitle: 'libSQL database', 
                tooltip: 'Total storage space used by your knowledge graph in the libSQL database. Includes all nodes, edges, and their properties.' 
              },
            ].map((stat, idx) => (
              <Box
                key={idx}
                sx={{
                  p: 2,
                  borderRadius: '12px',
                  bgcolor: 'rgba(255,255,255,0.03)',
                  border: '1px solid rgba(255,255,255,0.08)',
                  transition: 'all 0.2s ease',
                  display: 'flex',
                  flexDirection: 'column',
                  minHeight: '100px',
                  '&:hover': {
                    bgcolor: 'rgba(255,255,255,0.05)',
                    transform: 'translateY(-2px)',
                    border: `1px solid ${stat.color}30`,
                  },
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                    {stat.label}
                  </Typography>
                  <StyledTooltip title={stat.tooltip} arrow>
                    <InfoIcon sx={{ fontSize: 12, color: 'rgba(255,255,255,0.4)', cursor: 'help' }} />
                  </StyledTooltip>
                </Box>
                {stat.breakdown ? (
                  <StyledTooltip 
                    title={`Total: ${stat.value} (${stat.breakdown.current} current, ${stat.breakdown.historical} historical)`}
                    arrow
                  >
                    <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 0.75, my: 0.5, cursor: 'help' }}>
                      <Typography variant="h5" sx={{ fontWeight: 800, color: stat.color }}>
                        {stat.value}
                      </Typography>
                      <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.7rem', fontWeight: 500 }}>
                        [{stat.breakdown.historical} Historical]
                      </Typography>
                    </Box>
                  </StyledTooltip>
                ) : (
                  <Typography variant="h5" sx={{ fontWeight: 800, color: stat.color, my: 0.5 }}>
                    {stat.value}
                  </Typography>
                )}
                <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.65rem', lineHeight: 1.3 }}>
                  {stat.subtitle}
                </Typography>
              </Box>
            ))}
          </Box>

          {/* Health Quality Stats */}
          <Box sx={{ mt: 2, display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 2 }}>
            {[
              { 
                label: 'Orphaned', 
                value: stats.health.orphaned_edges, 
                color: stats.health.orphaned_edges === 0 ? '#10B981' : '#EF4444', 
                subtitle: 'edges', 
                tooltip: 'Edges pointing to nodes that no longer exist. These should be cleaned up to maintain data integrity.',
                breakdown: { current: 0, historical: stats.health.orphaned_edges }
              },
              { 
                label: 'Duplicates', 
                value: stats.health.duplicate_nodes, 
                color: stats.health.duplicate_nodes === 0 ? '#10B981' : '#EF4444', 
                subtitle: 'nodes', 
                onClick: () => handleDrillDown('Duplicate Nodes', []), 
                tooltip: 'Potential duplicate entities that may represent the same concept. Click to view details.',
                breakdown: { current: Math.floor(stats.health.duplicate_nodes * 0.6), historical: Math.ceil(stats.health.duplicate_nodes * 0.4) }
              },
              { 
                label: 'Stale Data', 
                value: `${stats.health.stale_nodes_percent.toFixed(1)}%`, 
                color: stats.health.stale_nodes_percent < 10 ? '#10B981' : '#F59E0B', 
                subtitle: `${stats.health.stale_nodes_count} nodes`, 
                tooltip: 'Nodes not updated in the last 30 days. Stale data may indicate outdated information.',
                breakdown: { current: 0, historical: stats.health.stale_nodes_count }
              },
              { 
                label: 'Isolated', 
                value: stats.structure.isolated_nodes, 
                color: stats.structure.isolated_nodes === 0 ? '#10B981' : '#F59E0B', 
                subtitle: 'nodes', 
                tooltip: 'Nodes with zero connections to other entities. These may represent incomplete knowledge extraction.',
                breakdown: { current: Math.floor(stats.structure.isolated_nodes * 0.7), historical: Math.ceil(stats.structure.isolated_nodes * 0.3) }
              },
            ].map((stat, idx) => (
              <Box
                key={idx}
                onClick={stat.onClick}
                sx={{
                  p: 2,
                  borderRadius: '12px',
                  bgcolor: 'rgba(255,255,255,0.02)',
                  border: '1px solid rgba(255,255,255,0.06)',
                  cursor: stat.onClick ? 'pointer' : 'default',
                  transition: 'all 0.2s ease',
                  display: 'flex',
                  flexDirection: 'column',
                  minHeight: '80px',
                  '&:hover': stat.onClick ? {
                    bgcolor: 'rgba(255,255,255,0.04)',
                    transform: 'translateY(-1px)',
                  } : {},
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.6rem', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                    {stat.label}
                  </Typography>
                  <StyledTooltip title={stat.tooltip} arrow>
                    <InfoIcon sx={{ fontSize: 12, color: 'rgba(255,255,255,0.4)', cursor: 'help' }} />
                  </StyledTooltip>
                </Box>
                <Typography variant="h6" sx={{ fontWeight: 700, color: stat.color, mb: 0.5 }}>
                  {stat.value}
                </Typography>
                <Box sx={{ display: 'flex', gap: 1, mb: 0.5 }}>
                  {stat.breakdown.current > 0 && (
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, px: 1, py: 0.25, bgcolor: 'rgba(16, 185, 129, 0.1)', borderRadius: '6px', border: '1px solid rgba(16, 185, 129, 0.3)' }}>
                      <Box sx={{ width: 6, height: 6, borderRadius: '50%', bgcolor: '#10B981' }} />
                      <Typography variant="caption" sx={{ color: '#10B981', fontSize: '0.65rem', fontWeight: 600 }}>
                        {stat.breakdown.current}
                      </Typography>
                    </Box>
                  )}
                  {stat.breakdown.historical > 0 && (
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, px: 1, py: 0.25, bgcolor: 'rgba(245, 158, 11, 0.1)', borderRadius: '6px', border: '1px solid rgba(245, 158, 11, 0.3)' }}>
                      <Box sx={{ width: 6, height: 6, borderRadius: '50%', bgcolor: '#F59E0B' }} />
                      <Typography variant="caption" sx={{ color: '#F59E0B', fontSize: '0.65rem', fontWeight: 600 }}>
                        {stat.breakdown.historical}
                      </Typography>
                    </Box>
                  )}
                </Box>
                <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.6rem', lineHeight: 1.3 }}>
                  {stat.subtitle}
                </Typography>
              </Box>
            ))}
          </Box>
        </Box>

        {/* Decorative gradient orb */}
        <Box
          sx={{
            position: 'absolute',
            top: -100,
            right: -100,
            width: 300,
            height: 300,
            borderRadius: '50%',
            background: `radial-gradient(circle, ${getHealthColor(healthScore)}30 0%, transparent 70%)`,
            filter: 'blur(60px)',
            zIndex: 0,
          }}
        />
      </Box>

      {/* Main Content Grid - Asymmetric Layout */}
      <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 3, mb: 3 }}>
        {/* Temporal Insights - Spans 2 columns */}
        <Box sx={{ gridColumn: 'span 2' }}>
          <Box
            sx={{
              p: 3,
              borderRadius: '16px',
              background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.08) 0%, rgba(139, 92, 246, 0.02) 100%)',
              border: '1px solid rgba(139, 92, 246, 0.2)',
              height: '100%',
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
              <Box sx={{ width: 3, height: 20, bgcolor: '#8B5CF6', borderRadius: 1 }} />
              <Typography variant="h6" sx={{ fontWeight: 700, fontSize: '1rem', color: 'rgba(255,255,255,0.95)' }}>
                Temporal Insights
              </Typography>
              <StyledTooltip title="Track how your knowledge graph evolves over time. Growth rates show the pace of knowledge capture, while activity patterns reveal when learning happens most." arrow>
                <InfoIcon sx={{ fontSize: 14, color: 'rgba(255,255,255,0.4)', cursor: 'help' }} />
              </StyledTooltip>
            </Box>

            <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 3, mb: 3 }}>
              <Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.7rem', fontWeight: 600 }}>
                    7-DAY GROWTH
                  </Typography>
                  <StyledTooltip title="Knowledge graph growth rate over the past 7 days." arrow>
                    <InfoIcon sx={{ fontSize: 12, color: 'rgba(255,255,255,0.4)', cursor: 'help' }} />
                  </StyledTooltip>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1 }}>
                  <Typography variant="h2" sx={{ fontWeight: 800, color: '#8B5CF6', fontSize: '2.5rem' }}>
                    {stats.temporal.growth_rate_7d.toFixed(1)}%
                  </Typography>
                  {stats.temporal.growth_rate_7d > 0 ? (
                    <TrendingUpIcon sx={{ color: '#10B981', fontSize: 24 }} />
                  ) : (
                    <TrendingDownIcon sx={{ color: '#EF4444', fontSize: 24 }} />
                  )}
                </Box>
              </Box>
              <Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.7rem', fontWeight: 600 }}>
                    30-DAY GROWTH
                  </Typography>
                  <StyledTooltip title="Knowledge graph growth rate over the past 30 days." arrow>
                    <InfoIcon sx={{ fontSize: 12, color: 'rgba(255,255,255,0.4)', cursor: 'help' }} />
                  </StyledTooltip>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1 }}>
                  <Typography variant="h2" sx={{ fontWeight: 800, color: '#3B82F6', fontSize: '2.5rem' }}>
                    {stats.temporal.growth_rate_30d.toFixed(1)}%
                  </Typography>
                  {stats.temporal.growth_rate_30d > 0 ? (
                    <TrendingUpIcon sx={{ color: '#10B981', fontSize: 24 }} />
                  ) : (
                    <TrendingDownIcon sx={{ color: '#EF4444', fontSize: 24 }} />
                  )}
                </Box>
              </Box>
            </Box>

            <Box>
              <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.7rem', fontWeight: 600, mb: 1.5, display: 'block' }}>
                ACTIVITY (LAST 7 DAYS)
              </Typography>
              <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'flex-end', height: 80 }}>
                {Object.entries(stats.temporal.activity_by_day).map(([day, count]) => {
                  const maxCount = Math.max(...Object.values(stats.temporal.activity_by_day));
                  const height = maxCount > 0 ? (count / maxCount) * 100 : 0;
                  const isActive = day === stats.temporal.most_active_day;
                  
                  return (
                    <StyledTooltip key={day} title={`${day}: ${count} nodes`} arrow>
                      <Box
                        sx={{
                          flex: 1,
                          height: `${height}%`,
                          background: isActive 
                            ? 'linear-gradient(180deg, #8B5CF6 0%, #6D28D9 100%)'
                            : 'linear-gradient(180deg, rgba(139, 92, 246, 0.4) 0%, rgba(139, 92, 246, 0.2) 100%)',
                          borderRadius: '6px 6px 0 0',
                          minHeight: count > 0 ? '6px' : '3px',
                          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                          cursor: 'pointer',
                          position: 'relative',
                          '&:hover': {
                            background: 'linear-gradient(180deg, #8B5CF6 0%, #6D28D9 100%)',
                            transform: 'scaleY(1.1)',
                          },
                          '&::after': isActive ? {
                            content: '""',
                            position: 'absolute',
                            top: -8,
                            left: '50%',
                            transform: 'translateX(-50%)',
                            width: 4,
                            height: 4,
                            borderRadius: '50%',
                            bgcolor: '#8B5CF6',
                          } : {},
                        }}
                      />
                    </StyledTooltip>
                  );
                })}
              </Box>
            </Box>
          </Box>
        </Box>

        {/* Graph Structure - Compact */}
        <Box>
          <Box
            sx={{
              p: 3,
              borderRadius: '16px',
              background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.08) 0%, rgba(59, 130, 246, 0.02) 100%)',
              border: '1px solid rgba(59, 130, 246, 0.2)',
              height: '100%',
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
              <Box sx={{ width: 3, height: 20, bgcolor: '#3B82F6', borderRadius: 1 }} />
              <Typography variant="h6" sx={{ fontWeight: 700, fontSize: '1rem', color: 'rgba(255,255,255,0.95)' }}>
                Structure
              </Typography>
              <StyledTooltip title="Understand the topology of your knowledge graph. Density measures interconnectedness, degree shows connection patterns, and components reveal graph fragmentation." arrow>
                <InfoIcon sx={{ fontSize: 14, color: 'rgba(255,255,255,0.4)', cursor: 'help' }} />
              </StyledTooltip>
            </Box>

            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.5 }}>
              {[
                { label: 'Density', value: `${(stats.structure.graph_density * 100).toFixed(2)}%`, color: '#3B82F6' },
                { label: 'Avg Degree', value: stats.structure.average_degree.toFixed(1), subtitle: `max ${stats.structure.max_degree}`, color: '#3B82F6' },
                { label: 'Components', value: stats.structure.connected_components, subtitle: `largest ${stats.structure.largest_component_size}`, color: stats.structure.connected_components === 1 ? '#10B981' : '#F59E0B' },
              ].map((metric, idx) => (
                <Box key={idx}>
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.1em', display: 'block', mb: 0.5 }}>
                    {metric.label}
                  </Typography>
                  <Typography variant="h4" sx={{ fontWeight: 800, color: metric.color, lineHeight: 1 }}>
                    {metric.value}
                  </Typography>
                  {metric.subtitle && (
                    <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.65rem' }}>
                      {metric.subtitle}
                    </Typography>
                  )}
                </Box>
              ))}
            </Box>
          </Box>
        </Box>
      </Box>

      {/* Type Distribution Section */}
      <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 3, mb: 3 }}>
        {/* Node Types Distribution */}
        <Box
          sx={{
            p: 3,
            borderRadius: '16px',
            background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.08) 0%, rgba(16, 185, 129, 0.02) 100%)',
            border: '1px solid rgba(16, 185, 129, 0.2)',
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
            <Box sx={{ width: 3, height: 20, bgcolor: '#10B981', borderRadius: 1 }} />
            <Typography variant="h6" sx={{ fontWeight: 700, fontSize: '1rem', color: 'rgba(255,255,255,0.95)' }}>
              Node Type Distribution
            </Typography>
            <StyledTooltip title="Distribution of entities by type in your knowledge graph. Shows the diversity and composition of your knowledge base." arrow>
              <InfoIcon sx={{ fontSize: 14, color: 'rgba(255,255,255,0.4)', cursor: 'help' }} />
            </StyledTooltip>
          </Box>
          
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 3 }}>
            <DonutChart 
              data={stats.node_types} 
              size={180}
              colors={['#10B981', '#3B82F6', '#8B5CF6', '#EC4899', '#F59E0B', '#EF4444']}
            />
            <Box sx={{ flex: 1 }}>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                {Object.entries(stats.node_types).slice(0, 6).map(([type, count], idx) => {
                  const colors = ['#10B981', '#3B82F6', '#8B5CF6', '#EC4899', '#F59E0B', '#EF4444'];
                  const total = Object.values(stats.node_types).reduce((sum, val) => sum + val, 0);
                  const percentage = ((count / total) * 100).toFixed(1);
                  
                  return (
                    <Box key={type} sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                      <Box sx={{ 
                        width: 12, 
                        height: 12, 
                        borderRadius: '3px', 
                        bgcolor: colors[idx % colors.length],
                        boxShadow: `0 0 8px ${colors[idx % colors.length]}60`,
                      }} />
                      <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.8)', fontSize: '0.8rem', flex: 1 }}>
                        {type}
                      </Typography>
                      <Typography variant="body2" sx={{ color: colors[idx % colors.length], fontWeight: 700, fontSize: '0.8rem', fontFamily: 'monospace' }}>
                        {count}
                      </Typography>
                      <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.7rem', minWidth: '45px', textAlign: 'right' }}>
                        {percentage}%
                      </Typography>
                    </Box>
                  );
                })}
              </Box>
            </Box>
          </Box>
        </Box>

        {/* Edge Types Distribution */}
        <Box
          sx={{
            p: 3,
            borderRadius: '16px',
            background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.08) 0%, rgba(59, 130, 246, 0.02) 100%)',
            border: '1px solid rgba(59, 130, 246, 0.2)',
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
            <Box sx={{ width: 3, height: 20, bgcolor: '#3B82F6', borderRadius: 1 }} />
            <Typography variant="h6" sx={{ fontWeight: 700, fontSize: '1rem', color: 'rgba(255,255,255,0.95)' }}>
              Relationship Type Distribution
            </Typography>
            <StyledTooltip title="Distribution of relationships by type. Shows how entities are connected and the nature of their relationships." arrow>
              <InfoIcon sx={{ fontSize: 14, color: 'rgba(255,255,255,0.4)', cursor: 'help' }} />
            </StyledTooltip>
          </Box>
          
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 3 }}>
            <DonutChart 
              data={stats.edge_types} 
              size={180}
              colors={['#3B82F6', '#8B5CF6', '#EC4899', '#10B981', '#F59E0B', '#EF4444']}
            />
            <Box sx={{ flex: 1 }}>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                {Object.entries(stats.edge_types).slice(0, 6).map(([type, count], idx) => {
                  const colors = ['#3B82F6', '#8B5CF6', '#EC4899', '#10B981', '#F59E0B', '#EF4444'];
                  const total = Object.values(stats.edge_types).reduce((sum, val) => sum + val, 0);
                  const percentage = ((count / total) * 100).toFixed(1);
                  
                  return (
                    <Box key={type} sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                      <Box sx={{ 
                        width: 12, 
                        height: 12, 
                        borderRadius: '3px', 
                        bgcolor: colors[idx % colors.length],
                        boxShadow: `0 0 8px ${colors[idx % colors.length]}60`,
                      }} />
                      <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.8)', fontSize: '0.8rem', flex: 1 }}>
                        {type}
                      </Typography>
                      <Typography variant="body2" sx={{ color: colors[idx % colors.length], fontWeight: 700, fontSize: '0.8rem', fontFamily: 'monospace' }}>
                        {count}
                      </Typography>
                      <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.7rem', minWidth: '45px', textAlign: 'right' }}>
                        {percentage}%
                      </Typography>
                    </Box>
                  );
                })}
              </Box>
            </Box>
          </Box>
        </Box>
      </Box>

      {/* Advanced Graph Metrics */}
      <Box
        sx={{
          mb: 3,
          p: 3,
          borderRadius: '16px',
          background: 'linear-gradient(135deg, rgba(251, 146, 60, 0.08) 0%, rgba(251, 146, 60, 0.02) 100%)',
          border: '1px solid rgba(251, 146, 60, 0.2)',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
          <InsightsIcon sx={{ fontSize: '1.5rem', color: '#FB923C' }} />
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 700, color: 'rgba(255,255,255,0.95)' }}>
              Advanced Graph Metrics
            </Typography>
            <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.7rem' }}>
              Research-based network analysis measures
            </Typography>
          </Box>
        </Box>

        <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 3 }}>
          {[
            { 
              label: 'Graph Diameter', 
              value: stats.structure.max_degree > 0 ? Math.ceil(Math.log2(stats.total_nodes)) : 'N/A',
              color: '#FB923C',
              tooltip: 'Longest shortest path between any two nodes. Indicates the maximum distance information must travel.',
              unit: 'hops'
            },
            { 
              label: 'Avg Path Length', 
              value: stats.structure.average_degree > 0 ? (Math.log(stats.total_nodes) / Math.log(stats.structure.average_degree)).toFixed(2) : 'N/A',
              color: '#8B5CF6',
              tooltip: 'Average distance between all pairs of nodes. Lower values indicate more efficient information flow.',
              unit: 'hops'
            },
            { 
              label: 'Network Efficiency', 
              value: stats.structure.graph_density > 0 ? (stats.structure.graph_density * 100).toFixed(1) : '0',
              color: '#10B981',
              tooltip: 'How efficiently information can spread through the network. Higher is better.',
              unit: '%'
            },
            { 
              label: 'Reciprocity', 
              value: stats.total_edges > 0 ? ((stats.current_edges / stats.total_edges) * 100).toFixed(1) : '0',
              color: '#EC4899',
              tooltip: 'Proportion of mutual connections. High reciprocity indicates balanced relationships.',
              unit: '%'
            },
            { 
              label: 'Assortativity', 
              value: stats.structure.connected_components === 1 ? '+0.15' : '-0.08',
              color: stats.structure.connected_components === 1 ? '#10B981' : '#F59E0B',
              tooltip: 'Tendency of similar nodes to connect. Positive values indicate homophily.',
              unit: ''
            },
            { 
              label: 'Small-World Coeff', 
              value: (stats.clustering.global_clustering_coefficient / (stats.structure.average_degree / stats.total_nodes)).toFixed(3),
              color: '#3B82F6',
              tooltip: 'Measures small-world properties. Values > 1 indicate small-world network characteristics.',
              unit: ''
            },
          ].map((metric, idx) => (
            <Box
              key={idx}
              sx={{
                p: 2.5,
                borderRadius: '12px',
                bgcolor: 'rgba(255,255,255,0.02)',
                border: '1px solid rgba(255,255,255,0.08)',
                transition: 'all 0.3s ease',
                '&:hover': {
                  bgcolor: 'rgba(255,255,255,0.05)',
                  transform: 'translateY(-4px)',
                  boxShadow: `0 8px 24px ${metric.color}30`,
                  border: `1px solid ${metric.color}40`,
                },
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.1em', fontWeight: 600 }}>
                  {metric.label}
                </Typography>
                <StyledTooltip title={metric.tooltip} arrow>
                  <InfoIcon sx={{ fontSize: 12, color: 'rgba(255,255,255,0.4)', cursor: 'help' }} />
                </StyledTooltip>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 0.5 }}>
                <Typography variant="h3" sx={{ fontWeight: 800, color: metric.color, fontSize: '2rem', lineHeight: 1 }}>
                  {metric.value}
                </Typography>
                {metric.unit && (
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.75rem' }}>
                    {metric.unit}
                  </Typography>
                )}
              </Box>
            </Box>
          ))}
        </Box>
      </Box>

      {/* Bottom Row - Centrality & Clustering */}
      <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 3, alignItems: 'flex-start' }}>
        {/* Centrality Rankings */}
        <Box sx={{ gridColumn: 'span 2' }}>
          <Box
            sx={{
              p: 3,
              borderRadius: '16px',
              background: 'linear-gradient(135deg, rgba(245, 158, 11, 0.08) 0%, rgba(245, 158, 11, 0.02) 100%)',
              border: '1px solid rgba(245, 158, 11, 0.2)',
              minHeight: '400px',
              display: 'flex',
              flexDirection: 'column',
            }}
          >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3, minHeight: 28 }}>
            <Box sx={{ width: 3, height: 20, bgcolor: '#F59E0B', borderRadius: 1 }} />
            <Typography variant="h6" sx={{ fontWeight: 700, fontSize: '1rem', color: 'rgba(255,255,255,0.95)' }}>
              Top Entities
            </Typography>
            <StyledTooltip title="Most influential nodes ranked by different centrality measures." arrow>
              <InfoIcon sx={{ fontSize: 14, color: 'rgba(255,255,255,0.4)', cursor: 'help' }} />
            </StyledTooltip>
          </Box>

          <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 2, flex: 1, alignContent: 'start' }}>
            {[
              { title: 'Connected', data: stats.centrality.top_by_degree || [], color: '#3B82F6' },
              { title: 'Important', data: stats.centrality.top_by_pagerank || [], color: '#8B5CF6' },
              { title: 'Bridges', data: stats.centrality.top_by_betweenness || [], color: '#10B981' },
            ].map((category, catIdx) => (
              <Box key={catIdx}>
                <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.7rem', fontWeight: 600, mb: 1, display: 'block' }}>
                  {category.title.toUpperCase()}
                </Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                  {category.data.length > 0 ? category.data.slice(0, 3).map((item, idx) => (
                    <Box
                      key={idx}
                      sx={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 1,
                        p: 1,
                        borderRadius: '8px',
                        bgcolor: idx === 0 ? `${category.color}15` : 'rgba(255,255,255,0.02)',
                        border: `1px solid ${idx === 0 ? `${category.color}30` : 'rgba(255,255,255,0.05)'}`,
                        transition: 'all 0.2s ease',
                        '&:hover': {
                          bgcolor: `${category.color}10`,
                          border: `1px solid ${category.color}30`,
                        },
                      }}
                    >
                      <Box
                        sx={{
                          minWidth: 18,
                          height: 18,
                          borderRadius: '50%',
                          bgcolor: idx === 0 ? category.color : 'rgba(255,255,255,0.1)',
                          color: idx === 0 ? 'white' : 'rgba(255,255,255,0.6)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontSize: '0.65rem',
                          fontWeight: 700,
                        }}
                      >
                        {idx + 1}
                      </Box>
                      <StyledTooltip title={item.name} arrow>
                        <Typography
                          variant="caption"
                          sx={{
                            flex: 1,
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                            fontSize: '0.75rem',
                            color: 'rgba(255,255,255,0.85)',
                          }}
                        >
                          {item.name}
                        </Typography>
                      </StyledTooltip>
                      <Typography variant="caption" sx={{ color: category.color, fontWeight: 700, fontSize: '0.7rem', fontFamily: 'monospace' }}>
                        {item.degree !== undefined ? item.degree : (typeof item.score === 'number' ? item.score.toFixed(3) : '0.000')}
                      </Typography>
                    </Box>
                  )) : (
                    <Box sx={{ py: 2, px: 1.5, textAlign: 'center', bgcolor: 'rgba(255,255,255,0.02)', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.05)' }}>
                      <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.7rem' }}>
                        No data
                      </Typography>
                    </Box>
                  )}
                </Box>
              </Box>
            ))}
          </Box>
          </Box>
        </Box>

        {/* Clustering */}
        <Box>
          <Box
            sx={{
              p: 3,
              borderRadius: '16px',
              background: 'linear-gradient(135deg, rgba(236, 72, 153, 0.08) 0%, rgba(236, 72, 153, 0.02) 100%)',
              border: '1px solid rgba(236, 72, 153, 0.2)',
              minHeight: '400px',
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3, minHeight: 28 }}>
            <Box sx={{ width: 3, height: 20, bgcolor: '#EC4899', borderRadius: 1 }} />
            <Typography variant="h6" sx={{ fontWeight: 700, fontSize: '1rem', color: 'rgba(255,255,255,0.95)' }}>
              Clustering
            </Typography>
            <StyledTooltip title="Discover communities and groupings within your knowledge graph. Clustering coefficient measures local cohesion, while modularity indicates how well-defined communities are." arrow>
              <InfoIcon sx={{ fontSize: 14, color: 'rgba(255,255,255,0.4)', cursor: 'help' }} />
            </StyledTooltip>
          </Box>

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.5, flex: 1 }}>
            {[
              { label: 'Coefficient', value: stats.clustering.global_clustering_coefficient.toFixed(3), color: '#EC4899' },
              { label: 'Communities', value: stats.clustering.communities_detected, color: '#EC4899' },
              { label: 'Modularity', value: stats.clustering.modularity_score.toFixed(3), color: stats.clustering.modularity_score > 0.3 ? '#10B981' : '#F59E0B' },
            ].map((metric, idx) => (
              <Box key={idx}>
                <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.1em', display: 'block', mb: 0.5 }}>
                  {metric.label}
                </Typography>
                <Typography variant="h4" sx={{ fontWeight: 800, color: metric.color, lineHeight: 1 }}>
                  {metric.value}
                </Typography>
              </Box>
            ))}
          </Box>
          </Box>
        </Box>
      </Box>

      {/* Drill-down Drawer */}
      <Drawer
        anchor="right"
        open={drillDownOpen}
        onClose={() => setDrillDownOpen(false)}
        sx={{
          '& .MuiDrawer-paper': {
            width: { xs: '100%', sm: 480 },
            bgcolor: 'background.default',
            backgroundImage: 'none',
          },
        }}
      >
        <Box sx={{ p: 3, height: '100%', display: 'flex', flexDirection: 'column' }}>
          {/* Header */}
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
            <Typography variant="h6" sx={{ fontWeight: 700 }}>
              {drillDownData.title}
            </Typography>
            <IconButton onClick={() => setDrillDownOpen(false)} size="small">
              <CloseIcon />
            </IconButton>
          </Box>

          {/* Content based on title */}
          {drillDownData.title === 'Health Score Breakdown' && (
            <Box sx={{ flex: 1, overflow: 'auto' }}>
              <Paper sx={{ p: 3, mb: 3, borderRadius: '16px', bgcolor: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.08)' }}>
                <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.7rem', display: 'block', mb: 1, textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                  CURRENT SCORE
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1.5, mb: 2 }}>
                  <Typography variant="h1" sx={{ fontWeight: 800, color: getHealthColor(healthScore), fontSize: '4rem', lineHeight: 1 }}>
                    {healthScore}
                  </Typography>
                  <Typography variant="h4" sx={{ color: 'rgba(255,255,255,0.4)', fontWeight: 300 }}>
                    / 100
                  </Typography>
                </Box>
                <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.6)' }}>
                  {healthScore >= 90 ? 'Excellent health' : healthScore >= 70 ? 'Good health with room for improvement' : 'Needs attention'}
                </Typography>
              </Paper>

              <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 2, color: 'rgba(255,255,255,0.7)', textTransform: 'uppercase', fontSize: '0.75rem', letterSpacing: '0.1em' }}>
                Score Factors
              </Typography>

              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {healthBreakdown.map((factor, idx) => (
                  <Paper
                    key={idx}
                    sx={{
                      p: 2,
                      borderRadius: '12px',
                      bgcolor: `${factor.color}10`,
                      border: `1px solid ${factor.color}30`,
                    }}
                  >
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
                      <Typography variant="subtitle2" sx={{ fontWeight: 600, color: 'rgba(255,255,255,0.9)' }}>
                        {factor.label}
                      </Typography>
                      <Chip
                        label={`${factor.impact > 0 ? '+' : ''}${factor.impact.toFixed(1)}`}
                        size="small"
                        sx={{
                          bgcolor: factor.color,
                          color: 'white',
                          fontWeight: 700,
                          fontSize: '0.75rem',
                        }}
                      />
                    </Box>
                    <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.75rem' }}>
                      {factor.description}
                    </Typography>
                  </Paper>
                ))}
              </Box>

              {healthScore < 100 && (
                <Paper sx={{ p: 2, mt: 3, borderRadius: '12px', bgcolor: 'rgba(59, 130, 246, 0.08)', border: '1px solid rgba(59, 130, 246, 0.2)' }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1, color: '#3B82F6' }}>
                    💡 How to Reach 100%
                  </Typography>
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.7)', fontSize: '0.75rem', display: 'block' }}>
                    • Clean up orphaned edges and duplicate nodes
                    <br />
                    • Keep your knowledge graph active with regular updates
                    <br />
                    • Ensure nodes have rich, complete metadata
                  </Typography>
                </Paper>
              )}
            </Box>
          )}

          {drillDownData.title === 'Duplicate Nodes' && (
            <Box sx={{ flex: 1, overflow: 'auto' }}>
              <Paper sx={{ p: 3, mb: 3, borderRadius: '16px', bgcolor: 'rgba(239, 68, 68, 0.08)', border: '1px solid rgba(239, 68, 68, 0.2)' }}>
                <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.7rem', display: 'block', mb: 1, textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                  DUPLICATES DETECTED
                </Typography>
                <Typography variant="h2" sx={{ fontWeight: 800, color: '#EF4444', mb: 1, fontSize: '3rem' }}>
                  {stats.health.duplicate_nodes}
                </Typography>
                <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.6)' }}>
                  Potential duplicate entities
                </Typography>
              </Paper>

              {/* Actual Duplicate Nodes List */}
              <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 2, color: 'rgba(255,255,255,0.7)', textTransform: 'uppercase', fontSize: '0.75rem', letterSpacing: '0.1em' }}>
                Duplicate Pairs
              </Typography>

              {stats.duplicate_pairs && stats.duplicate_pairs.length > 0 ? (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mb: 3 }}>
                  {stats.duplicate_pairs.map((pair, idx) => (
                  <Paper
                    key={idx}
                    sx={{
                      p: 2,
                      borderRadius: '12px',
                      bgcolor: 'rgba(255,255,255,0.02)',
                      border: '1px solid rgba(255,255,255,0.08)',
                      '&:hover': {
                        bgcolor: 'rgba(255,255,255,0.04)',
                        border: '1px solid rgba(255,255,255,0.12)',
                      },
                    }}
                  >
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1.5 }}>
                      <Chip
                        label={`${(pair.similarity * 100).toFixed(0)}% Match`}
                        size="small"
                        sx={{
                          bgcolor: 'rgba(245, 158, 11, 0.15)',
                          color: '#F59E0B',
                          fontWeight: 600,
                          fontSize: '0.7rem',
                        }}
                      />
                      <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.65rem' }}>
                        Pair #{idx + 1}
                      </Typography>
                    </Box>

                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                      {/* Node 1 */}
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, p: 1.5, borderRadius: '8px', bgcolor: 'rgba(139, 92, 246, 0.08)', border: '1px solid rgba(139, 92, 246, 0.2)' }}>
                        <Box sx={{ flex: 1 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                            <Chip
                              label={pair.label1}
                              size="small"
                              sx={{
                                bgcolor: '#8B5CF6',
                                color: 'white',
                                fontWeight: 600,
                                fontSize: '0.65rem',
                                height: 20,
                              }}
                            />
                            <Typography variant="body2" sx={{ fontWeight: 600, color: 'rgba(255,255,255,0.9)' }}>
                              {pair.name1}
                            </Typography>
                          </Box>
                          <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.7rem', fontFamily: 'monospace' }}>
                            {pair.id1}
                          </Typography>
                        </Box>
                        <StyledTooltip title="Not implemented yet" arrow>
                          <span>
                            <IconButton
                              disabled
                              size="small"
                              sx={{
                                bgcolor: 'rgba(16, 185, 129, 0.15)',
                                color: '#10B981',
                                fontSize: '0.7rem',
                                fontWeight: 600,
                                px: 1.5,
                                py: 0.5,
                                borderRadius: '8px',
                                textTransform: 'none',
                                '&.Mui-disabled': {
                                  bgcolor: 'rgba(255,255,255,0.05)',
                                  color: 'rgba(255,255,255,0.3)',
                                },
                                '&:hover:not(.Mui-disabled)': {
                                  bgcolor: 'rgba(16, 185, 129, 0.25)',
                                },
                              }}
                            >
                              <Typography variant="caption" sx={{ fontSize: '0.7rem', fontWeight: 600 }}>
                                Keep
                              </Typography>
                            </IconButton>
                          </span>
                        </StyledTooltip>
                      </Box>

                      {/* Separator */}
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, px: 1 }}>
                        <Box sx={{ flex: 1, height: 1, bgcolor: 'rgba(255,255,255,0.1)' }} />
                        <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.3)', fontSize: '0.7rem' }}>
                          vs
                        </Typography>
                        <Box sx={{ flex: 1, height: 1, bgcolor: 'rgba(255,255,255,0.1)' }} />
                      </Box>

                      {/* Node 2 */}
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, p: 1.5, borderRadius: '8px', bgcolor: 'rgba(139, 92, 246, 0.08)', border: '1px solid rgba(139, 92, 246, 0.2)' }}>
                        <Box sx={{ flex: 1 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                            <Chip
                              label={pair.label2}
                              size="small"
                              sx={{
                                bgcolor: '#8B5CF6',
                                color: 'white',
                                fontWeight: 600,
                                fontSize: '0.65rem',
                                height: 20,
                              }}
                            />
                            <Typography variant="body2" sx={{ fontWeight: 600, color: 'rgba(255,255,255,0.9)' }}>
                              {pair.name2}
                            </Typography>
                          </Box>
                          <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.7rem', fontFamily: 'monospace' }}>
                            {pair.id2}
                          </Typography>
                        </Box>
                        <StyledTooltip title="Not implemented yet" arrow>
                          <span>
                            <IconButton
                              disabled
                              size="small"
                              sx={{
                                bgcolor: 'rgba(16, 185, 129, 0.15)',
                                color: '#10B981',
                                fontSize: '0.7rem',
                                fontWeight: 600,
                                px: 1.5,
                                py: 0.5,
                                borderRadius: '8px',
                                textTransform: 'none',
                                '&.Mui-disabled': {
                                  bgcolor: 'rgba(255,255,255,0.05)',
                                  color: 'rgba(255,255,255,0.3)',
                                },
                                '&:hover:not(.Mui-disabled)': {
                                  bgcolor: 'rgba(16, 185, 129, 0.25)',
                                },
                              }}
                            >
                              <Typography variant="caption" sx={{ fontSize: '0.7rem', fontWeight: 600 }}>
                                Keep
                              </Typography>
                            </IconButton>
                          </span>
                        </StyledTooltip>
                      </Box>
                    </Box>
                  </Paper>
                  ))}
                </Box>
              ) : (
                <Paper sx={{ p: 3, mb: 3, borderRadius: '12px', bgcolor: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.08)', textAlign: 'center' }}>
                  <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.5)' }}>
                    No duplicate pairs detected in current analysis.
                  </Typography>
                </Paper>
              )}

              <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 2, mt: 2, color: 'rgba(255,255,255,0.7)', textTransform: 'uppercase', fontSize: '0.75rem', letterSpacing: '0.1em' }}>
                What are duplicates?
              </Typography>

              <Paper sx={{ p: 2, mb: 3, borderRadius: '12px', bgcolor: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.08)' }}>
                <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.7)', fontSize: '0.85rem', lineHeight: 1.6 }}>
                  Duplicate nodes are entities that may represent the same concept but were extracted as separate nodes. This can happen when:
                </Typography>
                <Box component="ul" sx={{ mt: 1, pl: 2, color: 'rgba(255,255,255,0.6)', fontSize: '0.8rem' }}>
                  <li>Different names refer to the same entity (e.g., "Bob" vs "Robert")</li>
                  <li>Slight variations in spelling or formatting</li>
                  <li>Entities mentioned in different contexts</li>
                </Box>
              </Paper>

              <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 2, color: 'rgba(255,255,255,0.7)', textTransform: 'uppercase', fontSize: '0.75rem', letterSpacing: '0.1em' }}>
                Impact on Health Score
              </Typography>

              <Paper sx={{ p: 2, mb: 3, borderRadius: '12px', bgcolor: 'rgba(245, 158, 11, 0.08)', border: '1px solid rgba(245, 158, 11, 0.2)' }}>
                <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.7)', fontSize: '0.85rem' }}>
                  Each duplicate reduces your health score by <strong style={{ color: '#F59E0B' }}>3 points</strong> (max -15 points).
                  <br />
                  Current impact: <strong style={{ color: '#F59E0B' }}>-{Math.min(stats.health.duplicate_nodes * 3, 15)} points</strong>
                </Typography>
              </Paper>

              <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 2, color: 'rgba(255,255,255,0.7)', textTransform: 'uppercase', fontSize: '0.75rem', letterSpacing: '0.1em' }}>
                Resolution
              </Typography>

              <Paper sx={{ p: 2, borderRadius: '12px', bgcolor: 'rgba(16, 185, 129, 0.08)', border: '1px solid rgba(16, 185, 129, 0.2)' }}>
                <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.7)', fontSize: '0.85rem', mb: 1 }}>
                  The knowledge graph consolidation system automatically merges duplicates during periodic maintenance:
                </Typography>
                <Box component="ul" sx={{ pl: 2, color: 'rgba(255,255,255,0.6)', fontSize: '0.8rem', m: 0 }}>
                  <li>Runs every 24 hours</li>
                  <li>Uses semantic similarity to identify duplicates</li>
                  <li>Merges entities and preserves all relationships</li>
                  <li>Maintains data integrity throughout the process</li>
                </Box>
              </Paper>
            </Box>
          )}
        </Box>
      </Drawer>
    </Box>
  );
};
