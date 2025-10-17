import 'package:aico_frontend/core/providers/networking_providers.dart';
import 'package:aico_frontend/networking/services/connection_manager.dart';
import 'package:aico_frontend/presentation/providers/auth_provider.dart';
import 'package:aico_frontend/presentation/providers/avatar_state_provider.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Avatar with subtle pulsating ring status indicator - clean, minimal, following design principles
/// Now uses centralized avatar state provider for rich information display
class CompanionAvatar extends ConsumerStatefulWidget {
  const CompanionAvatar({super.key});

  @override
  ConsumerState<CompanionAvatar> createState() => _CompanionAvatarState();
}

class _CompanionAvatarState extends ConsumerState<CompanionAvatar>
    with TickerProviderStateMixin {
  late AnimationController _pulseController;
  late AnimationController _colorTransitionController;
  late AnimationController _expansionTransitionController;
  late Animation<double> _pulseAnimation;
  late Animation<Color?> _ringColorAnimation;
  late Animation<double> _expansionAnimation;
  
  late InternalConnectionStatus _currentStatus;
  late bool _isAuthenticated;
  late AvatarMode _previousAvatarMode;
  late Color _targetRingColor;
  double _currentExpansion = 1.0;
  double _targetExpansion = 1.0;

  @override
  void initState() {
    super.initState();
    
    // Initialize from actual current state to prevent flicker on rebuild
    final connectionManager = ref.read(connectionManagerProvider);
    final authState = ref.read(authProvider);
    final avatarState = ref.read(avatarRingStateProvider);
    
    _currentStatus = connectionManager.health.status;
    _isAuthenticated = authState.isAuthenticated;
    _previousAvatarMode = avatarState.mode;
    
    // Initialize target color based on current avatar mode
    _targetRingColor = _getInitialRingColor(avatarState.mode);
    
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
    
    // Color transition controller for smooth color changes
    _colorTransitionController = AnimationController(
      duration: const Duration(milliseconds: 1200), // Longer transition for smoothness
      vsync: this,
    );
    
    _ringColorAnimation = ColorTween(
      begin: _targetRingColor,
      end: _targetRingColor,
    ).animate(CurvedAnimation(
      parent: _colorTransitionController,
      curve: Curves.easeInOutCubic, // Smoother cubic curve
    ));
    
    // Expansion transition controller for smooth size changes
    _expansionTransitionController = AnimationController(
      duration: const Duration(milliseconds: 1000),
      vsync: this,
    );
    
    _expansionAnimation = Tween<double>(
      begin: 1.0,
      end: 1.0,
    ).animate(CurvedAnimation(
      parent: _expansionTransitionController,
      curve: Curves.easeInOutCubic,
    ));
    
    _startPulsing();
  }

  void _startPulsing() {
    _pulseController.repeat(reverse: true);
  }

  void _stopPulsing() {
    _pulseController.stop();
    _pulseController.reset();
  }

  bool _shouldPulse(AvatarMode avatarMode) {
    // Enhanced pulsing logic for different states
    if (!_isAuthenticated) return false;
    
    // Pulse for most avatar modes
    switch (avatarMode) {
      case AvatarMode.idle:
        return _currentStatus == InternalConnectionStatus.connected;
      case AvatarMode.thinking:
      case AvatarMode.listening:
      case AvatarMode.speaking:
      case AvatarMode.processing:
      case AvatarMode.success:
        return true;
      case AvatarMode.connecting:
        return true;
      case AvatarMode.attention:
        return true;
      case AvatarMode.error:
        return false; // Static for errors
    }
  }

  void _updateAnimationState(AvatarMode avatarMode, double intensity) {
    if (_shouldPulse(avatarMode)) {
      // Adjust pulse speed based on mode and intensity
      final Duration duration = _getPulseDuration(avatarMode, intensity);
      
      if (_pulseController.duration != duration) {
        // Smoothly transition pulse speed by continuing from current position
        final currentValue = _pulseController.value;
        _pulseController.duration = duration;
        
        // Don't reset - continue from current position for smooth transition
        if (!_pulseController.isAnimating) {
          _pulseController.value = currentValue;
          _startPulsing();
        }
      } else if (!_pulseController.isAnimating) {
        _startPulsing();
      }
    } else {
      _stopPulsing();
    }
  }
  
  Duration _getPulseDuration(AvatarMode mode, double intensity) {
    // Base duration modified by intensity (higher intensity = faster)
    final baseDuration = switch (mode) {
      AvatarMode.thinking => 900, // Faster for more visible thinking
      AvatarMode.processing => 800,
      AvatarMode.listening => 1200, // Faster, more responsive
      AvatarMode.speaking => 1000,
      AvatarMode.success => 1000,
      AvatarMode.attention => 1800,
      AvatarMode.connecting => 1500,
      AvatarMode.error => 3000,
      AvatarMode.idle => 3000,
    };
    
    // Intensity affects speed (higher intensity = faster pulse)
    final adjustedDuration = (baseDuration / (0.5 + intensity * 0.5)).round();
    return Duration(milliseconds: adjustedDuration);
  }

  Color _getInitialRingColor(AvatarMode avatarMode) {
    // Get initial color without theme context (for initState)
    // Use full opacity colors as defaults
    const coral = Color(0xFFED7867);
    const emerald = Color(0xFF10B981);
    const amber = Color(0xFFF59E0B);
    const sapphire = Color(0xFF3B82F6);
    const purple = Color(0xFFB8A1EA);
    const violet = Color(0xFF8B5CF6);
    
    switch (avatarMode) {
      case AvatarMode.thinking:
      case AvatarMode.speaking:
        return purple;
      case AvatarMode.processing:
        return violet;
      case AvatarMode.listening:
        return sapphire;
      case AvatarMode.success:
        return emerald;
      case AvatarMode.error:
        return coral;
      case AvatarMode.attention:
        return amber;
      case AvatarMode.connecting:
        return sapphire;
      case AvatarMode.idle:
        return emerald; // Default to green for idle/connected
    }
  }

  Color _getRingColor(AvatarMode avatarMode) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    
    // Enhanced color system for immersive status representation
    const coral = Color(0xFFED7867); // Error/warning accent
    const emerald = Color(0xFF10B981); // Success/healthy state
    const amber = Color(0xFFF59E0B); // Caution/transitional
    const sapphire = Color(0xFF3B82F6); // Processing/connecting
    const purple = Color(0xFFB8A1EA); // Thinking/processing state
    const violet = Color(0xFF8B5CF6); // Deep processing
    
    // Avatar mode takes priority over connection status
    switch (avatarMode) {
      case AvatarMode.thinking:
        return isDark ? purple.withOpacity(0.95) : purple; // More visible
      case AvatarMode.processing:
        return isDark ? violet.withOpacity(0.95) : violet;
      case AvatarMode.listening:
        return isDark ? sapphire.withOpacity(0.95) : sapphire; // Blue for user typing
      case AvatarMode.speaking:
        return isDark ? purple.withOpacity(0.8) : purple.withOpacity(0.9);
      case AvatarMode.success:
        return isDark ? emerald.withOpacity(1.0) : emerald;
      case AvatarMode.error:
        return isDark ? coral.withOpacity(0.9) : coral;
      case AvatarMode.attention:
        return isDark ? amber.withOpacity(0.8) : amber;
      case AvatarMode.connecting:
        return isDark ? sapphire.withOpacity(0.8) : sapphire;
      case AvatarMode.idle:
        // Fall back to connection status for idle mode
        if (!_isAuthenticated) {
          return isDark ? coral.withOpacity(0.7) : coral.withOpacity(0.8);
        }
        
        switch (_currentStatus) {
          case InternalConnectionStatus.connected:
            return isDark ? emerald.withOpacity(0.9) : emerald;
          case InternalConnectionStatus.connecting:
            return isDark ? sapphire.withOpacity(0.8) : sapphire;
          case InternalConnectionStatus.disconnected:
            return isDark ? amber.withOpacity(0.7) : amber;
          case InternalConnectionStatus.offline:
            return isDark ? coral.withOpacity(0.6) : coral.withOpacity(0.7);
          case InternalConnectionStatus.error:
            return isDark ? coral.withOpacity(0.9) : coral;
        }
    }
  }

  String _getTooltipMessage(AvatarMode avatarMode) {
    // Avatar mode messages take priority
    switch (avatarMode) {
      case AvatarMode.thinking:
        return 'Thinking...';
      case AvatarMode.processing:
        return 'Processing...';
      case AvatarMode.listening:
        return 'Listening...';
      case AvatarMode.speaking:
        return 'Speaking...';
      case AvatarMode.success:
        return 'Done!';
      case AvatarMode.error:
        return 'Error occurred';
      case AvatarMode.attention:
        return 'Attention needed';
      case AvatarMode.connecting:
        return 'Connecting...';
      case AvatarMode.idle:
        // Fall back to connection status
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
  }

  double _getPulseMultiplier(AvatarMode mode, double intensity) {
    // Base multiplier for each mode
    final baseMultiplier = switch (mode) {
      AvatarMode.thinking => 1.8, // More dramatic pulse
      AvatarMode.processing => 2.0,
      AvatarMode.listening => 1.6, // More visible
      AvatarMode.speaking => 1.4,
      AvatarMode.success => 1.6,
      AvatarMode.attention => 1.2,
      AvatarMode.connecting => 1.3,
      AvatarMode.error => 1.0,
      AvatarMode.idle => 1.0,
    };
    
    // Intensity further modulates the expansion
    return baseMultiplier * (0.7 + intensity * 0.3);
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _colorTransitionController.dispose();
    _expansionTransitionController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final connectionManager = ref.watch(connectionManagerProvider);
    final authState = ref.watch(authProvider);
    final avatarState = ref.watch(avatarRingStateProvider);
    
    return StreamBuilder<ConnectionHealth>(
      stream: connectionManager.healthStream,
      initialData: connectionManager.health,
      builder: (context, snapshot) {
        final health = snapshot.data ?? connectionManager.health;
        final newStatus = health.status;
        final newAuthState = authState.isAuthenticated;
        
        // Update state and animations when status or avatar mode changes
        if (newStatus != _currentStatus || newAuthState != _isAuthenticated || avatarState.mode != _previousAvatarMode) {
          WidgetsBinding.instance.addPostFrameCallback((_) {
            final newColor = _getRingColor(avatarState.mode);
            
            // Smooth color transition using HSL color space
            if (newColor != _targetRingColor) {
              final currentColor = _colorTransitionController.isAnimating
                  ? (_ringColorAnimation.value ?? _targetRingColor)
                  : _targetRingColor;
              
              // Create custom HSL tween to avoid passing through red
              _ringColorAnimation = _HSLColorTween(
                begin: currentColor,
                end: newColor,
              ).animate(CurvedAnimation(
                parent: _colorTransitionController,
                curve: Curves.easeInOutCubic,
              ));
              
              _targetRingColor = newColor;
              _colorTransitionController.forward(from: 0.0);
            }
            
            // Smooth expansion transition
            final newExpansion = _getPulseMultiplier(avatarState.mode, avatarState.intensity);
            if ((newExpansion - _targetExpansion).abs() > 0.01) {
              _expansionAnimation = Tween<double>(
                begin: _currentExpansion,
                end: newExpansion,
              ).animate(CurvedAnimation(
                parent: _expansionTransitionController,
                curve: Curves.easeInOutCubic,
              ));
              _targetExpansion = newExpansion;
              _expansionTransitionController.forward(from: 0.0).then((_) {
                _currentExpansion = newExpansion;
              });
            }
            
            setState(() {
              _currentStatus = newStatus;
              _isAuthenticated = newAuthState;
              _previousAvatarMode = avatarState.mode;
            });
            _updateAnimationState(avatarState.mode, avatarState.intensity);
          });
        }
        
        return Tooltip(
          message: _getTooltipMessage(avatarState.mode),
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
              // Use animated color or target color
              final ringColor = _colorTransitionController.isAnimating 
                  ? (_ringColorAnimation.value ?? _targetRingColor)
                  : _getRingColor(avatarState.mode);
              final ringOpacity = _shouldPulse(avatarState.mode) ? _pulseAnimation.value : 0.8;
              
              // Pulse expansion with smooth transition
              final pulseMultiplier = _expansionTransitionController.isAnimating
                  ? _expansionAnimation.value
                  : _currentExpansion;
              
              return SizedBox(
                width: 240, // Increased to allow glow to extend
                height: 240,
                child: Stack(
                  clipBehavior: Clip.none, // Allow glow to extend beyond bounds
                  alignment: Alignment.center,
                  children: [
                    // Outer breathing ring with glow
                    Container(
                      width: 148 + (_pulseAnimation.value * 26 * pulseMultiplier),
                      height: 148 + (_pulseAnimation.value * 26 * pulseMultiplier),
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: Colors.transparent,
                        border: Border.all(
                          color: ringColor.withOpacity(theme.brightness == Brightness.dark ? ringOpacity * 0.75 : ringOpacity * 0.95),
                          width: 3.0,
                        ),
                        boxShadow: [
                          // Dark contrast shadow behind ring for definition
                          BoxShadow(
                            color: Colors.black.withOpacity(theme.brightness == Brightness.dark ? 0.4 : 0.15),
                            blurRadius: 8,
                            spreadRadius: -2,
                          ),
                          // Multi-layer glow for smooth gradient (reduces banding)
                          BoxShadow(
                            color: ringColor.withOpacity(theme.brightness == Brightness.dark ? 0.4 : 0.3),
                            blurRadius: 50,
                            spreadRadius: 15,
                          ),
                          BoxShadow(
                            color: ringColor.withOpacity(theme.brightness == Brightness.dark ? 0.3 : 0.22),
                            blurRadius: 70,
                            spreadRadius: 22,
                          ),
                          BoxShadow(
                            color: ringColor.withOpacity(theme.brightness == Brightness.dark ? 0.22 : 0.16),
                            blurRadius: 90,
                            spreadRadius: 28,
                          ),
                          BoxShadow(
                            color: ringColor.withOpacity(theme.brightness == Brightness.dark ? 0.15 : 0.11),
                            blurRadius: 110,
                            spreadRadius: 35,
                          ),
                          BoxShadow(
                            color: ringColor.withOpacity(theme.brightness == Brightness.dark ? 0.08 : 0.06),
                            blurRadius: 130,
                            spreadRadius: 42,
                          ),
                        ],
                      ),
                    ),
                      // Inner breathing ring with subtle glow
                      Container(
                        width: 135 + (_pulseAnimation.value * 16 * pulseMultiplier),
                        height: 135 + (_pulseAnimation.value * 16 * pulseMultiplier),
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: Colors.transparent,
                          border: Border.all(
                            color: ringColor.withOpacity(theme.brightness == Brightness.dark ? ringOpacity * 0.65 : ringOpacity * 0.8),
                            width: 1.8,
                          ),
                          boxShadow: [
                            // Dark contrast shadow for definition
                            BoxShadow(
                              color: Colors.black.withOpacity(theme.brightness == Brightness.dark ? 0.3 : 0.1),
                              blurRadius: 6,
                              spreadRadius: -1,
                            ),
                            // Subtle inner glow for depth
                            BoxShadow(
                              color: ringColor.withOpacity(theme.brightness == Brightness.dark ? 0.15 : 0.12),
                              blurRadius: 10,
                              spreadRadius: 0,
                            ),
                          ],
                        ),
                      ),
                      // Clean avatar circle with mood-colored gradient overlay
                      SizedBox(
                        width: 125,
                        height: 125,
                        child: ClipOval(
                          child: Stack(
                            fit: StackFit.expand,
                            children: [
                              // Avatar image
                              Image.asset(
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
                              // Subtle mood-colored radial gradient overlay
                              // Creates seamless transition from rings to avatar
                              Container(
                                decoration: BoxDecoration(
                                  gradient: RadialGradient(
                                    center: Alignment.center,
                                    radius: 0.8,
                                    colors: [
                                      Colors.transparent, // Clear center - avatar fully visible
                                      Colors.transparent, // Keep center clear
                                      ringColor.withOpacity(0.08), // Very subtle at mid-range
                                      ringColor.withOpacity(0.18), // Gentle glow at edges
                                    ],
                                    stops: const [0.0, 0.4, 0.7, 1.0],
                                  ),
                                ),
                              ),
                            ],
                          ),
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

/// Custom color tween that interpolates through HSL color space
/// This prevents colors from passing through unwanted hues (e.g., red between green and purple)
class _HSLColorTween extends Tween<Color?> {
  _HSLColorTween({required super.begin, required super.end});

  @override
  Color? lerp(double t) {
    if (begin == null || end == null) return null;
    
    final beginHSL = HSLColor.fromColor(begin!);
    final endHSL = HSLColor.fromColor(end!);
    
    // Interpolate hue taking the shortest path around the color wheel
    double hue;
    final hueDiff = endHSL.hue - beginHSL.hue;
    if (hueDiff.abs() <= 180) {
      hue = beginHSL.hue + hueDiff * t;
    } else if (hueDiff > 180) {
      hue = beginHSL.hue + (hueDiff - 360) * t;
    } else {
      hue = beginHSL.hue + (hueDiff + 360) * t;
    }
    
    // Normalize hue to 0-360 range
    hue = hue % 360;
    if (hue < 0) hue += 360;
    
    return HSLColor.fromAHSL(
      beginHSL.alpha + (endHSL.alpha - beginHSL.alpha) * t,
      hue,
      beginHSL.saturation + (endHSL.saturation - beginHSL.saturation) * t,
      beginHSL.lightness + (endHSL.lightness - beginHSL.lightness) * t,
    ).toColor();
  }
}
