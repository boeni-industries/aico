import React, { useState } from 'react';
import { Box, Typography, Paper, Tabs, Tab, TextField, Button, Chip, IconButton, ToggleButtonGroup, ToggleButton } from '@mui/material';
import { Search as SearchIcon, Code as CodeIcon, BarChart3 as AnalyticsIcon, GitBranch as GraphIcon, Info as InfoOutlinedIcon, CheckCircle as CheckCircleIcon, History as HistoryIcon, Filter as FilterListIcon, TrendingUp as TrendingUpIcon, TrendingDown as TrendingDownIcon, AlertTriangle as WarningIcon, Lightbulb as LightbulbIcon } from 'lucide-react';
import { KnowledgeGraphVisualization } from './KnowledgeGraphVisualization';
import { GQLQueryInterface } from './GQLQueryInterface';
import { StyledTooltip } from '../common/StyledTooltip';
import { GraphStats } from '../../api/kg';

interface KnowledgeGraphExplorerProps {
  nodes: any[];
  edges: any[];
  stats?: GraphStats | null;
}

export const KnowledgeGraphExplorer: React.FC<KnowledgeGraphExplorerProps> = ({ nodes, edges, stats }) => {
  const [activeTab, setActiveTab] = useState<'graph' | 'query' | 'analytics'>('graph');
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filteredNodes, setFilteredNodes] = useState(nodes);
  const [filteredEdges, setFilteredEdges] = useState(edges);
  const [statusFilter, setStatusFilter] = useState<'all' | 'current' | 'historical'>('current');
  const [isViewingHistory, setIsViewingHistory] = useState(false);
  
  // Calculate status counts
  const currentCount = nodes.filter(n => n.is_current === 1).length;
  const historicalCount = nodes.filter(n => n.is_current === 0).length;
  
  // Sync filteredNodes when nodes prop changes
  React.useEffect(() => {
    if (!isViewingHistory) {
      setFilteredNodes(nodes);
      setFilteredEdges(edges);
      console.log('KG Explorer: Loaded', nodes.length, 'nodes');
    }
  }, [nodes, edges, isViewingHistory]);
  
  const applyFilters = (query: string, status: 'all' | 'current' | 'historical') => {
    let filtered = nodes;
    
    // Apply status filter
    if (status === 'current') {
      filtered = filtered.filter(n => n.is_current === 1);
    } else if (status === 'historical') {
      filtered = filtered.filter(n => n.is_current === 0);
    }
    
    // Apply search filter
    if (query.trim()) {
      const lowerQuery = query.toLowerCase();
      filtered = filtered.filter(node => {
        const displayLabel = (node.label || '').toLowerCase();
        const nameProperty = (node.properties?.name || '').toLowerCase();
        const typeField = (node.type || '').toLowerCase();
        const matchesLabel = displayLabel.includes(lowerQuery) || nameProperty.includes(lowerQuery) || typeField.includes(lowerQuery);
        const matchesId = (node.id || '').toLowerCase().includes(lowerQuery);
        const matchesProperties = node.properties && Object.values(node.properties).some(value => {
          const strValue = String(value).toLowerCase();
          return strValue.includes(lowerQuery);
        });
        return matchesLabel || matchesId || matchesProperties;
      });
    }
    
    setFilteredNodes(filtered);
  };
  
  const handleSearchChange = (query: string) => {
    setSearchQuery(query);
    applyFilters(query, statusFilter);
  };
  
  const handleStatusFilterChange = (event: React.MouseEvent<HTMLElement>, newStatus: 'all' | 'current' | 'historical' | null) => {
    if (newStatus !== null) {
      setStatusFilter(newStatus);
      applyFilters(searchQuery, newStatus);
    }
  };
  
  const handleClearSearch = () => {
    setSearchQuery('');
    setFilteredNodes(nodes);
  };
  
  // Update filtered nodes when nodes prop changes
  React.useEffect(() => {
    applyFilters(searchQuery, statusFilter);
  }, [nodes]);

  return (
    <Box>
      {/* Search & Filters */}
      <Paper sx={{ p: 2.5, mb: 3, borderRadius: '16px', border: '1px solid', borderColor: 'divider' }}>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', mb: 2, flexWrap: 'wrap' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <FilterListIcon sx={{ color: 'text.secondary', fontSize: 20 }} />
            <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Status Filter
            </Typography>
          </Box>
          <ToggleButtonGroup
            value={statusFilter}
            exclusive
            onChange={handleStatusFilterChange}
            size="small"
            sx={{
              '& .MuiToggleButton-root': {
                px: 2,
                py: 0.5,
                fontSize: '0.75rem',
                textTransform: 'none',
                border: '1px solid',
                borderColor: 'divider',
                '&.Mui-selected': {
                  bgcolor: 'primary.main',
                  color: 'primary.contrastText',
                  '&:hover': {
                    bgcolor: 'primary.dark',
                  },
                },
              },
            }}
          >
            <ToggleButton value="all">
              All ({nodes.length})
            </ToggleButton>
            <ToggleButton value="current">
              <CheckCircleIcon sx={{ fontSize: 16, mr: 0.5 }} />
              Current ({currentCount})
            </ToggleButton>
            <ToggleButton value="historical">
              <HistoryIcon sx={{ fontSize: 16, mr: 0.5 }} />
              Historical ({historicalCount})
            </ToggleButton>
          </ToggleButtonGroup>
        </Box>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <SearchIcon sx={{ color: 'text.secondary' }} />
          <TextField
            fullWidth
            placeholder={`Search ${filteredNodes.length.toLocaleString()} nodes by label, property, or ID...`}
            value={searchQuery}
            onChange={(e) => handleSearchChange(e.target.value)}
            variant="outlined"
            size="small"
            sx={{
              '& .MuiOutlinedInput-root': {
                borderRadius: '12px',
              },
            }}
          />
          {searchQuery && (
            <Button
              variant="outlined"
              onClick={handleClearSearch}
              sx={{
                borderRadius: '12px',
                textTransform: 'none',
                px: 2,
              }}
            >
              Clear
            </Button>
          )}
        </Box>
        {searchQuery && (
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.75rem', ml: 5 }}>
            {filteredNodes.length === nodes.length 
              ? `Showing all ${nodes.length} nodes`
              : `Found ${filteredNodes.length} of ${nodes.length} nodes`}
          </Typography>
        )}
      </Paper>

      {/* Tabs */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={activeTab} onChange={(_, v) => setActiveTab(v)}>
          <Tab icon={<GraphIcon />} label="Graph View" value="graph" sx={{ textTransform: 'none' }} />
          <Tab icon={<CodeIcon />} label="GQL Query" value="query" sx={{ textTransform: 'none' }} />
          <Tab icon={<AnalyticsIcon />} label="Analytics" value="analytics" sx={{ textTransform: 'none' }} />
        </Tabs>
      </Box>

      {/* Tab Content */}
      {activeTab === 'graph' && (
        <Box>
          <KnowledgeGraphVisualization
            nodes={filteredNodes}
            edges={filteredEdges.filter(edge => 
              filteredNodes.some(n => n.id === edge.source) && 
              filteredNodes.some(n => n.id === edge.target)
            )}
            onNodeClick={(node) => setSelectedNode(node)}
            onTemporalStateChange={(historicalNodes, historicalEdges, isLive) => {
              if (isLive) {
                // Return to live view - reapply current filters
                console.log('[EXPLORER] Returning to live view:', nodes.length, 'nodes,', edges.length, 'edges');
                setIsViewingHistory(false);
                applyFilters(searchQuery, statusFilter);
              } else {
                // Switch to historical view - apply status filter to historical data
                console.log('[EXPLORER] Switching to historical view:', historicalNodes.length, 'nodes,', historicalEdges.length, 'edges');
                
                setIsViewingHistory(true);
                
                // Apply status filter to historical nodes
                let filtered = historicalNodes;
                if (statusFilter === 'current') {
                  filtered = filtered.filter(n => n.is_current === 1);
                } else if (statusFilter === 'historical') {
                  filtered = filtered.filter(n => n.is_current === 0);
                }
                
                // Apply search filter if active
                if (searchQuery.trim()) {
                  const lowerQuery = searchQuery.toLowerCase();
                  filtered = filtered.filter(node => {
                    const displayLabel = (node.label || '').toLowerCase();
                    const nameProperty = (node.properties?.name || '').toLowerCase();
                    const typeField = (node.type || '').toLowerCase();
                    const matchesLabel = displayLabel.includes(lowerQuery) || nameProperty.includes(lowerQuery) || typeField.includes(lowerQuery);
                    const matchesId = (node.id || '').toLowerCase().includes(lowerQuery);
                    const matchesProperties = node.properties && Object.values(node.properties).some(value => {
                      const strValue = String(value).toLowerCase();
                      return strValue.includes(lowerQuery);
                    });
                    return matchesLabel || matchesId || matchesProperties;
                  });
                }
                
                // Filter edges to only include those connected to visible nodes
                const nodeIds = new Set(filtered.map(n => n.id));
                const validEdges = historicalEdges.filter(e => nodeIds.has(e.source) && nodeIds.has(e.target));
                
                console.log('[EXPLORER] Applied filters - showing', filtered.length, 'nodes,', validEdges.length, 'edges');
                
                setFilteredNodes(filtered);
                setFilteredEdges(validEdges);
              }
            }}
          />
        </Box>
      )}

      {activeTab === 'query' && (
        <GQLQueryInterface />
      )}

      {activeTab === 'analytics' && stats && (
        <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 3 }}>
          {/* PageRank Analysis - REAL DATA */}
          <Paper 
            sx={{ 
              p: 3, 
              borderRadius: '16px', 
              background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.08) 0%, rgba(139, 92, 246, 0.02) 100%)',
              border: '1px solid rgba(139, 92, 246, 0.2)',
              transition: 'all 0.3s ease',
              '&:hover': {
                transform: 'translateY(-4px)',
                boxShadow: '0 12px 32px rgba(139, 92, 246, 0.2)',
              },
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
              <Box sx={{ width: 3, height: 20, bgcolor: '#8B5CF6', borderRadius: 1 }} />
              <Typography variant="h6" sx={{ fontWeight: 700, fontSize: '1rem' }}>
                PageRank Analysis
              </Typography>
              <StyledTooltip title="Node importance based on incoming connections. Higher scores indicate more influential entities." arrow>
                <InfoOutlinedIcon sx={{ fontSize: 14, color: 'rgba(255,255,255,0.4)', cursor: 'help' }} />
              </StyledTooltip>
            </Box>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2.5, fontSize: '0.8rem' }}>
              Top {stats.centrality.top_by_pagerank.length} most influential nodes
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
              {stats.centrality.top_by_pagerank.slice(0, 5).map((item, i) => {
                const colors = ['#8B5CF6', '#A78BFA', '#C4B5FD', '#DDD6FE', '#EDE9FE'];
                return (
                  <Box 
                    key={item.id} 
                    sx={{ 
                      display: 'flex', 
                      justifyContent: 'space-between', 
                      alignItems: 'center', 
                      p: 1.5, 
                      bgcolor: `${colors[i]}15`, 
                      borderRadius: '10px',
                      border: `1px solid ${colors[i]}30`,
                      transition: 'all 0.2s ease',
                      '&:hover': {
                        bgcolor: `${colors[i]}25`,
                        transform: 'translateX(4px)',
                      },
                    }}
                  >
                    <Box sx={{ flex: 1 }}>
                      <Typography variant="body2" sx={{ fontWeight: 600, fontSize: '0.85rem', mb: 0.3 }}>
                        {item.label || item.name || `Node ${item.id.substring(0, 8)}`}
                      </Typography>
                      <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.7rem' }}>
                        ID: {item.id.substring(0, 12)}...
                      </Typography>
                    </Box>
                    <Chip
                      label={(item.score || 0).toFixed(4)}
                      size="small"
                      sx={{
                        bgcolor: colors[i],
                        color: 'white',
                        fontWeight: 700,
                        fontSize: '0.75rem',
                        fontFamily: 'monospace',
                      }}
                    />
                  </Box>
                );
              })}
            </Box>
          </Paper>

          {/* Community Detection - REAL DATA */}
          <Paper 
            sx={{ 
              p: 3, 
              borderRadius: '16px',
              background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.08) 0%, rgba(16, 185, 129, 0.02) 100%)',
              border: '1px solid rgba(16, 185, 129, 0.2)',
              transition: 'all 0.3s ease',
              '&:hover': {
                transform: 'translateY(-4px)',
                boxShadow: '0 12px 32px rgba(16, 185, 129, 0.2)',
              },
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
              <Box sx={{ width: 3, height: 20, bgcolor: '#10B981', borderRadius: 1 }} />
              <Typography variant="h6" sx={{ fontWeight: 700, fontSize: '1rem' }}>
                Community Detection
              </Typography>
              <StyledTooltip title="Detected clusters of related entities. Communities reveal how knowledge naturally groups together." arrow>
                <InfoOutlinedIcon sx={{ fontSize: 14, color: 'rgba(255,255,255,0.4)', cursor: 'help' }} />
              </StyledTooltip>
            </Box>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2.5, fontSize: '0.8rem' }}>
              {stats.clustering.communities_detected} communities detected
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, p: 2, bgcolor: 'rgba(16, 185, 129, 0.1)', borderRadius: '10px', border: '1px solid rgba(16, 185, 129, 0.3)' }}>
                <Box sx={{ textAlign: 'center', flex: 1 }}>
                  <Typography variant="h3" sx={{ fontWeight: 800, color: '#10B981', fontSize: '2rem', lineHeight: 1 }}>
                    {stats.clustering.communities_detected}
                  </Typography>
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.7rem', textTransform: 'uppercase' }}>
                    Communities
                  </Typography>
                </Box>
                <Box sx={{ width: 1, height: 40, bgcolor: 'rgba(255,255,255,0.1)' }} />
                <Box sx={{ textAlign: 'center', flex: 1 }}>
                  <Typography variant="h3" sx={{ fontWeight: 800, color: '#3B82F6', fontSize: '2rem', lineHeight: 1 }}>
                    {stats.clustering.modularity_score.toFixed(2)}
                  </Typography>
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.7rem', textTransform: 'uppercase' }}>
                    Modularity
                  </Typography>
                </Box>
              </Box>
              <Box sx={{ p: 2, bgcolor: 'rgba(255,255,255,0.02)', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.08)' }}>
                <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.7rem', display: 'block', mb: 1 }}>
                  CLUSTERING COEFFICIENT
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1 }}>
                  <Typography variant="h4" sx={{ fontWeight: 800, color: '#8B5CF6', fontSize: '1.5rem' }}>
                    {(stats.clustering.global_clustering_coefficient * 100).toFixed(1)}%
                  </Typography>
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)' }}>
                    nodes cluster together
                  </Typography>
                </Box>
              </Box>
            </Box>
          </Paper>

          {/* Temporal Patterns - REAL DATA */}
          <Paper 
            sx={{ 
              p: 3, 
              borderRadius: '16px',
              background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.08) 0%, rgba(59, 130, 246, 0.02) 100%)',
              border: '1px solid rgba(59, 130, 246, 0.2)',
              transition: 'all 0.3s ease',
              '&:hover': {
                transform: 'translateY(-4px)',
                boxShadow: '0 12px 32px rgba(59, 130, 246, 0.2)',
              },
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
              <Box sx={{ width: 3, height: 20, bgcolor: '#3B82F6', borderRadius: 1 }} />
              <Typography variant="h6" sx={{ fontWeight: 700, fontSize: '1rem' }}>
                Temporal Patterns
              </Typography>
              <StyledTooltip title="Activity trends showing how your knowledge graph evolves over time." arrow>
                <InfoOutlinedIcon sx={{ fontSize: 14, color: 'rgba(255,255,255,0.4)', cursor: 'help' }} />
              </StyledTooltip>
            </Box>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2.5, fontSize: '0.8rem' }}>
              Growth and activity insights
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, p: 1.5, bgcolor: 'rgba(59, 130, 246, 0.1)', borderRadius: '8px' }}>
                {stats.temporal.growth_rate_7d > 0 ? (
                  <TrendingUpIcon sx={{ color: '#10B981', fontSize: 20 }} />
                ) : (
                  <TrendingDownIcon sx={{ color: '#EF4444', fontSize: 20 }} />
                )}
                <Box sx={{ flex: 1 }}>
                  <Typography variant="body2" sx={{ fontSize: '0.8rem', fontWeight: 600 }}>
                    {stats.temporal.growth_rate_7d.toFixed(1)}% growth (7 days)
                  </Typography>
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.7rem' }}>
                    {stats.current_nodes - Math.round(stats.current_nodes / (1 + stats.temporal.growth_rate_7d / 100))} new nodes
                  </Typography>
                </Box>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, p: 1.5, bgcolor: 'rgba(139, 92, 246, 0.1)', borderRadius: '8px' }}>
                {stats.temporal.growth_rate_30d > 0 ? (
                  <TrendingUpIcon sx={{ color: '#10B981', fontSize: 20 }} />
                ) : (
                  <TrendingDownIcon sx={{ color: '#EF4444', fontSize: 20 }} />
                )}
                <Box sx={{ flex: 1 }}>
                  <Typography variant="body2" sx={{ fontSize: '0.8rem', fontWeight: 600 }}>
                    {stats.temporal.growth_rate_30d.toFixed(1)}% growth (30 days)
                  </Typography>
                  <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.7rem' }}>
                    Long-term trend
                  </Typography>
                </Box>
              </Box>
              <Box sx={{ p: 1.5, bgcolor: 'rgba(255,255,255,0.02)', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.08)' }}>
                <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.7rem', display: 'block', mb: 0.5 }}>
                  PEAK ACTIVITY
                </Typography>
                <Typography variant="body2" sx={{ fontSize: '0.8rem', fontWeight: 600 }}>
                  {Object.entries(stats.temporal.activity_by_day).reduce((max, [day, count]) => 
                    count > max.count ? { day, count } : max, 
                    { day: 'Unknown', count: 0 }
                  ).day}
                </Typography>
                <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)', fontSize: '0.7rem' }}>
                  Most active day of week
                </Typography>
              </Box>
            </Box>
          </Paper>

          {/* Knowledge Gaps - REAL DATA */}
          <Paper 
            sx={{ 
              p: 3, 
              borderRadius: '16px',
              background: 'linear-gradient(135deg, rgba(245, 158, 11, 0.08) 0%, rgba(245, 158, 11, 0.02) 100%)',
              border: '1px solid rgba(245, 158, 11, 0.2)',
              transition: 'all 0.3s ease',
              '&:hover': {
                transform: 'translateY(-4px)',
                boxShadow: '0 12px 32px rgba(245, 158, 11, 0.2)',
              },
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
              <Box sx={{ width: 3, height: 20, bgcolor: '#F59E0B', borderRadius: 1 }} />
              <Typography variant="h6" sx={{ fontWeight: 700, fontSize: '1rem' }}>
                Knowledge Gaps
              </Typography>
              <StyledTooltip title="Areas needing attention: orphaned edges, duplicates, stale data, and isolated nodes." arrow>
                <InfoOutlinedIcon sx={{ fontSize: 14, color: 'rgba(255,255,255,0.4)', cursor: 'help' }} />
              </StyledTooltip>
            </Box>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2.5, fontSize: '0.8rem' }}>
              Data quality issues detected
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
              {stats.health.orphaned_edges > 0 && (
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, p: 1.5, bgcolor: 'rgba(239, 68, 68, 0.1)', borderRadius: '8px', border: '1px solid rgba(239, 68, 68, 0.2)' }}>
                  <WarningIcon sx={{ color: '#EF4444', fontSize: 18 }} />
                  <Box sx={{ flex: 1 }}>
                    <Typography variant="body2" sx={{ fontSize: '0.8rem', fontWeight: 600 }}>
                      {stats.health.orphaned_edges} orphaned edges
                    </Typography>
                    <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.7rem' }}>
                      Relationships without valid nodes
                    </Typography>
                  </Box>
                </Box>
              )}
              {stats.health.duplicate_nodes > 0 && (
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, p: 1.5, bgcolor: 'rgba(245, 158, 11, 0.1)', borderRadius: '8px', border: '1px solid rgba(245, 158, 11, 0.2)' }}>
                  <WarningIcon sx={{ color: '#F59E0B', fontSize: 18 }} />
                  <Box sx={{ flex: 1 }}>
                    <Typography variant="body2" sx={{ fontSize: '0.8rem', fontWeight: 600 }}>
                      {stats.health.duplicate_nodes} duplicate nodes
                    </Typography>
                    <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.7rem' }}>
                      Potential consolidation opportunities
                    </Typography>
                  </Box>
                </Box>
              )}
              {stats.health.stale_nodes_percent > 0 && (
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, p: 1.5, bgcolor: 'rgba(139, 92, 246, 0.1)', borderRadius: '8px', border: '1px solid rgba(139, 92, 246, 0.2)' }}>
                  <WarningIcon sx={{ color: '#8B5CF6', fontSize: 18 }} />
                  <Box sx={{ flex: 1 }}>
                    <Typography variant="body2" sx={{ fontSize: '0.8rem', fontWeight: 600 }}>
                      {stats.health.stale_nodes_percent.toFixed(1)}% stale data
                    </Typography>
                    <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.7rem' }}>
                      Not updated in 30+ days
                    </Typography>
                  </Box>
                </Box>
              )}
              {stats.structure.connected_components > 1 && (
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, p: 1.5, bgcolor: 'rgba(59, 130, 246, 0.1)', borderRadius: '8px', border: '1px solid rgba(59, 130, 246, 0.2)' }}>
                  <LightbulbIcon sx={{ color: '#3B82F6', fontSize: 18 }} />
                  <Box sx={{ flex: 1 }}>
                    <Typography variant="body2" sx={{ fontSize: '0.8rem', fontWeight: 600 }}>
                      {stats.structure.connected_components} isolated clusters
                    </Typography>
                    <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.7rem' }}>
                      Disconnected knowledge groups
                    </Typography>
                  </Box>
                </Box>
              )}
              {stats.health.orphaned_edges === 0 && stats.health.duplicate_nodes === 0 && stats.health.stale_nodes_percent === 0 && stats.structure.connected_components === 1 && (
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, p: 2, bgcolor: 'rgba(16, 185, 129, 0.1)', borderRadius: '8px', border: '1px solid rgba(16, 185, 129, 0.2)' }}>
                  <CheckCircleIcon sx={{ color: '#10B981', fontSize: 24 }} />
                  <Box>
                    <Typography variant="body2" sx={{ fontSize: '0.85rem', fontWeight: 600, color: '#10B981' }}>
                      Excellent Data Quality!
                    </Typography>
                    <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.7rem' }}>
                      No significant issues detected
                    </Typography>
                  </Box>
                </Box>
              )}
            </Box>
          </Paper>
        </Box>
      )}

    </Box>
  );
};
