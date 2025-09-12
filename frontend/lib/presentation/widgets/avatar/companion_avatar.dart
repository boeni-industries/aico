import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/auth_provider.dart';
import '../../../core/providers/networking_providers.dart';
import '../../../networking/services/connection_manager.dart';

/// Avatar with subtle pulsating ring status indicator - clean, minimal, following design principles
class CompanionAvatar extends ConsumerStatefulWidget {
  const CompanionAvatar({super.key});

  @override
  ConsumerState<CompanionAvatar> createState() => _CompanionAvatarState();
}

class _CompanionAvatarState extends ConsumerState<CompanionAvatar>
    with TickerProviderStateMixin {
  late AnimationController _pulseController;
  late Animation<double> _pulseAnimation;
  
  InternalConnectionStatus _currentStatus = InternalConnectionStatus.connected;
  bool _isAuthenticated = false;

  @override
  void initState() {
    super.initState();
    
    // Dynamic pulse animation - adapts to connection state
    _pulseController = AnimationController(
      duration: const Duration(milliseconds: 3000),
      vsync: this,
    );
    
    _pulseAnimation = Tween<double>(
      begin: 0.7,
      end: 1.0,
    ).animate(CurvedAnimation(
      parent: _pulseController,
      curve: Curves.easeInOut,
    ));
    
    _startPulsing();
  }

  void _startPulsing() {
    if (_shouldPulse()) {
      _pulseController.repeat(reverse: true);
    }
  }

  void _stopPulsing() {
    _pulseController.stop();
    _pulseController.reset();
  }

  bool _shouldPulse() {
    // Enhanced pulsing logic for different states
    if (!_isAuthenticated) return false;
    
    switch (_currentStatus) {
      case InternalConnectionStatus.connected:
        return true; // Healthy breathing
      case InternalConnectionStatus.connecting:
        return true; // Active connection pulse
      default:
        return false; // Static for issues
    }
  }

  void _updateAnimationState() {
    if (_shouldPulse()) {
      // Adjust pulse speed based on connection state
      final duration = _currentStatus == InternalConnectionStatus.connecting
          ? const Duration(milliseconds: 1500) // Faster for connecting
          : const Duration(milliseconds: 3000); // Slower for connected
      
      if (_pulseController.duration != duration) {
        _pulseController.duration = duration;
        _pulseController.reset();
      }
      _startPulsing();
    } else {
      _stopPulsing();
    }
  }

  Color _getRingColor() {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    
    // Enhanced color system for immersive status representation
    const coral = Color(0xFFED7867); // Error/warning accent
    const emerald = Color(0xFF10B981); // Success/healthy state
    const amber = Color(0xFFF59E0B); // Caution/transitional
    const sapphire = Color(0xFF3B82F6); // Processing/connecting
    
    if (!_isAuthenticated) {
      return isDark ? coral.withOpacity(0.7) : coral.withOpacity(0.8);
    }
    
    switch (_currentStatus) {
      case InternalConnectionStatus.connected:
        // Vibrant emerald for optimal connection - more celebratory
        return isDark ? emerald.withOpacity(0.9) : emerald;
      case InternalConnectionStatus.connecting:
        // Dynamic sapphire for active connection attempts
        return isDark ? sapphire.withOpacity(0.8) : sapphire;
      case InternalConnectionStatus.disconnected:
        // Warm amber for temporary disconnection
        return isDark ? amber.withOpacity(0.7) : amber;
      case InternalConnectionStatus.offline:
        // Muted coral for network unavailability
        return isDark ? coral.withOpacity(0.6) : coral.withOpacity(0.7);
      case InternalConnectionStatus.error:
        // Stronger coral for persistent errors
        return isDark ? coral.withOpacity(0.9) : coral;
    }
  }

  String _getTooltipMessage() {
    if (!_isAuthenticated) {
      return 'Touch to authenticate';
    }
    
    switch (_currentStatus) {
      case InternalConnectionStatus.connected:
        return 'Ready to chat';
      case InternalConnectionStatus.connecting:
        return 'Connecting...';
      case InternalConnectionStatus.disconnected:
        return 'Reconnecting in background';
      case InternalConnectionStatus.offline:
        return 'Check network connection';
      case InternalConnectionStatus.error:
        return 'Connection issue - will retry automatically';
    }
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final connectionManager = ref.watch(connectionManagerProvider);
    final authState = ref.watch(authProvider);
    
    return StreamBuilder<ConnectionHealth>(
      stream: connectionManager.healthStream,
      initialData: connectionManager.health,
      builder: (context, snapshot) {
        final health = snapshot.data ?? connectionManager.health;
        final newStatus = health.status;
        final newAuthState = authState.isAuthenticated;
        
        // Update state and animations when status changes
        if (newStatus != _currentStatus || newAuthState != _isAuthenticated) {
          WidgetsBinding.instance.addPostFrameCallback((_) {
            setState(() {
              _currentStatus = newStatus;
              _isAuthenticated = newAuthState;
            });
            _updateAnimationState();
          });
        }
        
        return Tooltip(
          message: _getTooltipMessage(),
          decoration: BoxDecoration(
            color: Colors.black87,
            borderRadius: BorderRadius.circular(8),
          ),
          textStyle: const TextStyle(
            color: Colors.white,
            fontSize: 12,
            fontWeight: FontWeight.w500,
          ),
          child: AnimatedBuilder(
            animation: _pulseController,
            builder: (context, child) {
              final ringColor = _getRingColor();
              final ringOpacity = _shouldPulse() ? _pulseAnimation.value : 0.8;
              
              return SizedBox(
                width: 182,
                height: 182,
                child: RepaintBoundary(
                  child: Stack(
                    alignment: Alignment.center,
                    children: [
                      // Outer breathing ring
                      Container(
                        width: 148 + (_pulseAnimation.value * 26),
                        height: 148 + (_pulseAnimation.value * 26),
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: Colors.transparent,
                          border: Border.all(
                            color: ringColor.withOpacity(theme.brightness == Brightness.dark ? ringOpacity * 0.6 : ringOpacity * 0.9),
                            width: 2.6,
                          ),
                        ),
                      ),
                      // Inner breathing ring
                      Container(
                        width: 135 + (_pulseAnimation.value * 16),
                        height: 135 + (_pulseAnimation.value * 16),
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: Colors.transparent,
                          border: Border.all(
                            color: ringColor.withOpacity(theme.brightness == Brightness.dark ? ringOpacity * 0.5 : ringOpacity * 0.7),
                            width: 1.3,
                          ),
                        ),
                      ),
                      // Clean avatar circle
                      Container(
                        width: 125,
                        height: 125,
                        child: ClipOval(
                          child: Image.asset(
                            'assets/images/aico.png',
                            width: 125,
                            height: 125,
                            fit: BoxFit.cover,
                            errorBuilder: (context, error, stackTrace) {
                              // Fallback to icon if image fails to load
                              return Icon(
                                Icons.person_2,
                                size: 62,
                                color: ringColor,
                              );
                            },
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              );
            },
          ),
        );
      },
    );
  }
}
