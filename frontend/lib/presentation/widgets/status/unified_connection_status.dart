import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/providers/networking_providers.dart';
import '../../../networking/services/connection_manager.dart';
import '../../providers/auth_provider.dart';

/// Unified, immersive connection status system that enhances the avatar
/// without breaking immersion. Follows AICO's simplicity and DRY principles.
/// 
/// Replaces multiple overlapping status systems with a single, cohesive solution.
class UnifiedConnectionStatus extends ConsumerStatefulWidget {
  final Widget child;
  
  const UnifiedConnectionStatus({
    super.key,
    required this.child,
  });

  @override
  ConsumerState<UnifiedConnectionStatus> createState() => _UnifiedConnectionStatusState();
}

class _UnifiedConnectionStatusState extends ConsumerState<UnifiedConnectionStatus>
    with TickerProviderStateMixin {
  late AnimationController _ambientController;
  late AnimationController _transitionController;
  
  InternalConnectionStatus _currentStatus = InternalConnectionStatus.connected;
  bool _showTransitionEffect = false;

  @override
  void initState() {
    super.initState();
    
    // Single ambient animation for connected state
    _ambientController = AnimationController(
      duration: const Duration(seconds: 6),
      vsync: this,
    );
    
    // Transition effects for status changes
    _transitionController = AnimationController(
      duration: const Duration(milliseconds: 1200),
      vsync: this,
    );
  }

  @override
  void dispose() {
    _ambientController.dispose();
    _transitionController.dispose();
    super.dispose();
  }

  void _handleStatusChange(InternalConnectionStatus newStatus, bool isAuthenticated) {
    if (newStatus == _currentStatus) return;
    
    final wasDisconnected = _currentStatus != InternalConnectionStatus.connected;
    final isConnected = newStatus == InternalConnectionStatus.connected;
    
    setState(() => _currentStatus = newStatus);
    
    // Show subtle transition effect for reconnection
    if (wasDisconnected && isConnected && isAuthenticated) {
      _showReconnectionSuccess();
    }
    
    _updateAnimations();
  }

  void _showReconnectionSuccess() {
    setState(() => _showTransitionEffect = true);
    _transitionController.forward().then((_) {
      if (mounted) {
        setState(() => _showTransitionEffect = false);
        _transitionController.reset();
      }
    });
  }

  void _updateAnimations() {
    if (_currentStatus == InternalConnectionStatus.connected) {
      _ambientController.repeat();
    } else {
      _ambientController.stop();
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
        final isAuthenticated = authState.isAuthenticated;
        
        WidgetsBinding.instance.addPostFrameCallback((_) {
          _handleStatusChange(status, isAuthenticated);
        });
        
        return Stack(
          children: [
            widget.child,
            
            // Ambient particles for connected state
            if (_currentStatus == InternalConnectionStatus.connected && isAuthenticated)
              _buildAmbientEffect(),
            
            // Reconnection celebration
            if (_showTransitionEffect)
              _buildTransitionEffect(),
            
            // Contextual hint (minimal, only when actionable)
            if (_shouldShowHint(status, isAuthenticated))
              _buildContextualHint(status, isAuthenticated),
          ],
        );
      },
    );
  }

  Widget _buildAmbientEffect() {
    return Positioned.fill(
      child: AnimatedBuilder(
        animation: _ambientController,
        builder: (context, child) {
          return CustomPaint(
            painter: AmbientEffectPainter(
              progress: _ambientController.value,
              color: const Color(0xFF10B981).withOpacity(0.08),
            ),
          );
        },
      ),
    );
  }

  Widget _buildTransitionEffect() {
    return Positioned.fill(
      child: AnimatedBuilder(
        animation: _transitionController,
        builder: (context, child) {
          return CustomPaint(
            painter: TransitionEffectPainter(
              progress: _transitionController.value,
              color: const Color(0xFF10B981),
            ),
          );
        },
      ),
    );
  }

  bool _shouldShowHint(InternalConnectionStatus status, bool isAuthenticated) {
    // Only show for actionable states - keep it minimal
    return !isAuthenticated || 
           status == InternalConnectionStatus.offline ||
           status == InternalConnectionStatus.error;
  }

  Widget _buildContextualHint(InternalConnectionStatus status, bool isAuthenticated) {
    final (message, icon, color) = _getHintInfo(status, isAuthenticated);
    
    return Positioned(
      bottom: 100,
      left: 0,
      right: 0,
      child: Center(
        child: TweenAnimationBuilder<double>(
          duration: const Duration(milliseconds: 600),
          tween: Tween(begin: 0.0, end: 1.0),
          builder: (context, value, child) {
            return Transform.translate(
              offset: Offset(0, 15 * (1 - value)),
              child: Opacity(
                opacity: value * 0.9,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: Colors.black.withOpacity(0.75),
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: color.withOpacity(0.4), width: 1),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(icon, size: 14, color: color),
                      const SizedBox(width: 6),
                      Text(
                        message,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 11,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            );
          },
        ),
      ),
    );
  }

  (String, IconData, Color) _getHintInfo(InternalConnectionStatus status, bool isAuthenticated) {
    if (!isAuthenticated) {
      return ("Touch avatar to authenticate", Icons.fingerprint, const Color(0xFFED7867));
    }
    
    switch (status) {
      case InternalConnectionStatus.offline:
        return ("Working offline", Icons.cloud_off_outlined, const Color(0xFFF59E0B));
      case InternalConnectionStatus.error:
        return ("Connection issue", Icons.refresh, const Color(0xFFED7867));
      default:
        return ("", Icons.info, Colors.grey);
    }
  }
}

/// Minimal ambient effect painter
class AmbientEffectPainter extends CustomPainter {
  final double progress;
  final Color color;
  
  AmbientEffectPainter({required this.progress, required this.color});
  
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..style = PaintingStyle.fill;
    final center = Offset(size.width / 2, size.height / 2);
    
    // Subtle floating particles around avatar area
    for (int i = 0; i < 6; i++) {
      final angle = (i / 6) * 2 * math.pi + (progress * 0.5);
      final radius = 120 + (math.sin(progress * 2 * math.pi + i) * 15);
      final x = center.dx + math.cos(angle) * radius;
      final y = center.dy + math.sin(angle) * radius;
      
      final opacity = (math.sin(progress * 2 * math.pi + i * 0.7) + 1) * 0.5;
      paint.color = color.withOpacity(opacity * 0.4);
      
      canvas.drawCircle(Offset(x, y), 1.5, paint);
    }
  }
  
  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => true;
}

/// Transition effect for reconnection success
class TransitionEffectPainter extends CustomPainter {
  final double progress;
  final Color color;
  
  TransitionEffectPainter({required this.progress, required this.color});
  
  @override
  void paint(Canvas canvas, Size size) {
    if (progress == 0) return;
    
    final paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5;
    
    final center = Offset(size.width / 2, size.height / 2);
    final radius = progress * 100;
    
    // Expanding ring
    paint.color = color.withOpacity(0.6 * (1 - progress));
    canvas.drawCircle(center, radius, paint);
    
    // Subtle sparkles
    paint.style = PaintingStyle.fill;
    for (int i = 0; i < 4; i++) {
      final angle = (i / 4) * 2 * math.pi;
      final sparkleRadius = radius * 0.7;
      final x = center.dx + math.cos(angle) * sparkleRadius;
      final y = center.dy + math.sin(angle) * sparkleRadius;
      
      paint.color = color.withOpacity(0.8 * (1 - progress));
      canvas.drawCircle(Offset(x, y), 2 * (1 - progress), paint);
    }
  }
  
  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => true;
}
