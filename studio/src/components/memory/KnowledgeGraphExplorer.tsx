import React, { useState } from 'react';
import { Box, Typography, Paper, Tabs, Tab, TextField, Button, Chip, IconButton, ToggleButtonGroup, ToggleButton } from '@mui/material';
import {
  Search as SearchIcon,
  Code as CodeIcon,
  Analytics as AnalyticsIcon,
  AccountTree as GraphIcon,
  Info as InfoIcon,
  InfoOutlined as InfoOutlinedIcon,
  CheckCircle as CheckCircleIcon,
  History as HistoryIcon,
  FilterList as FilterListIcon,
} from '@mui/icons-material';
import { KnowledgeGraphVisualization } from './KnowledgeGraphVisualization';
import { StyledTooltip } from '../common/StyledTooltip';

interface KnowledgeGraphExplorerProps {
  nodes: any[];
  edges: any[];
  stats?: {
    total_node_properties: number;
    storage_size_mb: number;
  };
}

export const KnowledgeGraphExplorer: React.FC<KnowledgeGraphExplorerProps> = ({ nodes, edges, stats }) => {
  const [activeTab, setActiveTab] = useState<'graph' | 'query' | 'analytics' | 'properties'>('graph');
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filteredNodes, setFilteredNodes] = useState(nodes);
  const [statusFilter, setStatusFilter] = useState<'all' | 'current' | 'historical'>('all');
  
  // Calculate status counts
  const currentCount = nodes.filter(n => n.is_current === 1).length;
  const historicalCount = nodes.filter(n => n.is_current === 0).length;
  
  // Sync filteredNodes when nodes prop changes
  React.useEffect(() => {
    setFilteredNodes(nodes);
    console.log('KG Explorer: Loaded', nodes.length, 'nodes');
    if (nodes.length > 0) {
      console.log('Sample node structure:', {
        id: nodes[0].id,
        label: nodes[0].label,
        type: nodes[0].type,
        properties: nodes[0].properties,
        hasProperties: !!nodes[0].properties,
        propertyKeys: nodes[0].properties ? Object.keys(nodes[0].properties) : []
      });
      
      // Show a few more samples to understand the data
      console.log('First 5 nodes labels:', nodes.slice(0, 5).map(n => ({
        label: n.label,
        type: n.type,
        name: n.properties?.name
      })));
    }
  }, [nodes]);
  
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
          <Tab icon={<InfoIcon />} label="Properties" value="properties" sx={{ textTransform: 'none' }} />
        </Tabs>
      </Box>

      {/* Tab Content */}
      {activeTab === 'graph' && (
        <Box>
          <KnowledgeGraphVisualization
            nodes={filteredNodes}
            edges={edges.filter(edge => 
              filteredNodes.some(n => n.id === edge.source) && 
              filteredNodes.some(n => n.id === edge.target)
            )}
            onNodeClick={(node) => setSelectedNode(node)}
          />
          
          {selectedNode && (
            <Paper sx={{ mt: 3, p: 3, borderRadius: '16px', border: '1px solid', borderColor: 'divider' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                <Typography variant="h6" sx={{ fontWeight: 600, flex: 1 }}>
                  Node Details: {selectedNode.label}
                </Typography>
                <Chip
                  icon={selectedNode.is_current === 1 ? <CheckCircleIcon /> : <HistoryIcon />}
                  label={selectedNode.is_current === 1 ? 'Current' : 'Historical'}
                  size="small"
                  sx={{
                    bgcolor: selectedNode.is_current === 1 ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                    color: selectedNode.is_current === 1 ? '#10B981' : '#F59E0B',
                    border: `1px solid ${selectedNode.is_current === 1 ? '#10B981' : '#F59E0B'}`,
                    fontWeight: 600,
                    fontSize: '0.7rem',
                    '& .MuiChip-icon': {
                      color: selectedNode.is_current === 1 ? '#10B981' : '#F59E0B',
                    },
                  }}
                />
              </Box>
              <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 2 }}>
                <Box>
                  <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                    TYPE
                  </Typography>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>
                    {selectedNode.type.toUpperCase()}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                    CONNECTIONS
                  </Typography>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>
                    {selectedNode.connections}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                    IMPORTANCE
                  </Typography>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>
                    {(selectedNode.importance * 100).toFixed(0)}%
                  </Typography>
                </Box>
                {selectedNode.properties && (
                  <Box sx={{ gridColumn: '1 / -1' }}>
                    <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', mb: 1, display: 'block' }}>
                      PROPERTIES
                    </Typography>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                      {Object.entries(selectedNode.properties).map(([key, value]) => (
                        <Box key={key} sx={{ display: 'flex', justifyContent: 'space-between', p: 1, bgcolor: 'rgba(255,255,255,0.02)', borderRadius: '8px' }}>
                          <Typography variant="body2" sx={{ fontSize: '0.8rem', color: 'text.secondary' }}>
                            {key}:
                          </Typography>
                          <Typography variant="body2" sx={{ fontSize: '0.8rem', fontWeight: 600 }}>
                            {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                          </Typography>
                        </Box>
                      ))}
                    </Box>
                  </Box>
                )}
              </Box>
            </Paper>
          )}
        </Box>
      )}

      {activeTab === 'query' && (
        <Paper sx={{ p: 3, borderRadius: '16px', border: '1px solid', borderColor: 'divider' }}>
          <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
            GQL/Cypher Query Interface
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Execute graph queries using ISO standard GQL syntax via GrandCypher
          </Typography>
          
          <TextField
            fullWidth
            multiline
            rows={6}
            placeholder={`MATCH (p:PERSON)-[:WORKING_ON]->(proj:PROJECT)\nWHERE proj.status = 'active'\nRETURN p.name, proj.name, proj.progress`}
            variant="outlined"
            sx={{
              mb: 2,
              '& .MuiOutlinedInput-root': {
                fontFamily: 'monospace',
                fontSize: '0.9rem',
              },
            }}
          />
          
          <Button variant="contained" startIcon={<CodeIcon />} sx={{ textTransform: 'none' }}>
            Execute Query
          </Button>

          <Box sx={{ mt: 3, p: 2, bgcolor: 'rgba(59, 130, 246, 0.08)', borderRadius: '12px' }}>
            <Typography variant="caption" sx={{ fontSize: '0.7rem', fontWeight: 600, mb: 1, display: 'block' }}>
              QUERY CAPABILITIES
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
              <Typography variant="body2" sx={{ fontSize: '0.75rem' }}>
                • Pattern matching with MATCH clauses
              </Typography>
              <Typography variant="body2" sx={{ fontSize: '0.75rem' }}>
                • Property filtering (WHERE status = 'active')
              </Typography>
              <Typography variant="body2" sx={{ fontSize: '0.75rem' }}>
                • Multi-hop traversal (MATCH (a)-[*1..3]{'->'} (b))
              </Typography>
              <Typography variant="body2" sx={{ fontSize: '0.75rem' }}>
                • Temporal queries (WHERE valid_from {'>'} '2024-01-01')
              </Typography>
              <Typography variant="body2" sx={{ fontSize: '0.75rem' }}>
                • Aggregations (COUNT, AVG, SUM)
              </Typography>
            </Box>
          </Box>
        </Paper>
      )}

      {activeTab === 'analytics' && (
        <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 3 }}>
          <Paper sx={{ p: 3, borderRadius: '16px', border: '1px solid', borderColor: 'divider' }}>
            <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
              PageRank Analysis
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2, fontSize: '0.85rem' }}>
              Node importance based on incoming connections
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
              {['Michael', 'English Practice', 'Become Fluent'].map((entity, i) => (
                <Box key={entity} sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', p: 1.5, bgcolor: 'rgba(139, 92, 246, 0.08)', borderRadius: '8px' }}>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>
                    {entity}
                  </Typography>
                  <Chip
                    label={`${(1.0 - i * 0.15).toFixed(2)}`}
                    size="small"
                    sx={{
                      bgcolor: 'rgba(139, 92, 246, 0.2)',
                      color: '#8B5CF6',
                      fontWeight: 700,
                    }}
                  />
                </Box>
              ))}
            </Box>
          </Paper>

          <Paper sx={{ p: 3, borderRadius: '16px', border: '1px solid', borderColor: 'divider' }}>
            <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
              Community Detection
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2, fontSize: '0.85rem' }}>
              Relationship clusters and groups
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
              {[
                { name: 'Learning Cluster', count: 8, color: '#10B981' },
                { name: 'Work Projects', count: 12, color: '#3B82F6' },
                { name: 'Personal Goals', count: 6, color: '#EC4899' },
              ].map((cluster) => (
                <Box key={cluster.name} sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', p: 1.5, bgcolor: `${cluster.color}15`, borderRadius: '8px', border: '1px solid', borderColor: `${cluster.color}30` }}>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>
                    {cluster.name}
                  </Typography>
                  <Typography variant="caption" sx={{ color: cluster.color, fontWeight: 700 }}>
                    {cluster.count} nodes
                  </Typography>
                </Box>
              ))}
            </Box>
          </Paper>

          <Paper sx={{ p: 3, borderRadius: '16px', border: '1px solid', borderColor: 'divider' }}>
            <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
              Temporal Patterns
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2, fontSize: '0.85rem' }}>
              Activity trends over time
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              <Typography variant="body2" sx={{ fontSize: '0.8rem' }}>
                • 15 new nodes this week
              </Typography>
              <Typography variant="body2" sx={{ fontSize: '0.8rem' }}>
                • 23 relationships updated
              </Typography>
              <Typography variant="body2" sx={{ fontSize: '0.8rem' }}>
                • Peak activity: Weekday afternoons
              </Typography>
              <Typography variant="body2" sx={{ fontSize: '0.8rem' }}>
                • Growing interest: Language learning
              </Typography>
            </Box>
          </Paper>

          <Paper sx={{ p: 3, borderRadius: '16px', border: '1px solid', borderColor: 'divider' }}>
            <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
              Knowledge Gaps
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2, fontSize: '0.85rem' }}>
              Missing connections and information
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              <Typography variant="body2" sx={{ fontSize: '0.8rem' }}>
                • 3 projects without deadlines
              </Typography>
              <Typography variant="body2" sx={{ fontSize: '0.8rem' }}>
                • 5 goals without clear tasks
              </Typography>
              <Typography variant="body2" sx={{ fontSize: '0.8rem' }}>
                • 2 isolated entity clusters
              </Typography>
              <Typography variant="body2" sx={{ fontSize: '0.8rem' }}>
                • Missing: Skill proficiency levels
              </Typography>
            </Box>
          </Paper>
        </Box>
      )}

      {activeTab === 'properties' && (
        <Paper sx={{ p: 3, borderRadius: '16px', border: '1px solid', borderColor: 'divider' }}>
          <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
            Property Schema & Examples
          </Typography>
          
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            {[
              {
                type: 'PROJECT',
                properties: {
                  name: 'English Practice',
                  status: 'active',
                  progress: 0.6,
                  deadline: '2025-12-31',
                  priority: 1,
                  description: 'Daily English conversation practice',
                },
              },
              {
                type: 'GOAL',
                properties: {
                  name: 'Become Fluent',
                  type: 'long_term',
                  status: 'in_progress',
                  motivation: 'personal_growth',
                  target_date: '2026-06-01',
                },
              },
              {
                type: 'PERSON',
                properties: {
                  name: 'Michael',
                  relationship: 'self',
                  canonical_id: 'person_michael_001',
                  aliases: ['Michael', 'Mike', 'M'],
                },
              },
            ].map((example) => (
              <Box key={example.type} sx={{ p: 2.5, bgcolor: 'rgba(255,255,255,0.02)', borderRadius: '12px', border: '1px solid', borderColor: 'divider' }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 2, color: '#8B5CF6' }}>
                  {example.type}
                </Typography>
                <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 2 }}>
                  {Object.entries(example.properties).map(([key, value]) => (
                    <Box key={key}>
                      <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                        {key}
                      </Typography>
                      <Typography variant="body2" sx={{ fontWeight: 600, fontSize: '0.85rem', fontFamily: typeof value === 'number' ? 'monospace' : 'inherit' }}>
                        {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                      </Typography>
                    </Box>
                  ))}
                </Box>
              </Box>
            ))}
          </Box>
        </Paper>
      )}
    </Box>
  );
};
