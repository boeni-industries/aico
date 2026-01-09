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
import { X as CloseIcon, Save as SaveIcon, Trash2 as DeleteIcon, Plus as AddIcon, CheckCircle as CheckIcon, AlertCircle as ErrorIcon, AlertTriangle as WarningIcon } from 'lucide-react';
import { QueryTemplate } from '../../api/kg';
import { CodeEditor } from '../common/CodeEditor';

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
  }, [template, isNew]);


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
              <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600, color: 'rgba(255,255,255,0.9)' }}>
                Cypher Query
              </Typography>
              <CodeEditor
                value={formData.query}
                onChange={(value: string) => setFormData({ ...formData, query: value })}
                language="cypher"
                height={300}
                placeholder="Write your Cypher query here (MATCH, WHERE, RETURN, LIMIT)"
                schemaEndpoint="http://localhost:8771/api/v1/kg/schema"
              />
              {errors.query && (
                <Typography variant="caption" sx={{ color: '#f44336', mt: 0.5, display: 'block' }}>
                  {errors.query}
                </Typography>
              )}
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
