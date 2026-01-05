import React, { useState } from 'react';
import { Box, Typography, Paper, TextField, Chip, InputAdornment, Accordion, AccordionSummary, AccordionDetails } from '@mui/material';
import { Search as SearchIcon, ChevronDown as ExpandIcon } from 'lucide-react';

interface PropertyInfo {
  key: string;
  count: number;
  valueTypes: string[];
  sampleValues: any[];
  entityTypes: string[];
}

interface PropertyBrowserProps {
  properties: PropertyInfo[];
  onPropertyClick?: (key: string) => void;
}

export const PropertyBrowser: React.FC<PropertyBrowserProps> = ({
  properties,
  onPropertyClick,
}) => {
  const [searchQuery, setSearchQuery] = useState('');

  const filteredProperties = properties.filter((prop) =>
    prop.key.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      string: '#3B82F6',
      number: '#10B981',
      boolean: '#F59E0B',
      object: '#8B5CF6',
      array: '#EC4899',
    };
    return colors[type] || '#94A3B8';
  };

  return (
    <Box>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
          Property Index Browser
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Explore all {properties.length} unique properties across 1,084 nodes
        </Typography>

        {/* Search */}
        <TextField
          fullWidth
          placeholder="Search properties..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          size="small"
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon sx={{ color: 'text.secondary' }} />
              </InputAdornment>
            ),
          }}
          sx={{
            '& .MuiOutlinedInput-root': {
              borderRadius: '12px',
            },
          }}
        />
      </Box>

      {/* Stats */}
      <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 2, mb: 3 }}>
        <Paper sx={{ p: 2, borderRadius: '12px', bgcolor: 'rgba(139, 92, 246, 0.08)' }}>
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
            TOTAL PROPERTIES
          </Typography>
          <Typography variant="h5" sx={{ fontWeight: 700, color: '#8B5CF6' }}>
            {properties.length}
          </Typography>
        </Paper>
        <Paper sx={{ p: 2, borderRadius: '12px', bgcolor: 'rgba(59, 130, 246, 0.08)' }}>
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
            FILTERED
          </Typography>
          <Typography variant="h5" sx={{ fontWeight: 700, color: '#3B82F6' }}>
            {filteredProperties.length}
          </Typography>
        </Paper>
        <Paper sx={{ p: 2, borderRadius: '12px', bgcolor: 'rgba(16, 185, 129, 0.08)' }}>
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
            AVG PER NODE
          </Typography>
          <Typography variant="h5" sx={{ fontWeight: 700, color: '#10B981' }}>
            2.25
          </Typography>
        </Paper>
      </Box>

      {/* Property List */}
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
        {filteredProperties.map((prop) => (
          <Accordion
            key={prop.key}
            sx={{
              borderRadius: '12px !important',
              border: '1px solid',
              borderColor: 'divider',
              '&:before': { display: 'none' },
              '&.Mui-expanded': {
                margin: '0 !important',
              },
            }}
          >
            <AccordionSummary
              expandIcon={<ExpandIcon />}
              sx={{
                '&.Mui-expanded': {
                  minHeight: 48,
                },
                '& .MuiAccordionSummary-content': {
                  margin: '12px 0',
                  '&.Mui-expanded': {
                    margin: '12px 0',
                  },
                },
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%', pr: 2 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                  <Typography
                    variant="body2"
                    sx={{
                      fontWeight: 600,
                      fontSize: '0.9rem',
                      fontFamily: 'monospace',
                    }}
                  >
                    {prop.key}
                  </Typography>
                  <Chip
                    label={`${prop.count} nodes`}
                    size="small"
                    sx={{
                      height: 20,
                      fontSize: '0.65rem',
                      bgcolor: 'rgba(139, 92, 246, 0.12)',
                      color: '#8B5CF6',
                    }}
                  />
                </Box>
                <Box sx={{ display: 'flex', gap: 0.5 }}>
                  {prop.valueTypes.map((type) => (
                    <Chip
                      key={type}
                      label={type}
                      size="small"
                      sx={{
                        height: 18,
                        fontSize: '0.6rem',
                        bgcolor: `${getTypeColor(type)}15`,
                        color: getTypeColor(type),
                        fontWeight: 600,
                      }}
                    />
                  ))}
                </Box>
              </Box>
            </AccordionSummary>
            <AccordionDetails>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {/* Entity Types */}
                <Box>
                  <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', mb: 1, display: 'block' }}>
                    USED BY ENTITY TYPES
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 0.75, flexWrap: 'wrap' }}>
                    {prop.entityTypes.map((type) => (
                      <Chip
                        key={type}
                        label={type}
                        size="small"
                        sx={{
                          height: 20,
                          fontSize: '0.65rem',
                          bgcolor: 'rgba(59, 130, 246, 0.12)',
                          color: '#3B82F6',
                        }}
                      />
                    ))}
                  </Box>
                </Box>

                {/* Sample Values */}
                <Box>
                  <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', mb: 1, display: 'block' }}>
                    SAMPLE VALUES
                  </Typography>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                    {prop.sampleValues.slice(0, 3).map((value, i) => (
                      <Paper
                        key={i}
                        sx={{
                          p: 1.5,
                          bgcolor: 'rgba(255,255,255,0.02)',
                          borderRadius: '8px',
                        }}
                      >
                        <Typography
                          variant="body2"
                          sx={{
                            fontSize: '0.8rem',
                            fontFamily: typeof value === 'number' ? 'monospace' : 'inherit',
                            wordBreak: 'break-word',
                          }}
                        >
                          {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                        </Typography>
                      </Paper>
                    ))}
                  </Box>
                </Box>
              </Box>
            </AccordionDetails>
          </Accordion>
        ))}
      </Box>

      {filteredProperties.length === 0 && (
        <Paper sx={{ p: 3, textAlign: 'center', borderRadius: '12px' }}>
          <Typography variant="body2" color="text.secondary">
            No properties match your search
          </Typography>
        </Paper>
      )}
    </Box>
  );
};
