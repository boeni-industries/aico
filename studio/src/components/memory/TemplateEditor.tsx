import React, { useState, useEffect, useCallback } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Box,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  IconButton,
  Alert,
  Snackbar,
  Fade,
  CircularProgress,
} from '@mui/material';
import {
  Close as CloseIcon,
  Save as SaveIcon,
  Delete as DeleteIcon,
  Add as AddIcon,
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
} from '@mui/icons-material';
import { QueryTemplate } from '../../api/kg';

interface TemplateEditorProps {
  open: boolean;
  onClose: () => void;
  template: QueryTemplate | null;
  onSave: (template: QueryTemplate) => void;
  onDelete?: (templateId: string) => void;
  isNew?: boolean;
}

const CATEGORIES = ['exploration', 'analysis', 'temporal', 'relationships'] as const;

export const TemplateEditor: React.FC<TemplateEditorProps> = ({
  open,
  onClose,
  template,
  onSave,
  onDelete,
  isNew = false,
}) => {
  const [formData, setFormData] = useState<QueryTemplate>(
    template || {
      id: '',
      title: '',
      description: '',
      category: 'exploration',
      query: '',
      tags: [],
    }
  );
  const [newTag, setNewTag] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [showSuccess, setShowSuccess] = useState(false);
  const [queryValidation, setQueryValidation] = useState<{
    status: 'idle' | 'validating' | 'valid' | 'warning' | 'error';
    message?: string;
  }>({ status: 'idle' });

  React.useEffect(() => {
    if (template) {
      setFormData(template);
    } else if (isNew) {
      setFormData({
        id: '',
        title: '',
        description: '',
        category: 'exploration',
        query: '',
        tags: [],
      });
    }
    setQueryValidation({ status: 'idle' });
  }, [template, isNew]);

  const validateCypherQuery = useCallback((query: string) => {
    if (!query.trim()) {
      return { status: 'idle' as const };
    }

    const trimmedQuery = query.trim().toUpperCase();
    
    const typoPatterns = [
      { pattern: /\bLIMI\b/, message: 'Did you mean LIMIT?' },
      { pattern: /\bRETUR\b/, message: 'Did you mean RETURN?' },
      { pattern: /\bMATH\b/, message: 'Did you mean MATCH?' },
      { pattern: /\bWHER\b/, message: 'Did you mean WHERE?' },
    ];
    
    for (const typo of typoPatterns) {
      if (typo.pattern.test(trimmedQuery)) {
        return { status: 'error' as const, message: typo.message };
      }
    }
    
    const hasMatch = /\bMATCH\b/.test(trimmedQuery);
    const hasReturn = /\bRETURN\b/.test(trimmedQuery);
    const openParens = (query.match(/\(/g) || []).length;
    const closeParens = (query.match(/\)/g) || []).length;
    
    if (openParens !== closeParens) {
      return { status: 'error' as const, message: 'Unbalanced parentheses' };
    }
    
    if (!hasMatch && !hasReturn) {
      return { status: 'warning' as const, message: 'Query should contain MATCH and RETURN' };
    }
    
    return { status: 'valid' as const, message: 'Query syntax looks good' };
  }, []);

  useEffect(() => {
    if (!formData.query.trim()) {
      setQueryValidation({ status: 'idle' });
      return;
    }
    setQueryValidation({ status: 'validating' });
    const timer = setTimeout(() => {
      setQueryValidation(validateCypherQuery(formData.query));
    }, 500);
    return () => clearTimeout(timer);
  }, [formData.query, validateCypherQuery]);

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};
    if (!formData.id.trim()) newErrors.id = 'ID is required';
    else if (!/^[a-z0-9-]+$/.test(formData.id)) newErrors.id = 'ID must be lowercase letters, numbers, and hyphens';
    if (!formData.title.trim()) newErrors.title = 'Title is required';
    if (!formData.description.trim()) newErrors.description = 'Description is required';
    if (!formData.query.trim()) newErrors.query = 'Query is required';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSave = () => {
    if (validateForm()) {
      onSave(formData);
      setShowSuccess(true);
      setTimeout(() => onClose(), 1000);
    }
  };

  const handleAddTag = () => {
    if (newTag.trim() && !formData.tags.includes(newTag.trim())) {
      setFormData({ ...formData, tags: [...formData.tags, newTag.trim()] });
      setNewTag('');
    }
  };

  const handleDeleteTag = (tagToDelete: string) => {
    setFormData({ ...formData, tags: formData.tags.filter((tag) => tag !== tagToDelete) });
  };

  const handleDelete = () => {
    if (onDelete && formData.id) {
      if (window.confirm(`Delete template "${formData.title}"?`)) {
        onDelete(formData.id);
        onClose();
      }
    }
  };

  return (
    <>
      <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth scroll="paper"
        PaperProps={{ sx: { background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.85) 0%, rgba(30, 41, 59, 0.85) 100%)', backdropFilter: 'blur(20px) saturate(180%)', borderRadius: '36px', border: '1.5px solid rgba(255, 255, 255, 0.16)', height: '90vh', display: 'flex', flexDirection: 'column', boxShadow: '0 20px 40px rgba(0,0,0,0.28)' } }}>
        <DialogTitle sx={{ pb: 2.5, pt: 3, px: 4, flexShrink: 0, borderBottom: '1px solid rgba(255, 255, 255, 0.08)' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Box>
              <Typography variant="h5" sx={{ fontWeight: 700, fontSize: '1.5rem' }}>
                {isNew ? 'Create New Template' : 'Edit Template'}
              </Typography>
              <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)' }}>
                {isNew ? 'Define a new GQL query template' : 'Modify template configuration'}
              </Typography>
            </Box>
            <IconButton onClick={onClose} size="small" sx={{ color: 'rgba(255,255,255,0.5)' }}>
              <CloseIcon />
            </IconButton>
          </Box>
        </DialogTitle>

        <DialogContent sx={{ pt: 4, px: 4, pb: 3, overflow: 'auto', flex: 1 }}>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            <TextField label="Template ID" value={formData.id} onChange={(e) => setFormData({ ...formData, id: e.target.value })} disabled={!isNew} error={!!errors.id} helperText={errors.id || 'Unique identifier (lowercase, hyphens allowed)'} fullWidth
              sx={{ mt: 2.25, '& .MuiOutlinedInput-root': { bgcolor: 'rgba(255, 255, 255, 0.03)', backdropFilter: 'blur(10px)', borderRadius: '20px', '& fieldset': { borderColor: 'rgba(255, 255, 255, 0.1)' }, '&:hover': { bgcolor: 'rgba(255, 255, 255, 0.05)' }, '&:hover fieldset': { borderColor: 'rgba(184, 161, 234, 0.3)' }, '&.Mui-focused': { bgcolor: 'rgba(255, 255, 255, 0.08)' }, '&.Mui-focused fieldset': { borderColor: '#B8A1EA', borderWidth: '2px', boxShadow: '0 0 0 3px rgba(184, 161, 234, 0.1)' } }, '& .MuiInputLabel-root.Mui-focused': { color: '#B8A1EA' } }} />
            
            <TextField label="Title" value={formData.title} onChange={(e) => setFormData({ ...formData, title: e.target.value })} error={!!errors.title} helperText={errors.title || 'Display name for the template'} fullWidth
              sx={{ '& .MuiOutlinedInput-root': { bgcolor: 'rgba(255, 255, 255, 0.03)', backdropFilter: 'blur(10px)', borderRadius: '20px', '& fieldset': { borderColor: 'rgba(255, 255, 255, 0.1)' }, '&:hover': { bgcolor: 'rgba(255, 255, 255, 0.05)' }, '&:hover fieldset': { borderColor: 'rgba(184, 161, 234, 0.3)' }, '&.Mui-focused': { bgcolor: 'rgba(255, 255, 255, 0.08)' }, '&.Mui-focused fieldset': { borderColor: '#B8A1EA', borderWidth: '2px', boxShadow: '0 0 0 3px rgba(184, 161, 234, 0.1)' } }, '& .MuiInputLabel-root.Mui-focused': { color: '#B8A1EA' } }} />
            
            <TextField label="Description" value={formData.description} onChange={(e) => setFormData({ ...formData, description: e.target.value })} error={!!errors.description} helperText={errors.description || 'Brief description of what this query does'} fullWidth multiline rows={2}
              sx={{ '& .MuiOutlinedInput-root': { bgcolor: 'rgba(255, 255, 255, 0.03)', backdropFilter: 'blur(10px)', borderRadius: '20px', '& fieldset': { borderColor: 'rgba(255, 255, 255, 0.1)' }, '&:hover': { bgcolor: 'rgba(255, 255, 255, 0.05)' }, '&:hover fieldset': { borderColor: 'rgba(184, 161, 234, 0.3)' }, '&.Mui-focused': { bgcolor: 'rgba(255, 255, 255, 0.08)' }, '&.Mui-focused fieldset': { borderColor: '#B8A1EA', borderWidth: '2px', boxShadow: '0 0 0 3px rgba(184, 161, 234, 0.1)' } }, '& .MuiInputLabel-root.Mui-focused': { color: '#B8A1EA' } }} />
            
            <FormControl fullWidth>
              <InputLabel>Category</InputLabel>
              <Select value={formData.category} onChange={(e) => setFormData({ ...formData, category: e.target.value as typeof CATEGORIES[number] })} label="Category"
                sx={{ bgcolor: 'rgba(255, 255, 255, 0.03)', backdropFilter: 'blur(10px)', borderRadius: '20px', '& fieldset': { borderColor: 'rgba(255, 255, 255, 0.1)' }, '&:hover': { bgcolor: 'rgba(255, 255, 255, 0.05)' }, '&:hover fieldset': { borderColor: 'rgba(184, 161, 234, 0.3)' }, '&.Mui-focused': { bgcolor: 'rgba(255, 255, 255, 0.08)' }, '&.Mui-focused fieldset': { borderColor: '#B8A1EA', borderWidth: '2px', boxShadow: '0 0 0 3px rgba(184, 161, 234, 0.1)' } }}>
                {CATEGORIES.map((cat) => <MenuItem key={cat} value={cat}>{cat.charAt(0).toUpperCase() + cat.slice(1)}</MenuItem>)}
              </Select>
            </FormControl>

            <Box>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1.5 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 600, color: 'rgba(255,255,255,0.9)' }}>Cypher Query</Typography>
                <Fade in={queryValidation.status !== 'idle'} timeout={300}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, px: 1.5, py: 0.5, borderRadius: '8px', backdropFilter: 'blur(10px)', 
                    ...(queryValidation.status === 'validating' && { bgcolor: 'rgba(139, 92, 246, 0.15)', border: '1px solid rgba(139, 92, 246, 0.3)' }),
                    ...(queryValidation.status === 'valid' && { bgcolor: 'rgba(16, 185, 129, 0.15)', border: '1px solid rgba(16, 185, 129, 0.3)' }),
                    ...(queryValidation.status === 'warning' && { bgcolor: 'rgba(251, 191, 36, 0.15)', border: '1px solid rgba(251, 191, 36, 0.3)' }),
                    ...(queryValidation.status === 'error' && { bgcolor: 'rgba(239, 68, 68, 0.15)', border: '1px solid rgba(239, 68, 68, 0.3)' }) }}>
                    {queryValidation.status === 'validating' && <CircularProgress size={14} sx={{ color: '#8B5CF6' }} />}
                    {queryValidation.status === 'valid' && <CheckIcon sx={{ fontSize: 16, color: '#10B981' }} />}
                    {queryValidation.status === 'warning' && <WarningIcon sx={{ fontSize: 16, color: '#FBBF24' }} />}
                    {queryValidation.status === 'error' && <ErrorIcon sx={{ fontSize: 16, color: '#EF4444' }} />}
                    <Typography variant="caption" sx={{ fontSize: '0.75rem', fontWeight: 600,
                      ...(queryValidation.status === 'validating' && { color: '#8B5CF6' }),
                      ...(queryValidation.status === 'valid' && { color: '#10B981' }),
                      ...(queryValidation.status === 'warning' && { color: '#FBBF24' }),
                      ...(queryValidation.status === 'error' && { color: '#EF4444' }) }}>
                      {queryValidation.message || 'Validating...'}
                    </Typography>
                  </Box>
                </Fade>
              </Box>
              <TextField value={formData.query} onChange={(e) => setFormData({ ...formData, query: e.target.value })} error={!!errors.query || queryValidation.status === 'error'} helperText={errors.query || 'Write your Cypher query here (MATCH, WHERE, RETURN, LIMIT)'} fullWidth multiline rows={10}
                sx={{ '& textarea': { fontFamily: '"Fira Code", monospace', fontSize: '0.875rem', lineHeight: 1.6 }, '& .MuiOutlinedInput-root': { bgcolor: 'rgba(255, 255, 255, 0.03)', backdropFilter: 'blur(10px)', borderRadius: '20px', '& fieldset': { borderColor: 'rgba(255, 255, 255, 0.1)' }, '&:hover': { bgcolor: 'rgba(255, 255, 255, 0.05)' }, '&:hover fieldset': { borderColor: 'rgba(184, 161, 234, 0.3)' },
                  '&.Mui-focused': { bgcolor: 'rgba(255, 255, 255, 0.08)' },
                  ...(queryValidation.status === 'valid' && { '&.Mui-focused fieldset': { borderColor: '#10B981', borderWidth: '2px', boxShadow: '0 0 0 3px rgba(16, 185, 129, 0.1)' } }),
                  ...(queryValidation.status === 'warning' && { '&.Mui-focused fieldset': { borderColor: '#F59E0B', borderWidth: '2px', boxShadow: '0 0 0 3px rgba(245, 158, 11, 0.1)' } }),
                  ...(queryValidation.status === 'error' && { '&.Mui-focused fieldset': { borderColor: '#ED7867', borderWidth: '2px', boxShadow: '0 0 0 3px rgba(237, 120, 103, 0.1)' } }),
                  ...(!queryValidation.status || queryValidation.status === 'idle' || queryValidation.status === 'validating' ? { '&.Mui-focused fieldset': { borderColor: '#B8A1EA', borderWidth: '2px', boxShadow: '0 0 0 3px rgba(184, 161, 234, 0.1)' } } : {}) } }} />
            </Box>

            <Box>
              <Typography variant="subtitle2" sx={{ mb: 1.5, fontWeight: 600, color: 'rgba(255,255,255,0.9)' }}>Tags</Typography>
              <Box sx={{ display: 'flex', gap: 1, mb: 1.5, flexWrap: 'wrap' }}>
                {formData.tags.map((tag) => <Chip key={tag} label={tag} onDelete={() => handleDeleteTag(tag)} size="small" sx={{ bgcolor: 'rgba(236, 72, 153, 0.2)', color: '#EC4899' }} />)}
              </Box>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <TextField size="small" placeholder="Add tag..." value={newTag} onChange={(e) => setNewTag(e.target.value)} onKeyPress={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleAddTag(); } }}
                  sx={{ flex: 1, '& .MuiOutlinedInput-root': { bgcolor: 'rgba(255, 255, 255, 0.03)', backdropFilter: 'blur(10px)', borderRadius: '12px', '& fieldset': { borderColor: 'rgba(255, 255, 255, 0.1)' }, '&:hover': { bgcolor: 'rgba(255, 255, 255, 0.05)' }, '&:hover fieldset': { borderColor: 'rgba(184, 161, 234, 0.3)' }, '&.Mui-focused': { bgcolor: 'rgba(255, 255, 255, 0.08)' }, '&.Mui-focused fieldset': { borderColor: '#B8A1EA', borderWidth: '2px' } } }} />
                <Button variant="outlined" size="small" onClick={handleAddTag} startIcon={<AddIcon />} disabled={!newTag.trim()}>Add</Button>
              </Box>
            </Box>
          </Box>
        </DialogContent>

        <DialogActions sx={{ borderTop: '1px solid rgba(255, 255, 255, 0.08)', p: 3, px: 4, justifyContent: 'space-between', background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.95) 100%)', backdropFilter: 'blur(10px)', flexShrink: 0 }}>
          <Box>
            {!isNew && onDelete && <Button onClick={handleDelete} startIcon={<DeleteIcon />} color="error" variant="outlined">Delete</Button>}
          </Box>
          <Box sx={{ display: 'flex', gap: 1.5 }}>
            <Button onClick={onClose} variant="outlined" sx={{ borderColor: 'rgba(255, 255, 255, 0.2)', color: 'rgba(255, 255, 255, 0.7)' }}>Cancel</Button>
            <Button onClick={handleSave} variant="contained" startIcon={<SaveIcon />} sx={{ bgcolor: '#B8A1EA', color: '#1A1D27', fontWeight: 600, '&:hover': { bgcolor: '#A890E0', boxShadow: '0 0 20px rgba(184, 161, 234, 0.4)' }, px: 3, borderRadius: '20px', boxShadow: '0 4px 12px rgba(184, 161, 234, 0.3)' }}>
              {isNew ? 'Create Template' : 'Save Changes'}
            </Button>
          </Box>
        </DialogActions>
      </Dialog>

      <Snackbar open={showSuccess} autoHideDuration={3000} onClose={() => setShowSuccess(false)} anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
        <Alert severity="success">Template {isNew ? 'created' : 'updated'} successfully!</Alert>
      </Snackbar>
    </>
  );
};
