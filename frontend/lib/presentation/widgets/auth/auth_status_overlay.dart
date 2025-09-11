import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:aico_frontend/core/providers/networking_providers.dart';
import 'package:aico_frontend/presentation/providers/auth_provider.dart';
import 'package:aico_frontend/networking/services/token_manager.dart';

/// Award-winning authentication status overlay with premium animations
class AuthStatusOverlay extends ConsumerStatefulWidget {
  final Widget child;
  
  const AuthStatusOverlay({
    super.key,
    required this.child,
  });

  @override
  ConsumerState<AuthStatusOverlay> createState() => _AuthStatusOverlayState();
}

class _AuthStatusOverlayState extends ConsumerState<AuthStatusOverlay>
    with TickerProviderStateMixin {
  late AnimationController _overlayController;
  late AnimationController _shimmerController;
  late Animation<double> _overlayAnimation;
  late Animation<double> _shimmerAnimation;
  
  StreamSubscription<ReAuthenticationRequired>? _reAuthSubscription;
  bool _isReAuthenticating = false;

  @override
  void initState() {
    super.initState();
    
    _overlayController = AnimationController(
      duration: const Duration(milliseconds: 600),
      vsync: this,
    );
    
    _shimmerController = AnimationController(
      duration: const Duration(milliseconds: 2000),
      vsync: this,
    );
    
    _overlayAnimation = CurvedAnimation(
      parent: _overlayController,
      curve: Curves.easeInOutCubic,
    );
    
    _shimmerAnimation = Tween<double>(
      begin: -1.0,
      end: 2.0,
    ).animate(CurvedAnimation(
      parent: _shimmerController,
      curve: Curves.easeInOut,
    ));
    
    _setupReAuthListener();
  }

  @override
  void dispose() {
    _overlayController.dispose();
    _shimmerController.dispose();
    _reAuthSubscription?.cancel();
    super.dispose();
  }

  void _setupReAuthListener() {
    final tokenManager = ref.read(tokenManagerProvider);
    _reAuthSubscription = tokenManager.reAuthenticationStream.listen(
      (reAuthEvent) {
        setState(() {
          _isReAuthenticating = true;
        });
        _overlayController.forward();
        _shimmerController.repeat();
      },
    );
  }

  void _hideOverlay() {
    _shimmerController.stop();
    _overlayController.reverse().then((_) {
      if (mounted) {
        setState(() {
          _isReAuthenticating = false;
        });
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);
    
    // Hide overlay when authentication is successful
    if (_isReAuthenticating && authState.isAuthenticated && !authState.isLoading) {
      WidgetsBinding.instance.addPostFrameCallback((_) => _hideOverlay());
    }
    
    return Stack(
      children: [
        widget.child,
        
        // Premium re-authentication overlay
        if (_isReAuthenticating)
          AnimatedBuilder(
            animation: _overlayAnimation,
            builder: (context, child) {
              return Opacity(
                opacity: _overlayAnimation.value * 0.95,
                child: Container(
                  color: Colors.black.withOpacity(0.8),
                  child: _buildReAuthContent(context, authState),
                ),
              );
            },
          ),
      ],
    );
  }

  Widget _buildReAuthContent(BuildContext context, AuthState authState) {
    final theme = Theme.of(context);
    
    return Center(
      child: Container(
        margin: const EdgeInsets.all(32),
        padding: const EdgeInsets.all(32),
        decoration: BoxDecoration(
          color: theme.colorScheme.surface,
          borderRadius: BorderRadius.circular(24),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.3),
              blurRadius: 24,
              spreadRadius: 8,
            ),
          ],
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Premium animated icon
            _buildAnimatedIcon(theme),
            const SizedBox(height: 24),
            
            // Status text
            Text(
              _getStatusTitle(authState),
              style: theme.textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.w600,
                color: theme.colorScheme.onSurface,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 12),
            
            Text(
              _getStatusSubtitle(authState),
              style: theme.textTheme.bodyLarge?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 32),
            
            // Premium loading indicator
            if (authState.isLoading) _buildShimmerLoader(theme),
            
            // Error state
            if (authState.error != null) ...[
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.red.shade50,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.red.shade200),
                ),
                child: Row(
                  children: [
                    Icon(Icons.error_outline, color: Colors.red.shade600),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        'Authentication failed. Please check your credentials.',
                        style: theme.textTheme.bodyMedium?.copyWith(
                          color: Colors.red.shade700,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),
              
              ElevatedButton(
                onPressed: () => ref.read(authProvider.notifier).clearError(),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.red.shade600,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 16),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                child: const Text('Dismiss'),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildAnimatedIcon(ThemeData theme) {
    return Container(
      width: 80,
      height: 80,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: LinearGradient(
          colors: [
            theme.colorScheme.primary.withOpacity(0.2),
            theme.colorScheme.primary.withOpacity(0.1),
          ],
        ),
      ),
      child: AnimatedBuilder(
        animation: _overlayController,
        builder: (context, child) {
          return Transform.rotate(
            angle: _overlayController.value * 2 * 3.14159,
            child: Icon(
              Icons.security,
              size: 40,
              color: theme.colorScheme.primary,
            ),
          );
        },
      ),
    );
  }

  Widget _buildShimmerLoader(ThemeData theme) {
    return Container(
      height: 4,
      width: 200,
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceVariant,
        borderRadius: BorderRadius.circular(2),
      ),
      child: AnimatedBuilder(
        animation: _shimmerAnimation,
        builder: (context, child) {
          return Container(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(2),
              gradient: LinearGradient(
                begin: Alignment(_shimmerAnimation.value - 1, 0),
                end: Alignment(_shimmerAnimation.value, 0),
                colors: [
                  Colors.transparent,
                  theme.colorScheme.primary.withOpacity(0.4),
                  Colors.transparent,
                ],
                stops: const [0.0, 0.5, 1.0],
              ),
            ),
          );
        },
      ),
    );
  }

  String _getStatusTitle(AuthState authState) {
    if (authState.error != null) {
      return 'Authentication Error';
    } else if (authState.isLoading) {
      return 'Reconnecting';
    } else {
      return 'Session Expired';
    }
  }

  String _getStatusSubtitle(AuthState authState) {
    if (authState.error != null) {
      return 'Unable to restore your session automatically.';
    } else if (authState.isLoading) {
      return 'Restoring your secure session...';
    } else {
      return 'Your session has expired. Attempting to reconnect with stored credentials.';
    }
  }
}
