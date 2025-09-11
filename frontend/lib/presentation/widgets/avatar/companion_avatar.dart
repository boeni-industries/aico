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
  
  ConnectionStatus _currentStatus = ConnectionStatus.connected;
  bool _isAuthenticated = false;

  @override
  void initState() {
    super.initState();
    
    // Subtle pulse animation - like calm breathing
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
    return _currentStatus == ConnectionStatus.connected && _isAuthenticated;
  }

  void _updateAnimationState() {
    if (_shouldPulse()) {
      _startPulsing();
    } else {
      _stopPulsing();
    }
  }

  Color _getRingColor() {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    
    // Stronger colors for light mode, softer for dark mode
    const softPurple = Color(0xFFB8A1EA);
    final lightPurple = Color(0xFF8B5CF6); // Stronger purple for light mode
    
    if (!_isAuthenticated) {
      return isDark ? Colors.orange.shade400 : Colors.orange.shade600;
    }
    
    switch (_currentStatus) {
      case ConnectionStatus.connected:
        return isDark ? softPurple : lightPurple;
      case ConnectionStatus.connecting:
        return isDark ? Colors.blue.shade400 : Colors.blue.shade600;
      case ConnectionStatus.disconnected:
        return isDark ? Colors.orange.shade400 : Colors.orange.shade600;
      case ConnectionStatus.offline:
        return isDark ? Colors.red.shade400 : Colors.red.shade600;
      case ConnectionStatus.error:
        return isDark ? Colors.red.shade600 : Colors.red.shade700;
    }
  }

  String _getTooltipMessage() {
    if (!_isAuthenticated) {
      return 'Authentication required';
    }
    
    switch (_currentStatus) {
      case ConnectionStatus.connected:
        return 'All systems operational';
      case ConnectionStatus.connecting:
        return 'Establishing connection...';
      case ConnectionStatus.disconnected:
        return 'Connection interrupted - attempting to reconnect';
      case ConnectionStatus.offline:
        return 'No network connection available';
      case ConnectionStatus.error:
        return 'Connection error - check network settings';
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
