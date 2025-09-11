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
      begin: 0.6,
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
    const softPurple = Color(0xFFB8A1EA);
    
    if (!_isAuthenticated) {
      return Colors.orange.shade400;
    }
    
    switch (_currentStatus) {
      case ConnectionStatus.connected:
        return softPurple;
      case ConnectionStatus.connecting:
        return Colors.blue.shade400;
      case ConnectionStatus.disconnected:
        return Colors.orange.shade400;
      case ConnectionStatus.offline:
        return Colors.red.shade400;
      case ConnectionStatus.error:
        return Colors.red.shade600;
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
                width: 120,
                height: 120,
                child: Stack(
                  alignment: Alignment.center,
                  children: [
                    // Subtle pulsating ring
                    Container(
                      width: 120,
                      height: 120,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        border: Border.all(
                          color: ringColor.withOpacity(ringOpacity),
                          width: 2,
                        ),
                      ),
                    ),
                    // Clean avatar circle
                    Container(
                      width: 96,
                      height: 96,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: theme.colorScheme.surface,
                        border: Border.all(
                          color: theme.dividerColor.withOpacity(0.1),
                          width: 1,
                        ),
                      ),
                      child: Icon(
                        Icons.person_2,
                        size: 48,
                        color: ringColor,
                      ),
                    ),
                  ],
                ),
              );
            },
          ),
        );
      },
    );
  }
}
