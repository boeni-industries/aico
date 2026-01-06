import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Button,
  Typography,
  Chip,
  Alert,
  IconButton,
  Collapse,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  CircularProgress,
  Fade,
  TablePagination,
  Select,
  MenuItem,
  FormControl,
  Tooltip,
  Snackbar,
} from '@mui/material';
import { Code as CodeIcon, Play as PlayIcon, Copy as CopyIcon, ChevronDown as ExpandIcon, Sparkles as SparkleIcon, TrendingUp as TrendingIcon, Clock as TimelineIcon, GitBranch as GraphIcon, Search as SearchIcon, CheckCircle as SuccessIcon, AlertCircle as ErrorIcon, Download as DownloadIcon, Plus as AddIcon, Pencil as EditIcon } from 'lucide-react';
import { executeGQLQuery, fetchQueryTemplates, updateQueryTemplates, QueryTemplate } from '../../api/kg';
import { TemplateEditor } from './TemplateEditor';
import { CodeEditor } from '../common/CodeEditor';

const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  exploration: <GraphIcon />,
  analysis: <TrendingIcon />,
  temporal: <TimelineIcon />,
  relationships: <SearchIcon />,
};

const INITIAL_TEMPLATES: QueryTemplate[] = [
  {
    id: 'all-nodes',
    title: 'All Nodes',
    description: 'Show all nodes with ALL their properties',
    category: 'exploration',
    query: `MATCH (n)
RETURN n.id as id, n.label as type, n.name as name, 
       n.confidence as confidence, n.source_text as source_text,
       n.created_at as created_at, n.updated_at as updated_at,
       n.valid_from as valid_from, n.valid_until as valid_until,
       n.is_current as is_current, n.canonical_id as canonical_id,
       n.language as language, n.reason as reason
LIMIT 100`,
    tags: ['basic', 'exploration', 'all'],
  },
  {
    id: 'all-edges',
    title: 'All Edges',
    description: 'Show all edges with ALL their properties',
    category: 'exploration',
    query: `MATCH (a)-[r]->(b)
RETURN r.id as id, a.name as from_node, r.relation_type as relation_type, b.name as to_node,
       r.confidence as confidence, r.source_text as source_text,
       r.created_at as created, r.updated_at as updated,
       r.valid_from as valid_from, r.valid_until as valid_until,
       r.is_current as current, r.reason as reason
LIMIT 100`,
    tags: ['basic', 'exploration', 'edges', 'relationships'],
  },
  {
    id: 'active-projects',
    title: 'Active Projects',
    description: 'Find all active projects and who is working on them',
    category: 'exploration',
    query: `MATCH (p:PERSON)-[:WORKING_ON]->(proj:PROJECT)
WHERE proj.status = "active"
RETURN p.name, proj.name, proj.progress
ORDER BY proj.progress DESC`,
    tags: ['projects', 'people', 'status'],
  },
  {
    id: 'skill-gaps',
    title: 'Skill Gaps Analysis',
    description: 'Identify skills needed but not yet acquired',
    category: 'analysis',
    query: `MATCH (goal:GOAL)-[:REQUIRES]->(skill:SKILL)
WHERE NOT EXISTS {
  MATCH (p:PERSON)-[:HAS_SKILL]->(skill)
}
RETURN goal.name, skill.name
ORDER BY goal.priority DESC`,
    tags: ['skills', 'goals', 'gaps'],
  },
  {
    id: 'recent-changes',
    title: 'Recent Changes',
    description: 'Show nodes created or updated in the last 7 days',
    category: 'temporal',
    query: `MATCH (n)
WHERE n.created_at > "2024-12-24"
   OR n.updated_at > "2024-12-24"
RETURN n.label, n.name, n.created_at, n.updated_at
ORDER BY n.updated_at DESC
LIMIT 20`,
    tags: ['temporal', 'recent', 'activity'],
  },
  {
    id: 'connection-strength',
    title: 'Strongest Connections',
    description: 'Find the most connected nodes in the graph',
    category: 'analysis',
    query: `MATCH (n)-[r]-(m)
RETURN n.label, n.name, COUNT(r) as connections
ORDER BY connections DESC
LIMIT 10`,
    tags: ['centrality', 'connections', 'importance'],
  },
  {
    id: 'goal-dependencies',
    title: 'Goal Dependencies',
    description: 'Map out goal hierarchies and dependencies',
    category: 'relationships',
    query: `MATCH path = (parent:GOAL)-[:DEPENDS_ON*1..3]->(child:GOAL)
RETURN parent.name, child.name, LENGTH(path) as depth
ORDER BY depth, parent.name`,
    tags: ['goals', 'dependencies', 'hierarchy'],
  },
  {
    id: 'temporal-evolution',
    title: 'Temporal Evolution',
    description: 'Track how entities changed over time',
    category: 'temporal',
    query: `MATCH (n)
WHERE n.valid_from IS NOT NULL
RETURN n.label, n.name, n.valid_from, n.valid_until, n.is_current
ORDER BY n.valid_from DESC
LIMIT 20`,
    tags: ['temporal', 'history', 'evolution'],
  },
  {
    id: 'multi-hop-paths',
    title: 'Multi-Hop Paths',
    description: 'Find paths between two entities (up to 3 hops)',
    category: 'relationships',
    query: `MATCH path = (start:PERSON {name: "Michael"})-[*1..3]-(end:GOAL)
RETURN start.name, end.name, LENGTH(path) as hops,
       [rel in relationships(path) | type(rel)] as path_types
ORDER BY hops
LIMIT 10`,
    tags: ['paths', 'traversal', 'connections'],
  },
  {
    id: 'property-aggregation',
    title: 'Property Aggregation',
    description: 'Aggregate statistics across node types',
    category: 'analysis',
    query: `MATCH (n)
RETURN n.label, 
       COUNT(n) as total,
       AVG(n.confidence) as avg_confidence,
       COUNT(CASE WHEN n.is_current = 1 THEN 1 END) as current_count
ORDER BY total DESC`,
    tags: ['aggregation', 'statistics', 'summary'],
  },
];

