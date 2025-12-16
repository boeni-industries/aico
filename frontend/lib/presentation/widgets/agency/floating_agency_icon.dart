import 'package:aico_frontend/presentation/providers/agency_state_provider.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Floating icon above avatar that indicates agency state changes
/// Gaming-inspired: subtle indicator that prompts hover discovery
class FloatingAgencyIcon extends ConsumerStatefulWidget {
  const FloatingAgencyIcon({super.key});

  @override
  ConsumerState<FloatingAgencyIcon> createState() => _FloatingAgencyIconState();
}

class _FloatingAgencyIconState extends ConsumerState<FloatingAgencyIcon>
    with TickerProviderStateMixin {
  late AnimationController _bobController;
  late AnimationController _stateAnimationController;
  late AnimationController _appearController;
  
  late Animation<double> _bobAnimation;
  late Animation<double> _scaleAnimation;
  late Animation<double> _rotationAnimation;
  late Animation<double> _pulseAnimation;
  late Animation<double> _appearAnimation;
  
  AgencyBadgeMode? _previousMode;

  @override
  void initState() {
    super.initState();
    
    // Gentle vertical bob animation (like quest markers in games)
    _bobController = AnimationController(
      duration: const Duration(milliseconds: 2000),
      vsync: this,
    );
    
    _bobAnimation = Tween<double>(
      begin: -2.0,
      end: 2.0,
    ).animate(CurvedAnimation(
      parent: _bobController,
      curve: Curves.easeInOut,
    ));
    
    _bobController.repeat(reverse: true);
    
    // State-specific animation controller
    _stateAnimationController = AnimationController(
      duration: const Duration(milliseconds: 1200),
      vsync: this,
    );
    
    // Scale animation (for sparkle pulse and check bounce)
    _scaleAnimation = Tween<double>(
      begin: 0.9,
      end: 1.0,
    ).animate(CurvedAnimation(
      parent: _stateAnimationController,
      curve: Curves.easeInOut,
    ));
    
    // Rotation animation (for sparkle wobble)
    _rotationAnimation = Tween<double>(
      begin: -0.05,
      end: 0.05,
    ).animate(CurvedAnimation(
      parent: _stateAnimationController,
      curve: Curves.easeInOut,
    ));
    
    // Pulse animation (for attention dot)
    _pulseAnimation = Tween<double>(
      begin: 0.6,
      end: 1.0,
    ).animate(CurvedAnimation(
      parent: _stateAnimationController,
      curve: Curves.easeInOut,
    ));
    
    // Appear/disappear animation
    _appearController = AnimationController(
      duration: const Duration(milliseconds: 300),
      vsync: this,
    );
    
    _appearAnimation = CurvedAnimation(
      parent: _appearController,
      curve: Curves.easeOut,
    );
  }

  @override
  void dispose() {
    _bobController.dispose();
    _stateAnimationController.dispose();
    _appearController.dispose();
    super.dispose();
  }
  
  void _updateAnimationForMode(AgencyBadgeMode mode) {
    // Stop previous animation
    _stateAnimationController.stop();
    
    switch (mode) {
      case AgencyBadgeMode.activeIntention:
      case AgencyBadgeMode.goalProgress:
        // Sparkle: gentle pulse with repeat
        _stateAnimationController.repeat(reverse: true);
        break;
      case AgencyBadgeMode.lessonPending:
        // Attention dot: faster pulse for urgency
        _stateAnimationController.duration = const Duration(milliseconds: 1500);
        _stateAnimationController.repeat(reverse: true);
        break;
      case AgencyBadgeMode.goalCompleted:
        // Check: bounce once then gentle pulse
        _stateAnimationController.duration = const Duration(milliseconds: 600);
        _stateAnimationController.forward().then((_) {
          _stateAnimationController.duration = const Duration(milliseconds: 2000);
          _stateAnimationController.repeat(reverse: true);
        });
        break;
      case AgencyBadgeMode.multipleItems:
        // Three dots: sequential animation handled by custom painter
        _stateAnimationController.duration = const Duration(milliseconds: 1200);
        _stateAnimationController.repeat();
        break;
      case AgencyBadgeMode.none:
        break;
    }
  }

  @override
  Widget build(BuildContext context) {
    final agencyState = ref.watch(agencyBadgeStateProvider);
    
    // Handle appear/disappear animation
    if (agencyState.isVisible) {
      if (_previousMode != agencyState.mode) {
        _previousMode = agencyState.mode;
        _appearController.forward(from: 0.0);
        _updateAnimationForMode(agencyState.mode);
      }
    } else {
      if (_previousMode != null) {
        _previousMode = null;
        _appearController.reverse();
      }
    }
    
    // Don't show if no agency activity
    if (!agencyState.isVisible && _appearController.isDismissed) {
      return const SizedBox.shrink();
    }

    final color = _getAgencyColor(agencyState.mode);
    final useCustomPainter = agencyState.mode == AgencyBadgeMode.multipleItems;

    return AnimatedBuilder(
      animation: Listenable.merge([_bobAnimation, _stateAnimationController, _appearAnimation]),
      builder: (context, child) {
        // Calculate glow intensity based on animation state
        final glowIntensity = _getGlowIntensity(agencyState.mode);
        
        return FadeTransition(
          opacity: _appearAnimation,
          child: ScaleTransition(
            scale: Tween<double>(begin: 0.0, end: 1.0).animate(_appearAnimation),
            child: Transform.translate(
              offset: Offset(0, _bobAnimation.value),
              child: Transform.scale(
                scale: _getScaleForMode(agencyState.mode),
                child: Transform.rotate(
                  angle: _getRotationForMode(agencyState.mode),
                  child: Container(
                    width: 24,
                    height: 24,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      boxShadow: [
                        // Animated soft glow effect
                        BoxShadow(
                          color: color.withOpacity(0.4 * glowIntensity),
                          blurRadius: 8,
                          spreadRadius: 2,
                        ),
                        BoxShadow(
                          color: color.withOpacity(0.2 * glowIntensity),
                          blurRadius: 16,
                          spreadRadius: 4,
                        ),
                      ],
                    ),
                    child: useCustomPainter
                        ? CustomPaint(
                            painter: _ThreeDotsAnimatedPainter(
                              color: color,
                              progress: _stateAnimationController.value,
                            ),
                          )
                        : Opacity(
                            opacity: _getOpacityForMode(agencyState.mode),
                            child: Icon(
                              _getAgencyIcon(agencyState.mode),
                              size: 20,
                              color: color,
                              shadows: [
                                Shadow(
                                  color: color.withOpacity(0.5),
                                  blurRadius: 4,
                                ),
                              ],
                            ),
                          ),
                  ),
                ),
              ),
            ),
          ),
        );
      },
    );
  }
  
  double _getScaleForMode(AgencyBadgeMode mode) {
    switch (mode) {
      case AgencyBadgeMode.activeIntention:
      case AgencyBadgeMode.goalProgress:
        return _scaleAnimation.value;
      case AgencyBadgeMode.goalCompleted:
        // Bounce effect: scale up more on completion
        return 1.0 + (_scaleAnimation.value - 0.9) * 2.0;
      default:
        return 1.0;
    }
  }
  
  double _getRotationForMode(AgencyBadgeMode mode) {
    switch (mode) {
      case AgencyBadgeMode.activeIntention:
      case AgencyBadgeMode.goalProgress:
        return _rotationAnimation.value;
      default:
        return 0.0;
    }
  }
  
  double _getOpacityForMode(AgencyBadgeMode mode) {
    switch (mode) {
      case AgencyBadgeMode.lessonPending:
        return _pulseAnimation.value;
      default:
        return 1.0;
    }
  }
  
  double _getGlowIntensity(AgencyBadgeMode mode) {
    switch (mode) {
      case AgencyBadgeMode.lessonPending:
        return _pulseAnimation.value;
      case AgencyBadgeMode.activeIntention:
      case AgencyBadgeMode.goalProgress:
        return 0.7 + (_scaleAnimation.value - 0.9) * 3.0;
      case AgencyBadgeMode.goalCompleted:
        return 1.0;
      default:
        return 0.8;
    }
  }

  /// Get icon for agency state
  IconData _getAgencyIcon(AgencyBadgeMode mode) {
    switch (mode) {
      case AgencyBadgeMode.activeIntention:
      case AgencyBadgeMode.goalProgress:
        return Icons.auto_awesome; // Sparkle for active work
      case AgencyBadgeMode.lessonPending:
        return Icons.circle; // Dot for attention needed
      case AgencyBadgeMode.goalCompleted:
        return Icons.check_circle; // Check for success
      case AgencyBadgeMode.multipleItems:
        return Icons.more_horiz; // Placeholder - uses custom painter
      case AgencyBadgeMode.none:
        return Icons.circle; // Fallback
    }
  }

  /// Get color for agency state
  Color _getAgencyColor(AgencyBadgeMode mode) {
    const purple = Color(0xFFB8A1EA);
    const amber = Color(0xFFF59E0B);
    const emerald = Color(0xFF10B981);
    
    switch (mode) {
      case AgencyBadgeMode.lessonPending:
        return amber;
      case AgencyBadgeMode.goalCompleted:
        return emerald;
      case AgencyBadgeMode.activeIntention:
      case AgencyBadgeMode.goalProgress:
      case AgencyBadgeMode.multipleItems:
        return purple;
      case AgencyBadgeMode.none:
        return purple;
    }
  }
}

