import 'dart:math' as math;

import 'package:aico_frontend/presentation/providers/agency_state_provider.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Agency badge indicator positioned at bottom-right of avatar
/// Displays current agency state (intentions, lessons, goals)
class AgencyBadge extends ConsumerStatefulWidget {
  final VoidCallback? onTap;
  
  const AgencyBadge({
    super.key,
    this.onTap,
  });

  @override
  ConsumerState<AgencyBadge> createState() => _AgencyBadgeState();
}

class _AgencyBadgeState extends ConsumerState<AgencyBadge>
    with TickerProviderStateMixin {
  late AnimationController _pulseController;
  late AnimationController _rotationController;
  late AnimationController _burstController;
  late Animation<double> _pulseAnimation;
  late Animation<double> _rotationAnimation;
  late Animation<double> _burstAnimation;

  @override
  void initState() {
    super.initState();
    
    // Pulse animation for attention states
    _pulseController = AnimationController(
      duration: const Duration(milliseconds: 1500),
      vsync: this,
    );
    
    _pulseAnimation = Tween<double>(
      begin: 0.8,
      end: 1.0,
    ).animate(CurvedAnimation(
      parent: _pulseController,
      curve: Curves.easeInOut,
    ));
    
    // Rotation animation for progress states
    _rotationController = AnimationController(
      duration: const Duration(milliseconds: 2000),
      vsync: this,
    );
    
    _rotationAnimation = Tween<double>(
      begin: 0.0,
      end: 1.0,
    ).animate(CurvedAnimation(
      parent: _rotationController,
      curve: Curves.linear,
    ));
    
    // Burst animation for completion
    _burstController = AnimationController(
      duration: const Duration(milliseconds: 800),
      vsync: this,
    );
    
    _burstAnimation = Tween<double>(
      begin: 0.0,
      end: 1.0,
    ).animate(CurvedAnimation(
      parent: _burstController,
      curve: Curves.easeOut,
    ));
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _rotationController.dispose();
    _burstController.dispose();
    super.dispose();
  }

  void _updateAnimations(AgencyBadgeMode mode) {
    switch (mode) {
      case AgencyBadgeMode.none:
        _pulseController.stop();
        _rotationController.stop();
        _burstController.stop();
        break;
      case AgencyBadgeMode.activeIntention:
        if (!_pulseController.isAnimating) {
          _pulseController.repeat(reverse: true);
        }
        _rotationController.stop();
        break;
      case AgencyBadgeMode.lessonPending:
        if (!_pulseController.isAnimating) {
          _pulseController.repeat(reverse: true);
        }
        _rotationController.stop();
        break;
      case AgencyBadgeMode.goalProgress:
        _pulseController.stop();
        if (!_rotationController.isAnimating) {
          _rotationController.repeat();
        }
        break;
      case AgencyBadgeMode.goalCompleted:
        _pulseController.stop();
        _rotationController.stop();
        _burstController.forward(from: 0.0);
        break;
      case AgencyBadgeMode.multipleItems:
        if (!_pulseController.isAnimating) {
          _pulseController.repeat(reverse: true);
        }
        _rotationController.stop();
        break;
    }
  }

  Color _getBadgeColor(AgencyBadgeMode mode, bool isDark) {
    const purple = Color(0xFFB8A1EA); // Primary accent
    const amber = Color(0xFFF59E0B); // Attention
    const emerald = Color(0xFF10B981); // Success
    
    switch (mode) {
      case AgencyBadgeMode.none:
        return Colors.transparent;
      case AgencyBadgeMode.activeIntention:
        return isDark ? purple.withValues(alpha: 0.95) : purple;
      case AgencyBadgeMode.lessonPending:
        return isDark ? amber.withValues(alpha: 0.9) : amber;
      case AgencyBadgeMode.goalProgress:
        return isDark ? purple.withValues(alpha: 0.85) : purple;
      case AgencyBadgeMode.goalCompleted:
        return isDark ? emerald.withValues(alpha: 1.0) : emerald;
      case AgencyBadgeMode.multipleItems:
        return isDark ? purple.withValues(alpha: 0.9) : purple;
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final badgeState = ref.watch(agencyBadgeStateProvider);
    
    // Update animations when mode changes
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _updateAnimations(badgeState.mode);
    });
    
    if (!badgeState.isVisible) {
      return const SizedBox.shrink();
    }
    
    final badgeColor = _getBadgeColor(badgeState.mode, isDark);
    final tooltipMessage = _getTooltipMessage(badgeState);
    
    return Tooltip(
      message: tooltipMessage,
      preferBelow: false,
      verticalOffset: 8,
      waitDuration: const Duration(milliseconds: 500),
      child: GestureDetector(
        onTap: widget.onTap,
        child: AnimatedBuilder(
          animation: Listenable.merge([
            _pulseController,
            _rotationController,
            _burstController,
          ]),
          builder: (context, child) {
            return _buildBadgeForMode(
              badgeState.mode,
              badgeColor,
              isDark,
              badgeState,
            );
          },
        ),
      ),
    );
  }

  String _getTooltipMessage(AgencyBadgeState state) {
    switch (state.mode) {
      case AgencyBadgeMode.none:
        return '';
      case AgencyBadgeMode.activeIntention:
        return state.intentionSummary?.isNotEmpty == true
          ? 'Active: ${state.intentionSummary}'
          : 'Active intention';
      case AgencyBadgeMode.lessonPending:
        final count = state.pendingCount;
        return count > 1
          ? '$count lessons ready to review'
          : 'New lesson ready to review';
      case AgencyBadgeMode.goalProgress:
        final percent = (state.intensity * 100).round();
        final goalName = state.metadata['goalName'] as String?;
        return goalName?.isNotEmpty == true
          ? '$goalName: $percent%'
          : 'Goal in progress: $percent%';
      case AgencyBadgeMode.goalCompleted:
        final goalName = state.metadata['goalName'] as String?;
        return goalName?.isNotEmpty == true
          ? 'Completed: $goalName'
          : 'Goal completed!';
      case AgencyBadgeMode.multipleItems:
        return state.intentionSummary?.isNotEmpty == true
          ? '${state.pendingCount} items: ${state.intentionSummary}'
          : '${state.pendingCount} pending items';
    }
  }

  Widget _buildBadgeForMode(
    AgencyBadgeMode mode,
    Color color,
    bool isDark,
    AgencyBadgeState state,
  ) {
    switch (mode) {
      case AgencyBadgeMode.none:
        return const SizedBox.shrink();
        
      case AgencyBadgeMode.activeIntention:
      case AgencyBadgeMode.lessonPending:
        return _buildDotBadge(color, isDark, state.intensity);
        
      case AgencyBadgeMode.goalProgress:
        return _buildProgressRing(color, isDark, state.intensity);
        
      case AgencyBadgeMode.goalCompleted:
        return _buildBurstBadge(color, isDark);
        
      case AgencyBadgeMode.multipleItems:
        return _buildCountBadge(color, isDark, state.pendingCount);
    }
  }

  Widget _buildDotBadge(Color color, bool isDark, double intensity) {
    final scale = _pulseAnimation.value;
    final size = 12.0 * scale;
    
    return Semantics(
      label: 'Agency status indicator',
      button: true,
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          color: color,
          shape: BoxShape.circle,
          border: Border.all(
            color: isDark 
              ? Colors.white.withValues(alpha: 0.2)
              : Colors.white.withValues(alpha: 0.4),
            width: 1.5,
          ),
          boxShadow: isDark
            ? null // No shadows in dark mode per design principles
            : [
                BoxShadow(
                  color: color.withValues(alpha: 0.3),
                  blurRadius: 16,
                  spreadRadius: 4,
                ),
              ],
        ),
      ),
    );
  }

  Widget _buildProgressRing(Color color, bool isDark, double progress) {
    final progressPercent = (progress * 100).round();
    return Semantics(
      label: 'Goal $progressPercent% complete',
      button: true,
      child: CustomPaint(
        size: const Size(14, 14),
        painter: _ProgressRingPainter(
          progress: progress,
          color: color,
          rotation: _rotationAnimation.value,
          isDark: isDark,
        ),
      ),
    );
  }

  Widget _buildBurstBadge(Color color, bool isDark) {
    final burstValue = _burstAnimation.value;
    final scale = 1.0 + (burstValue * 0.5);
    final opacity = 1.0 - burstValue;
    
    return Semantics(
      label: 'Goal completed',
      child: Transform.scale(
        scale: scale,
        child: Opacity(
          opacity: opacity,
          child: Container(
            width: 14,
            height: 14,
            decoration: BoxDecoration(
              color: color.withValues(alpha: opacity),
              shape: BoxShape.circle,
              border: isDark
                ? Border.all(
                    color: Colors.white.withValues(alpha: opacity * 0.3),
                    width: 1.5,
                  )
                : null,
              boxShadow: isDark
                ? null // No shadows in dark mode
                : [
                    BoxShadow(
                      color: color.withValues(alpha: opacity * 0.6),
                      blurRadius: 20 * burstValue,
                      spreadRadius: 10 * burstValue,
                    ),
                  ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildCountBadge(Color color, bool isDark, int count) {
    final scale = _pulseAnimation.value;
    
    return Semantics(
      label: '$count pending agency items',
      button: true,
      child: Transform.scale(
        scale: scale,
        child: Container(
          constraints: const BoxConstraints(
            minWidth: 16,
            minHeight: 16,
          ),
          padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
              color: isDark 
                ? Colors.white.withValues(alpha: 0.2)
                : Colors.white.withValues(alpha: 0.4),
              width: 1.5,
            ),
            boxShadow: isDark
              ? null // No shadows in dark mode per design principles
              : [
                  BoxShadow(
                    color: color.withValues(alpha: 0.3),
                    blurRadius: 16,
                    spreadRadius: 4,
                  ),
                ],
          ),
          child: Text(
            count > 99 ? '99+' : count.toString(),
            style: const TextStyle(
              color: Colors.white,
              fontSize: 11, // Adjusted to match typography scale
              fontWeight: FontWeight.w600,
              height: 1.0,
            ),
            textAlign: TextAlign.center,
          ),
        ),
      ),
    );
  }
}

/// Custom painter for progress ring
class _ProgressRingPainter extends CustomPainter {
  final double progress;
  final Color color;
  final double rotation;
  final bool isDark;
  
  _ProgressRingPainter({
    required this.progress,
    required this.color,
    required this.rotation,
    required this.isDark,
  });
  
  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.width / 2;
    
    // Background circle
    final bgPaint = Paint()
      ..color = isDark 
        ? Colors.white.withValues(alpha: 0.1)
        : Colors.black.withValues(alpha: 0.1)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.0;
    
    canvas.drawCircle(center, radius - 1, bgPaint);
    
    // Progress arc with rotation
    final progressPaint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.0
      ..strokeCap = StrokeCap.round;
    
    final startAngle = -math.pi / 2 + (rotation * 2 * math.pi);
    final sweepAngle = progress * 2 * math.pi;
    
    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius - 1),
      startAngle,
      sweepAngle,
      false,
      progressPaint,
    );
    
    // Shimmer effect at progress end
    if (progress > 0) {
      final shimmerAngle = startAngle + sweepAngle;
      final shimmerX = center.dx + (radius - 1) * math.cos(shimmerAngle);
      final shimmerY = center.dy + (radius - 1) * math.sin(shimmerAngle);
      
      final shimmerPaint = Paint()
        ..color = color.withValues(alpha: 0.8)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 2);
      
      canvas.drawCircle(Offset(shimmerX, shimmerY), 2, shimmerPaint);
    }
  }
  
  @override
  bool shouldRepaint(_ProgressRingPainter oldDelegate) {
    return oldDelegate.progress != progress ||
           oldDelegate.rotation != rotation ||
           oldDelegate.color != color;
  }
}