const CATEGORY_COLORS = {
  exploration: { bg: 'rgba(59, 130, 246, 0.1)', text: '#3B82F6', border: 'rgba(59, 130, 246, 0.3)' },
  analysis: { bg: 'rgba(139, 92, 246, 0.1)', text: '#8B5CF6', border: 'rgba(139, 92, 246, 0.3)' },
  temporal: { bg: 'rgba(236, 72, 153, 0.1)', text: '#EC4899', border: 'rgba(236, 72, 153, 0.3)' },
  relationships: { bg: 'rgba(16, 185, 129, 0.1)', text: '#10B981', border: 'rgba(16, 185, 129, 0.3)' },
};

export const GQLQueryInterface: React.FC = () => {
  const [query, setQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [expandedTemplate, setExpandedTemplate] = useState<string | null>(null);
  const [isExecuting, setIsExecuting] = useState(false);
  const [queryResult, setQueryResult] = useState<any>(null);
  const [queryError, setQueryError] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [templates, setTemplates] = useState<QueryTemplate[]>(INITIAL_TEMPLATES);
  const [editorOpen, setEditorOpen] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<QueryTemplate | null>(null);
  const [isNewTemplate, setIsNewTemplate] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Load query templates from API on mount
  const loadTemplates = async () => {
    try {
      console.log('[GQL Templates] Fetching templates from backend...');
      const response = await fetchQueryTemplates();
      console.log('[GQL Templates] Received response:', response);
      if (response.templates && response.templates.length > 0) {
        console.log(`[GQL Templates] Loaded ${response.templates.length} templates from backend`);
        setTemplates(response.templates);
      } else {
        console.log('[GQL Templates] No templates in response, using defaults');
      }
    } catch (error) {
      console.error('[GQL Templates] Failed to load query templates, using defaults:', error);
    }
  };

  useEffect(() => {
    loadTemplates();
  }, []);

  const handleChangePage = (event: unknown, newPage: number) => {
    console.log('[GQL Pagination] Changing page from', page, 'to', newPage, '| rowsPerPage:', rowsPerPage);
    // Prevent default behavior that might cause scrolling
    if (event && typeof event === 'object' && 'preventDefault' in event) {
      (event as Event).preventDefault();
    }
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const handleCreateTemplate = () => {
    setEditingTemplate(null);
    setIsNewTemplate(true);
    setEditorOpen(true);
  };

  const handleEditTemplate = (template: QueryTemplate) => {
    setEditingTemplate(template);
    setIsNewTemplate(false);
    setEditorOpen(true);
  };

  const handleSaveTemplate = async (template: QueryTemplate) => {
    try {
      setSaveError(null);
      
      // Update local state
      let updatedTemplates: QueryTemplate[];
      if (isNewTemplate) {
        // Check for duplicate ID
        if (templates.some(t => t.id === template.id)) {
          setSaveError(`Template with ID "${template.id}" already exists`);
          return;
        }
        updatedTemplates = [...templates, template];
      } else {
        updatedTemplates = templates.map(t => t.id === template.id ? template : t);
      }
      
      // Save to backend
      await updateQueryTemplates(updatedTemplates);
      
      // Update local state
      setTemplates(updatedTemplates);
      setSaveSuccess(true);
      setEditorOpen(false);
      
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (error) {
      console.error('[GQL Templates] Failed to save template:', error);
      setSaveError(error instanceof Error ? error.message : 'Failed to save template');
    }
  };

  const handleDeleteTemplate = async (templateId: string) => {
    try {
      setSaveError(null);
      
      const updatedTemplates = templates.filter(t => t.id !== templateId);
      
      // Save to backend
      await updateQueryTemplates(updatedTemplates);
      
      // Update local state
      setTemplates(updatedTemplates);
      setSaveSuccess(true);
      setEditorOpen(false);
      
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (error) {
      console.error('[GQL Templates] Failed to delete template:', error);
      setSaveError(error instanceof Error ? error.message : 'Failed to delete template');
    }
  };

  const handleExportCSV = () => {
    if (!queryResult?.data?.rows || !queryResult?.data?.columns) return;

    const { columns, rows } = queryResult.data;
    
    // Create CSV content with full untruncated data
    const csvRows = [
      columns.join(','), // Header
      ...rows.map((row: any[]) => 
        row.map(cell => {
          // Convert to string, handling objects and arrays
          let str: string;
          if (cell === null || cell === undefined) {
            str = '';
          } else if (typeof cell === 'object') {
            str = JSON.stringify(cell); // Full object/array as JSON
          } else {
            str = String(cell);
          }
          // Escape quotes and wrap in quotes if contains comma or newline
          return str.includes(',') || str.includes('\n') || str.includes('"')
            ? `"${str.replace(/"/g, '""')}"` 
            : str;
        }).join(',')
      )
    ];
    
    const csvContent = csvRows.join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `kg-query-results-${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const handleExportJSON = () => {
    if (!queryResult?.data) return;

    const jsonContent = JSON.stringify(queryResult.data, null, 2);
    const blob = new Blob([jsonContent], { type: 'application/json;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `kg-query-results-${new Date().toISOString().slice(0, 10)}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const handleTemplateClick = (template: QueryTemplate) => {
    setQuery(template.query);
    setExpandedTemplate(null);
  };

  const handleCopyQuery = (queryText: string) => {
    navigator.clipboard.writeText(queryText);
  };

  const handleExecuteQuery = async () => {
    if (!query.trim()) return;
    
    setIsExecuting(true);
    setQueryError(null);
    setQueryResult(null);
    setPage(0); // Reset to first page when executing new query
    
    try {
      const result = await executeGQLQuery(query);
      console.log('[GQL] Query result:', result);
      
      // Parse data if it's a JSON string
      if (result.data && typeof result.data === 'string') {
        try {
          result.data = JSON.parse(result.data);
          console.log('[GQL] Parsed data from JSON string');
        } catch (e) {
          console.error('[GQL] Failed to parse data as JSON:', e);
        }
      }
      
      console.log('[GQL] Result structure:', {
        hasData: !!result.data,
        hasRows: !!result.data?.rows,
        hasColumns: !!result.data?.columns,
        rowCount: result.data?.rows?.length,
        columnCount: result.data?.columns?.length
      });
      setQueryResult(result);
    } catch (error: any) {
      console.error('[GQL] Query execution failed:', error);
      console.error('[GQL] Error details:', {
        message: error.message,
        response: error.response,
        data: error.response?.data,
        status: error.response?.status
      });
      
      // Extract error message, handling both plain and encrypted responses
      let errorMessage = 'Failed to execute query';
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      } else if (error.response?.data?.encrypted) {
        errorMessage = 'Query syntax error (encrypted response - check backend logs for details)';
      } else if (error.message) {
        errorMessage = error.message;
      }
      
      setQueryError(errorMessage);
    } finally {
      setIsExecuting(false);
    }
  };

  const filteredTemplates = selectedCategory
    ? templates.filter((t: QueryTemplate) => t.category === selectedCategory)
    : templates;

  return (
    <Box>
      {/* Query Editor */}
      <Paper
        sx={{
          p: 3,
          mb: 3,
          borderRadius: '20px',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          background: 'linear-gradient(135deg, rgba(30, 27, 75, 0.4) 0%, rgba(15, 23, 42, 0.6) 100%)',
          backdropFilter: 'blur(20px)',
          boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.4)',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
          <CodeIcon size={28} color="#3B82F6" />
          <Box sx={{ flex: 1 }}>
            <Typography variant="h6" sx={{ fontWeight: 700, fontSize: '1.1rem', mb: 0.5 }}>
              GQL Query Editor
            </Typography>
            <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.75rem' }}>
              Execute graph queries using ISO standard GQL syntax via GrandCypher
            </Typography>
          </Box>
        </Box>

        <Box sx={{ mb: 2 }}>
          <CodeEditor
            value={query}
            onChange={setQuery}
            language="cypher"
            height={300}
            placeholder="Enter your Cypher/GQL query here..."
            schemaEndpoint="http://localhost:8771/api/v1/kg/schema"
          />
        </Box>

        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="contained"
            startIcon={isExecuting ? <CircularProgress size={20} sx={{ color: '#fff' }} /> : <PlayIcon />}
            disabled={!query.trim() || isExecuting}
            onClick={handleExecuteQuery}
            sx={{
              textTransform: 'none',
              fontWeight: 600,
              px: 3,
              py: 1,
              borderRadius: '10px',
              background: 'linear-gradient(135deg, #3B82F6 0%, #2563EB 100%)',
              boxShadow: '0 4px 14px 0 rgba(59, 130, 246, 0.4)',
              '&:hover': {
                background: 'linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)',
                boxShadow: '0 6px 20px 0 rgba(59, 130, 246, 0.6)',
              },
              '&:disabled': {
                background: 'rgba(255, 255, 255, 0.1)',
                color: 'rgba(255, 255, 255, 0.3)',
              },
            }}
          >
            {isExecuting ? 'Executing...' : 'Execute Query'}
          </Button>
          <Button
            variant="outlined"
            startIcon={<CopyIcon />}
            disabled={!query.trim()}
            onClick={() => handleCopyQuery(query)}
            sx={{
              textTransform: 'none',
              borderColor: 'rgba(255, 255, 255, 0.2)',
              color: 'rgba(255, 255, 255, 0.8)',
              '&:hover': {
                borderColor: 'rgba(255, 255, 255, 0.4)',
                bgcolor: 'rgba(255, 255, 255, 0.05)',
              },
            }}
          >
            Copy
          </Button>
        </Box>
      </Paper>

      {/* Query Results */}
      {queryError && (
        <Alert
          severity="error"
          icon={<ErrorIcon />}
          sx={{
            mb: 3,
            borderRadius: '12px',
            bgcolor: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            '& .MuiAlert-icon': {
              color: '#EF4444',
            },
          }}
        >
          <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5 }}>
            Query Execution Failed
          </Typography>
          <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.7)' }}>
            {queryError}
          </Typography>
        </Alert>
      )}

      {queryResult && (
        <Paper
          sx={{
            mb: 3,
            p: 3,
            borderRadius: '16px',
            border: '1px solid rgba(16, 185, 129, 0.3)',
            background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(0, 0, 0, 0.2) 100%)',
            backdropFilter: 'blur(10px)',
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2 }}>
            <SuccessIcon size={24} color="#10B981" />
            <Typography variant="h6" sx={{ fontWeight: 700, fontSize: '1rem' }}>
              Query Results
            </Typography>
            <Chip
              label={`${queryResult.data?.count || 0} rows`}
              size="small"
              sx={{
                bgcolor: 'rgba(16, 185, 129, 0.2)',
                color: '#10B981',
                fontWeight: 700,
                fontSize: '0.75rem',
              }}
            />
            <Box sx={{ ml: 'auto', display: 'flex', gap: 1.5, alignItems: 'center' }}>
              <FormControl size="small" sx={{ minWidth: 100 }}>
                <Select
                  value={rowsPerPage}
                  onChange={(e) => {
                    setRowsPerPage(Number(e.target.value));
                    setPage(0);
                  }}
                  sx={{
                    color: '#10B981',
                    fontSize: '0.875rem',
                    '& .MuiOutlinedInput-notchedOutline': {
                      borderColor: 'rgba(16, 185, 129, 0.3)',
                    },
                    '&:hover .MuiOutlinedInput-notchedOutline': {
                      borderColor: '#10B981',
                    },
                    '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
                      borderColor: '#10B981',
                    },
                  }}
                >
                  <MenuItem value={10}>10 per page</MenuItem>
                  <MenuItem value={25}>25 per page</MenuItem>
                  <MenuItem value={50}>50 per page</MenuItem>
                  <MenuItem value={100}>100 per page</MenuItem>
                </Select>
              </FormControl>
              <Button
                size="small"
                variant="outlined"
                startIcon={<DownloadIcon />}
                onClick={handleExportCSV}
                sx={{
                  textTransform: 'none',
                  borderColor: 'rgba(16, 185, 129, 0.3)',
                  color: '#10B981',
                  '&:hover': {
                    borderColor: '#10B981',
                    bgcolor: 'rgba(16, 185, 129, 0.1)',
                  },
                }}
              >
                CSV
              </Button>
              <Button
                size="small"
                variant="outlined"
                startIcon={<DownloadIcon />}
                onClick={handleExportJSON}
                sx={{
                  textTransform: 'none',
                  borderColor: 'rgba(16, 185, 129, 0.3)',
                  color: '#10B981',
                  '&:hover': {
                    borderColor: '#10B981',
                    bgcolor: 'rgba(16, 185, 129, 0.1)',
                  },
                }}
              >
                JSON
              </Button>
            </Box>
          </Box>

          <TableContainer
            sx={{
              borderRadius: '12px',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              bgcolor: 'rgba(0, 0, 0, 0.4)',
              overflowX: 'auto',
            }}
          >
            <Table size="small">
              <TableHead>
                <TableRow>
                  {(queryResult.data?.columns || []).map((col: string, idx: number) => (
                    <TableCell
                      key={idx}
                      sx={{
                        bgcolor: 'rgba(16, 185, 129, 0.2)',
                        color: '#10B981',
                        fontWeight: 700,
                        fontSize: '0.8rem',
                        borderBottom: '2px solid rgba(16, 185, 129, 0.3)',
                        padding: '6px 8px',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {col}
                    </TableCell>
                  ))}
                </TableRow>
              </TableHead>
              <TableBody>
                {(() => {
                  const allRows = queryResult.data?.rows || [];
                  const startIdx = page * rowsPerPage;
                  const endIdx = startIdx + rowsPerPage;
                  const paginatedRows = allRows.slice(startIdx, endIdx);
                  console.log('[GQL Pagination] Rendering:', {
                    totalRows: allRows.length,
                    page,
                    rowsPerPage,
                    startIdx,
                    endIdx,
                    paginatedCount: paginatedRows.length
                  });
                  return paginatedRows;
                })().map((row: any[], rowIdx: number) => (
                  <TableRow
                    key={rowIdx}
                    sx={{
                      '&:hover': {
                        bgcolor: 'rgba(255, 255, 255, 0.05)',
                      },
                    }}
                  >
                    {row.map((cell: any, cellIdx: number) => {
                      // Format cell value for display
                      let displayValue: React.ReactNode;
                      
                      if (cell === null || cell === undefined) {
                        displayValue = <span style={{ color: 'rgba(255, 255, 255, 0.4)', fontStyle: 'italic' }}>null</span>;
                      } else if (typeof cell === 'boolean') {
                        displayValue = <span style={{ color: cell ? '#10B981' : '#EF4444', fontWeight: 600 }}>{String(cell)}</span>;
                      } else if (typeof cell === 'number') {
                        displayValue = <span style={{ color: '#60A5FA' }}>{cell}</span>;
                      } else if (Array.isArray(cell)) {
                        // Arrays - show as comma-separated
                        displayValue = cell.length === 0 
                          ? <span style={{ color: 'rgba(255, 255, 255, 0.4)' }}>[ ]</span>
                          : cell.join(', ');
                      } else if (typeof cell === 'object') {
                        // Objects - show as key-value pairs
                        const entries = Object.entries(cell);
                        if (entries.length === 0) {
                          displayValue = <span style={{ color: 'rgba(255, 255, 255, 0.4)' }}>{'{ }'}</span>;
                        } else {
                          displayValue = (
                            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                              {entries.map(([key, value], idx) => (
                                <Box key={idx} sx={{ display: 'flex', gap: 1 }}>
                                  <Typography component="span" sx={{ color: '#10B981', fontSize: '0.875rem', fontWeight: 600 }}>
                                    {key}:
                                  </Typography>
                                  <Typography component="span" sx={{ color: 'rgba(255, 255, 255, 0.9)', fontSize: '0.875rem' }}>
                                    {value === null || value === undefined ? 'null' : String(value)}
                                  </Typography>
                                </Box>
                              ))}
                            </Box>
                          );
                        }
                      } else {
                        // Strings and everything else
                        displayValue = String(cell);
                      }
                      
                      // Get string representation for tooltip
                      const cellString = cell === null || cell === undefined ? 'null' : 
                        typeof cell === 'object' ? JSON.stringify(cell, null, 2) : String(cell);
                      const isLongContent = cellString.length > 100;
                      
                      return (
                        <Tooltip 
                          title={isLongContent ? cellString : ''} 
                          placement="top"
                          arrow
                          enterDelay={300}
                          sx={{
                            '& .MuiTooltip-tooltip': {
                              maxWidth: '600px',
                              fontSize: '0.75rem',
                              whiteSpace: 'pre-wrap',
                              wordBreak: 'break-word',
                            }
                          }}
                        >
                          <TableCell
                            key={cellIdx}
                            sx={{
                              color: 'rgba(255, 255, 255, 0.9)',
                              fontSize: '0.8rem',
                              borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
                              padding: '4px 8px',
                              verticalAlign: 'top',
                              maxHeight: '4.8rem',
                              maxWidth: '400px', // Allow horizontal space
                              minWidth: '80px',
                              overflow: 'hidden',
                              lineHeight: '1.2rem',
                              cursor: isLongContent ? 'help' : 'default',
                            }}
                          >
                            <Box sx={{
                              display: '-webkit-box',
                              WebkitLineClamp: 4,
                              WebkitBoxOrient: 'vertical',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              wordBreak: 'break-word',
                            }}>
                              {displayValue}
                            </Box>
                          </TableCell>
                        </Tooltip>
                      );
                    })}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
          
          <TablePagination
            component="div"
            count={queryResult.data?.rows?.length || 0}
            page={page}
            onPageChange={handleChangePage}
            rowsPerPage={rowsPerPage}
            onRowsPerPageChange={handleChangeRowsPerPage}
            rowsPerPageOptions={[10, 25, 50, 100]}
            sx={{
              borderTop: '1px solid rgba(255, 255, 255, 0.1)',
              color: 'rgba(255, 255, 255, 0.7)',
              '& .MuiTablePagination-select': {
                color: '#10B981',
              },
              '& .MuiTablePagination-selectIcon': {
                color: '#10B981',
              },
              '& .MuiTablePagination-displayedRows': {
                color: 'rgba(255, 255, 255, 0.7)',
              },
            }}
          />
        </Paper>
      )}

      {/* Query Templates */}
      <Box>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <SparkleIcon size={20} color="#F59E0B" />
            <Typography variant="h6" sx={{ fontWeight: 700, fontSize: '1.1rem' }}>
              Query Templates
            </Typography>
          </Box>
          <Button
            variant="contained"
            size="small"
            startIcon={<AddIcon />}
            onClick={handleCreateTemplate}
            sx={{
              bgcolor: '#EC4899',
              '&:hover': {
                bgcolor: '#DB2777',
              },
            }}
          >
            Create Template
          </Button>
        </Box>

        {/* Category Filters */}
        <Box sx={{ display: 'flex', gap: 1.5, mb: 3, flexWrap: 'wrap' }}>
          <Chip
            label="All"
            onClick={() => setSelectedCategory(null)}
            sx={{
              bgcolor: !selectedCategory ? 'rgba(255, 255, 255, 0.15)' : 'rgba(255, 255, 255, 0.05)',
              color: !selectedCategory ? '#fff' : 'rgba(255, 255, 255, 0.6)',
              fontWeight: !selectedCategory ? 700 : 500,
              borderRadius: '10px',
              px: 2,
              transition: 'all 0.2s',
              '&:hover': {
                bgcolor: 'rgba(255, 255, 255, 0.2)',
              },
            }}
          />
          {Object.entries(CATEGORY_COLORS).map(([category, colors]) => (
            <Chip
              key={category}
              label={category.charAt(0).toUpperCase() + category.slice(1)}
              onClick={() => setSelectedCategory(selectedCategory === category ? null : category)}
              sx={{
                bgcolor: selectedCategory === category ? colors.bg : 'rgba(255, 255, 255, 0.05)',
                color: selectedCategory === category ? colors.text : 'rgba(255, 255, 255, 0.6)',
                fontWeight: selectedCategory === category ? 700 : 500,
                borderRadius: '10px',
                px: 2,
                border: selectedCategory === category ? `1px solid ${colors.border}` : 'none',
                transition: 'all 0.2s',
                '&:hover': {
                  bgcolor: colors.bg,
                  color: colors.text,
                },
              }}
            />
          ))}
        </Box>

        {/* Template Grid */}
        <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: 2 }}>
          {filteredTemplates.map((template) => {
            const colors = CATEGORY_COLORS[template.category];
            const isExpanded = expandedTemplate === template.id;

            return (
              <Fade in key={template.id} timeout={300}>
                <Paper
                  sx={{
                    p: 2.5,
                    borderRadius: '16px',
                    border: `1px solid ${colors.border}`,
                    background: `linear-gradient(135deg, ${colors.bg} 0%, rgba(0, 0, 0, 0.2) 100%)`,
                    backdropFilter: 'blur(10px)',
                    cursor: 'pointer',
                    transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                    '&:hover': {
                      transform: 'translateY(-4px)',
                      boxShadow: `0 12px 24px 0 ${colors.bg}`,
                      borderColor: colors.text,
                    },
                  }}
                  onClick={() => handleTemplateClick(template)}
                >
                  <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1.5, mb: 1.5 }}>
                    <Box
                      sx={{
                        width: 48,
                        height: 48,
                        borderRadius: '12px',
                        bgcolor: colors.bg,
                        border: `1px solid ${colors.border}`,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}
                    >
                      {CATEGORY_ICONS[template.category]}
                    </Box>
                    <Box sx={{ flex: 1 }}>
                      <Typography variant="subtitle1" sx={{ fontWeight: 700, fontSize: '0.95rem', mb: 0.5 }}>
                        {template.title}
                      </Typography>
                      <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.75rem', lineHeight: 1.4 }}>
                        {template.description}
                      </Typography>
                    </Box>
                    <IconButton
                      size="small"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleEditTemplate(template);
                      }}
                      sx={{
                        color: 'rgba(255,255,255,0.5)',
                        '&:hover': {
                          color: '#3B82F6',
                          bgcolor: 'rgba(59, 130, 246, 0.1)',
                        },
                      }}
                    >
                      <EditIcon size={16} color="#3B82F6" />
                    </IconButton>
                    <IconButton
                      size="small"
                      onClick={(e) => {
                        e.stopPropagation();
                        setExpandedTemplate(isExpanded ? null : template.id);
                      }}
                      sx={{
                        color: 'rgba(255,255,255,0.5)',
                        transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
                        transition: 'transform 0.3s',
                      }}
                    >
                      <ExpandIcon size={16} color="#3B82F6" />
                    </IconButton>
                  </Box>

                  <Collapse in={isExpanded}>
                    <Box
                      sx={{
                        mt: 2,
                        p: 1.5,
                        bgcolor: 'rgba(0, 0, 0, 0.3)',
                        borderRadius: '8px',
                        border: '1px solid rgba(255, 255, 255, 0.1)',
                      }}
                    >
                      <Typography
                        variant="body2"
                        sx={{
                          fontFamily: '"Fira Code", monospace',
                          fontSize: '0.75rem',
                          color: 'rgba(255, 255, 255, 0.85)',
                          whiteSpace: 'pre-wrap',
                          lineHeight: 1.6,
                        }}
                      >
                        {template.query}
                      </Typography>
                    </Box>
                  </Collapse>

                  <Box sx={{ display: 'flex', gap: 0.75, mt: 1.5, flexWrap: 'wrap' }}>
                    {template.tags.map((tag) => (
                      <Chip
                        key={tag}
                        label={tag}
                        size="small"
                        sx={{
                          height: 22,
                          fontSize: '0.7rem',
                          bgcolor: 'rgba(255, 255, 255, 0.08)',
                          color: 'rgba(255, 255, 255, 0.6)',
                          borderRadius: '6px',
                          '& .MuiChip-label': {
                            px: 1,
                          },
                        }}
                      />
                    ))}
                  </Box>
                </Paper>
              </Fade>
            );
          })}
        </Box>
      </Box>

      {/* GQL Query Cheatsheet */}
      <Paper
        sx={{
          mt: 4,
          p: 4,
          borderRadius: '20px',
          border: '1px solid rgba(16, 185, 129, 0.2)',
          bgcolor: 'rgba(15, 23, 42, 0.6)',
          backdropFilter: 'blur(10px)',
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
          <CodeIcon size={19} color="#10B981" />
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 700, color: '#10B981', letterSpacing: '-0.02em' }}>
              GQL Query Cheatsheet
            </Typography>
            <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)' }}>
              Quick reference for graph query patterns
            </Typography>
          </Box>
        </Box>

        <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 3 }}>
          {/* Pattern Matching */}
          <Box sx={{ 
            p: 2.5, 
            borderRadius: '12px', 
            bgcolor: 'rgba(59, 130, 246, 0.08)',
            border: '1px solid rgba(59, 130, 246, 0.2)',
            transition: 'all 0.2s',
            '&:hover': {
              bgcolor: 'rgba(59, 130, 246, 0.12)',
              transform: 'translateY(-2px)',
              boxShadow: '0 4px 12px rgba(59, 130, 246, 0.2)',
            }
          }}>
            <Typography variant="subtitle2" sx={{ color: '#3B82F6', fontWeight: 700, mb: 1.5, display: 'flex', alignItems: 'center', gap: 1 }}>
              <GraphIcon size={19} color="#3B82F6" />
              Pattern Matching
            </Typography>
            <Box component="code" sx={{ 
              display: 'block', 
              p: 1.5, 
              bgcolor: 'rgba(0,0,0,0.3)', 
              borderRadius: '8px', 
              fontSize: '0.75rem',
              color: '#60A5FA',
              fontFamily: 'monospace',
              mb: 1,
            }}>
              MATCH (n:PERSON)<br/>
              MATCH (a)-[r:KNOWS]-{'>'}(b)
            </Box>
            <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.7rem' }}>
              Find nodes and relationships by type
            </Typography>
          </Box>

          {/* Filtering */}
          <Box sx={{ 
            p: 2.5, 
            borderRadius: '12px', 
            bgcolor: 'rgba(168, 85, 247, 0.08)',
            border: '1px solid rgba(168, 85, 247, 0.2)',
            transition: 'all 0.2s',
            '&:hover': {
              bgcolor: 'rgba(168, 85, 247, 0.12)',
              transform: 'translateY(-2px)',
              boxShadow: '0 4px 12px rgba(168, 85, 247, 0.2)',
            }
          }}>
            <Typography variant="subtitle2" sx={{ color: '#A855F7', fontWeight: 700, mb: 1.5, display: 'flex', alignItems: 'center', gap: 1 }}>
              <SparkleIcon size={19} color="#A855F7" />
              Filtering
            </Typography>
            <Box component="code" sx={{ 
              display: 'block', 
              p: 1.5, 
              bgcolor: 'rgba(0,0,0,0.3)', 
              borderRadius: '8px', 
              fontSize: '0.75rem',
              color: '#C084FC',
              fontFamily: 'monospace',
              mb: 1,
            }}>
              WHERE n.confidence {'>'}= 0.8<br/>
              WHERE n.name = 'Alice'
            </Box>
            <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.7rem' }}>
              Filter by properties and conditions
            </Typography>
          </Box>

          {/* Temporal */}
          <Box sx={{ 
            p: 2.5, 
            borderRadius: '12px', 
            bgcolor: 'rgba(236, 72, 153, 0.08)',
            border: '1px solid rgba(236, 72, 153, 0.2)',
            transition: 'all 0.2s',
            '&:hover': {
              bgcolor: 'rgba(236, 72, 153, 0.12)',
              transform: 'translateY(-2px)',
              boxShadow: '0 4px 12px rgba(236, 72, 153, 0.2)',
            }
          }}>
            <Typography variant="subtitle2" sx={{ color: '#EC4899', fontWeight: 700, mb: 1.5, display: 'flex', alignItems: 'center', gap: 1 }}>
              <TimelineIcon size={19} color="#EC4899" />
              Temporal
            </Typography>
            <Box component="code" sx={{ 
              display: 'block', 
              p: 1.5, 
              bgcolor: 'rgba(0,0,0,0.3)', 
              borderRadius: '8px', 
              fontSize: '0.75rem',
              color: '#F472B6',
              fontFamily: 'monospace',
              mb: 1,
            }}>
              WHERE n.is_current = 1<br/>
              WHERE n.created_at IS NOT NULL
            </Box>
            <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.7rem' }}>
              Query by time and version state
            </Typography>
          </Box>

          {/* Limiting */}
          <Box sx={{ 
            p: 2.5, 
            borderRadius: '12px', 
            bgcolor: 'rgba(16, 185, 129, 0.08)',
            border: '1px solid rgba(16, 185, 129, 0.2)',
            transition: 'all 0.2s',
            '&:hover': {
              bgcolor: 'rgba(16, 185, 129, 0.12)',
              transform: 'translateY(-2px)',
              boxShadow: '0 4px 12px rgba(16, 185, 129, 0.2)',
            }
          }}>
            <Typography variant="subtitle2" sx={{ color: '#10B981', fontWeight: 700, mb: 1.5, display: 'flex', alignItems: 'center', gap: 1 }}>
              <TrendingIcon size={19} color="#10B981" />
              Limiting Results
            </Typography>
            <Box component="code" sx={{ 
              display: 'block', 
              p: 1.5, 
              bgcolor: 'rgba(0,0,0,0.3)', 
              borderRadius: '8px', 
              fontSize: '0.75rem',
              color: '#34D399',
              fontFamily: 'monospace',
              mb: 1,
            }}>
              LIMIT 100<br/>
              SKIP 50 LIMIT 25
            </Box>
            <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.7rem' }}>
              Control result set size and pagination
            </Typography>
          </Box>

          {/* Label Matching */}
          <Box sx={{ 
            p: 2.5, 
            borderRadius: '12px', 
            bgcolor: 'rgba(251, 146, 60, 0.08)',
            border: '1px solid rgba(251, 146, 60, 0.2)',
            transition: 'all 0.2s',
            '&:hover': {
              bgcolor: 'rgba(251, 146, 60, 0.12)',
              transform: 'translateY(-2px)',
              boxShadow: '0 4px 12px rgba(251, 146, 60, 0.2)',
            }
          }}>
            <Typography variant="subtitle2" sx={{ color: '#FB923C', fontWeight: 700, mb: 1.5, display: 'flex', alignItems: 'center', gap: 1 }}>
              <SparkleIcon size={19} />
              Label Matching
            </Typography>
            <Box component="code" sx={{ 
              display: 'block', 
              p: 1.5, 
              bgcolor: 'rgba(0,0,0,0.3)', 
              borderRadius: '8px', 
              fontSize: '0.75rem',
              color: '#FDBA74',
              fontFamily: 'monospace',
              mb: 1,
            }}>
              MATCH (p:PERSON)<br/>
              MATCH (g:GOAL)
            </Box>
            <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.7rem' }}>
              Match nodes by their type labels
            </Typography>
          </Box>

          {/* Relationship Types */}
          <Box sx={{ 
            p: 2.5, 
            borderRadius: '12px', 
            bgcolor: 'rgba(34, 197, 94, 0.08)',
            border: '1px solid rgba(34, 197, 94, 0.2)',
            transition: 'all 0.2s',
            '&:hover': {
              bgcolor: 'rgba(34, 197, 94, 0.12)',
              transform: 'translateY(-2px)',
              boxShadow: '0 4px 12px rgba(34, 197, 94, 0.2)',
            }
          }}>
            <Typography variant="subtitle2" sx={{ color: '#22C55E', fontWeight: 700, mb: 1.5, display: 'flex', alignItems: 'center', gap: 1 }}>
              <SearchIcon size={19} />
              Relationship Types
            </Typography>
            <Box component="code" sx={{ 
              display: 'block', 
              p: 1.5, 
              bgcolor: 'rgba(0,0,0,0.3)', 
              borderRadius: '8px', 
              fontSize: '0.75rem',
              color: '#4ADE80',
              fontFamily: 'monospace',
              mb: 1,
            }}>
              WHERE r.relation_type = 'WORKING_ON'<br/>
              WHERE r.confidence {'>'}= 0.7
            </Box>
            <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.7rem' }}>
              Filter relationships by type and properties
            </Typography>
          </Box>
        </Box>
      </Paper>

      {/* Template Editor Dialog */}
      <TemplateEditor
        open={editorOpen}
        onClose={() => setEditorOpen(false)}
        template={editingTemplate}
        onSave={handleSaveTemplate}
        onDelete={handleDeleteTemplate}
        isNew={isNewTemplate}
      />

      {/* Success Notification */}
      <Snackbar
        open={saveSuccess}
        autoHideDuration={3000}
        onClose={() => setSaveSuccess(false)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert severity="success" sx={{ width: '100%' }}>
          Template saved successfully!
        </Alert>
      </Snackbar>

      {/* Error Notification */}
      <Snackbar
        open={!!saveError}
        autoHideDuration={5000}
        onClose={() => setSaveError(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert severity="error" sx={{ width: '100%' }}>
          {saveError}
        </Alert>
      </Snackbar>
    </Box>
  );
};