/// Custom painter for animated three-dot indicator
/// Dots pulse in sequence (left → center → right) for visual interest
class _ThreeDotsAnimatedPainter extends CustomPainter {
  final Color color;
  final double progress; // 0.0 to 1.0

  _ThreeDotsAnimatedPainter({
    required this.color,
    required this.progress,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..style = PaintingStyle.fill;

    final center = Offset(size.width / 2, size.height / 2);
    final dotRadius = 2.5;
    final spacing = 6.0;

    // Three dot positions (left, center, right)
    final dots = [
      Offset(center.dx - spacing, center.dy),
      Offset(center.dx, center.dy),
      Offset(center.dx + spacing, center.dy),
    ];

    // Each dot animates in sequence
    // Dot 1: 0.0-0.33, Dot 2: 0.33-0.66, Dot 3: 0.66-1.0
    for (int i = 0; i < dots.length; i++) {
      final dotStart = i / 3.0;
      final dotEnd = (i + 1) / 3.0;
      
      double opacity;
      if (progress < dotStart) {
        opacity = 0.3; // Dim before animation
      } else if (progress >= dotStart && progress < dotEnd) {
        // Animate from 0.3 to 1.0 during this dot's window
        final localProgress = (progress - dotStart) / (dotEnd - dotStart);
        opacity = 0.3 + (0.7 * (1.0 - (localProgress - 0.5).abs() * 2.0));
      } else {
        opacity = 0.3; // Dim after animation
      }

      paint.color = color.withOpacity(opacity);
      canvas.drawCircle(dots[i], dotRadius, paint);
      
      // Add glow for active dot
      if (opacity > 0.5) {
        paint.color = color.withOpacity(opacity * 0.3);
        canvas.drawCircle(dots[i], dotRadius * 1.8, paint);
      }
    }
  }

  @override
  bool shouldRepaint(_ThreeDotsAnimatedPainter oldDelegate) {
    return oldDelegate.progress != progress || oldDelegate.color != color;
  }
}
