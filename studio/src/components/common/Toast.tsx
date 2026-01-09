import React, { createContext, useContext, useState, useCallback } from 'react';
import { Box, IconButton, AlertColor, Slide } from '@mui/material';
import { CheckCircle2, XCircle, AlertTriangle, Info, X } from 'lucide-react';

interface ToastMessage {
  id: number;
  message: string;
  severity: AlertColor;
  duration?: number;
}

interface ToastContextType {
  showToast: (message: string, severity?: AlertColor, duration?: number) => void;
  showSuccess: (message: string) => void;
  showError: (message: string) => void;
  showWarning: (message: string) => void;
  showInfo: (message: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within ToastProvider');
  }
  return context;
};

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const [nextId, setNextId] = useState(0);

  const showToast = useCallback((message: string, severity: AlertColor = 'info', duration: number = 4000) => {
    const id = nextId;
    setNextId(prev => prev + 1);
    setToasts(prev => [...prev, { id, message, severity, duration }]);
    
    // Auto-dismiss after duration
    setTimeout(() => {
      setToasts(prev => prev.filter(toast => toast.id !== id));
    }, duration);
  }, [nextId]);

  const showSuccess = useCallback((message: string) => showToast(message, 'success'), [showToast]);
  const showError = useCallback((message: string) => showToast(message, 'error', 6000), [showToast]);
  const showWarning = useCallback((message: string) => showToast(message, 'warning'), [showToast]);
  const showInfo = useCallback((message: string) => showToast(message, 'info'), [showToast]);

  const handleClose = useCallback((id: number) => {
    setToasts(prev => prev.filter(toast => toast.id !== id));
  }, []);

  const getIcon = (severity: AlertColor) => {
    const iconProps = { size: 20, strokeWidth: 2.5 };
    switch (severity) {
      case 'success': return <CheckCircle2 {...iconProps} />;
      case 'error': return <XCircle {...iconProps} />;
      case 'warning': return <AlertTriangle {...iconProps} />;
      case 'info': return <Info {...iconProps} />;
      default: return <Info {...iconProps} />;
    }
  };

  const getColors = (severity: AlertColor) => {
    switch (severity) {
      case 'success': return { bg: 'rgba(16, 185, 129, 0.12)', border: '#10b981', icon: '#10b981', text: '#d1fae5' };
      case 'error': return { bg: 'rgba(239, 68, 68, 0.12)', border: '#ef4444', icon: '#ef4444', text: '#fee2e2' };
      case 'warning': return { bg: 'rgba(245, 158, 11, 0.12)', border: '#f59e0b', icon: '#f59e0b', text: '#fef3c7' };
      case 'info': return { bg: 'rgba(59, 130, 246, 0.12)', border: '#3b82f6', icon: '#3b82f6', text: '#dbeafe' };
      default: return { bg: 'rgba(59, 130, 246, 0.12)', border: '#3b82f6', icon: '#3b82f6', text: '#dbeafe' };
    }
  };

  return (
    <ToastContext.Provider value={{ showToast, showSuccess, showError, showWarning, showInfo }}>
      {children}
      <Box
        sx={{
          position: 'fixed',
          top: 24,
          right: 24,
          zIndex: 9999,
          display: 'flex',
          flexDirection: 'column',
          gap: 1.5,
          maxWidth: 420,
          pointerEvents: 'none',
        }}
      >
        {toasts.map((toast) => {
          const colors = getColors(toast.severity);
          return (
            <Slide key={toast.id} direction="left" in={true} timeout={300}>
              <Box
                sx={{
                  pointerEvents: 'auto',
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: 1.5,
                  p: 2,
                  pr: 1.5,
                  backgroundColor: colors.bg,
                  backdropFilter: 'blur(12px)',
                  border: `1px solid ${colors.border}`,
                  borderRadius: 2,
                  boxShadow: '0 8px 32px rgba(0, 0, 0, 0.12), 0 2px 8px rgba(0, 0, 0, 0.08)',
                  transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
                  '&:hover': {
                    boxShadow: '0 12px 48px rgba(0, 0, 0, 0.16), 0 4px 12px rgba(0, 0, 0, 0.12)',
                    transform: 'translateY(-2px)',
                  },
                }}
              >
                <Box sx={{ color: colors.icon, display: 'flex', mt: 0.25 }}>
                  {getIcon(toast.severity)}
                </Box>
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Box
                    sx={{
                      color: colors.text,
                      fontSize: '0.9375rem',
                      fontWeight: 500,
                      lineHeight: 1.5,
                      letterSpacing: '-0.01em',
                    }}
                  >
                    {toast.message}
                  </Box>
                </Box>
                <IconButton
                  size="small"
                  onClick={() => handleClose(toast.id)}
                  sx={{
                    color: colors.text,
                    opacity: 0.6,
                    p: 0.5,
                    '&:hover': {
                      opacity: 1,
                      backgroundColor: 'rgba(255, 255, 255, 0.08)',
                    },
                  }}
                >
                  <X size={16} strokeWidth={2} />
                </IconButton>
              </Box>
            </Slide>
          );
        })}
      </Box>
    </ToastContext.Provider>
  );
};
