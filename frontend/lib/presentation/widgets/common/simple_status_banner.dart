import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:aico_frontend/core/providers/networking_providers.dart';
import 'package:aico_frontend/presentation/providers/auth_provider.dart';
import 'package:aico_frontend/networking/services/connection_manager.dart';

/// Simplified status banner that works with actual ConnectionManager API
class SimpleStatusBanner extends ConsumerStatefulWidget {
  final Widget child;
  
  const SimpleStatusBanner({
    super.key,
    required this.child,
  });

  @override
  ConsumerState<SimpleStatusBanner> createState() => _SimpleStatusBannerState();
}

class _SimpleStatusBannerState extends ConsumerState<SimpleStatusBanner>
    with TickerProviderStateMixin {
  late AnimationController _slideController;
  late Animation<Offset> _slideAnimation;
  
  Timer? _hideTimer;
  bool _isVisible = false;
  ConnectionStatus _currentStatus = ConnectionStatus.connected;

  @override
  void initState() {
    super.initState();
    
    _slideController = AnimationController(
      duration: const Duration(milliseconds: 500),
      vsync: this,
    );
    
    _slideAnimation = Tween<Offset>(
      begin: const Offset(0, -1),
      end: Offset.zero,
    ).animate(CurvedAnimation(
      parent: _slideController,
      curve: Curves.elasticOut,
    ));
  }

  @override
  void dispose() {
    _slideController.dispose();
    _hideTimer?.cancel();
    super.dispose();
  }

  void _handleStatusChange(ConnectionStatus status) {
    if (status == _currentStatus) return;
    
    final wasConnected = _currentStatus == ConnectionStatus.connected;
    final isConnected = status == ConnectionStatus.connected;
    
    setState(() => _currentStatus = status);
    
    // Show banner for non-connected states or when reconnecting
    if (!isConnected || (!wasConnected && isConnected)) {
      _showBanner();
      
      // Auto-hide success messages
      if (isConnected) {
        _hideTimer?.cancel();
        _hideTimer = Timer(const Duration(seconds: 2), _hideBanner);
      }
    }
  }

  void _showBanner() {
    if (!_isVisible) {
      setState(() => _isVisible = true);
      _slideController.forward();
    }
  }

  void _hideBanner() {
    if (_isVisible) {
      _slideController.reverse().then((_) {
        if (mounted) {
          setState(() => _isVisible = false);
        }
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final connectionManager = ref.watch(connectionManagerProvider);
    final authState = ref.watch(authProvider);
    
    return StreamBuilder<ConnectionHealth>(
      stream: connectionManager.healthStream,
      initialData: connectionManager.health,
      builder: (context, snapshot) {
        final health = snapshot.data ?? connectionManager.health;
        final status = health.status;
        
        WidgetsBinding.instance.addPostFrameCallback((_) {
          _handleStatusChange(status);
        });
        
        return Column(
          children: [
            if (_isVisible)
              SlideTransition(
                position: _slideAnimation,
                child: _buildStatusBanner(context, status, authState),
              ),
            Expanded(child: widget.child),
          ],
        );
      },
    );
  }

  Widget _buildStatusBanner(BuildContext context, ConnectionStatus status, AuthState authState) {
    final theme = Theme.of(context);
    final statusInfo = _getStatusInfo(status, authState);
    
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            statusInfo.color,
            statusInfo.color.withOpacity(0.8),
          ],
          begin: Alignment.centerLeft,
          end: Alignment.centerRight,
        ),
        boxShadow: [
          BoxShadow(
            color: statusInfo.color.withOpacity(0.3),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: SafeArea(
        bottom: false,
        child: Row(
          children: [
            // Status indicator
            Icon(
              statusInfo.icon,
              color: Colors.white,
              size: 24,
            ),
            const SizedBox(width: 16),
            
            // Status content
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    statusInfo.title,
                    style: theme.textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w600,
                      color: Colors.white,
                    ),
                  ),
                  if (statusInfo.subtitle != null)
                    Text(
                      statusInfo.subtitle!,
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: Colors.white.withOpacity(0.9),
                      ),
                    ),
                ],
              ),
            ),
            
            // Dismiss button
            IconButton(
              onPressed: _hideBanner,
              icon: const Icon(Icons.close, size: 20),
              style: IconButton.styleFrom(
                foregroundColor: Colors.white,
                backgroundColor: Colors.white.withOpacity(0.2),
                minimumSize: const Size(36, 36),
              ),
            ),
          ],
        ),
      ),
    );
  }

  _StatusInfo _getStatusInfo(ConnectionStatus status, AuthState authState) {
    switch (status) {
      case ConnectionStatus.connected:
        return _StatusInfo(
          title: 'Connected',
          subtitle: authState.isAuthenticated ? 'Secure connection established' : 'Authentication required',
          icon: Icons.check_circle,
          color: Colors.green.shade600,
        );
        
      case ConnectionStatus.connecting:
        return _StatusInfo(
          title: 'Connecting',
          subtitle: 'Establishing secure connection...',
          icon: Icons.wifi_find,
          color: Colors.blue.shade600,
        );
        
      case ConnectionStatus.disconnected:
        return _StatusInfo(
          title: 'Disconnected',
          subtitle: 'Connection lost, attempting to reconnect...',
          icon: Icons.wifi_off,
          color: Colors.orange.shade600,
        );
        
      case ConnectionStatus.offline:
        return _StatusInfo(
          title: 'No Internet Connection',
          subtitle: 'Check your network settings',
          icon: Icons.wifi_off,
          color: Colors.red.shade600,
        );
        
      case ConnectionStatus.error:
        return _StatusInfo(
          title: 'Connection Error',
          subtitle: 'Unable to reach AICO servers',
          icon: Icons.error,
          color: Colors.red.shade600,
        );
    }
  }
}

class _StatusInfo {
  final String title;
  final String? subtitle;
  final IconData icon;
  final Color color;

  const _StatusInfo({
    required this.title,
    this.subtitle,
    required this.icon,
    required this.color,
  });
}
