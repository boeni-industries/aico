import 'dart:math' as math;

import 'package:aico_frontend/presentation/providers/agency_state_provider.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Agency ring segment that displays around the avatar
/// Uses safe animations (glow/opacity only) to avoid motion sensitivity issues
class AgencyRingSegment extends ConsumerStatefulWidget {
  final double avatarSize;
  
  const AgencyRingSegment({
    super.key,
    required this.avatarSize,
  });

  @override
  ConsumerState<AgencyRingSegment> createState() => _AgencyRingSegmentState();
}

class _AgencyRingSegmentState extends ConsumerState<AgencyRingSegment>
    with SingleTickerProviderStateMixin {
  late AnimationController _glowController;
  late Animation<double> _glowAnimation;

  @override
  void initState() {
    super.initState();
    
    _glowController = AnimationController(
      duration: const Duration(seconds: 3),
      vsync: this,
    );
    
    _glowAnimation = Tween<double>(
      begin: 0.6,
      end: 1.0,
    ).animate(CurvedAnimation(
      parent: _glowController,
      curve: Curves.easeInOut,
    ));
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    
    // Respect prefers-reduced-motion accessibility setting
    final disableAnimations = MediaQuery.of(context).disableAnimations;
    
    if (disableAnimations) {
      _glowController.stop();
      _glowController.value = 1.0; // Static max glow
    } else {
      if (!_glowController.isAnimating) {
        _glowController.repeat(reverse: true);
      }
    }
  }

  @override
  void dispose() {
    _glowController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final agencyState = ref.watch(agencyBadgeStateProvider);
    
    // Don't render if no agency activity
    if (!agencyState.isVisible) {
      return const SizedBox.shrink();
    }

    return AnimatedBuilder(
      animation: _glowAnimation,
      builder: (context, child) {
        final arcLength = _calculateArcLength(agencyState);
        final color = _getColor(agencyState);
        final baseGlowIntensity = _getGlowIntensity(agencyState);
        final shouldPulse = _shouldPulse(agencyState);
        
        // Apply animation only if pulsing is needed
        final glowIntensity = shouldPulse 
            ? _glowAnimation.value * baseGlowIntensity
            : baseGlowIntensity;

        return CustomPaint(
          size: Size(widget.avatarSize, widget.avatarSize),
          painter: _AgencyRingPainter(
            arcLength: arcLength,
            color: color,
            glowIntensity: glowIntensity,
          ),
        );
      },
    );
  }

  /// Calculate arc length (0.0 to 0.95) based on agency activity
  double _calculateArcLength(AgencyBadgeState state) {
    int activeCount = 0;
    
    // Count active items
    if (state.mode == AgencyBadgeMode.activeIntention) activeCount++;
    if (state.mode == AgencyBadgeMode.goalProgress) activeCount++;
    if (state.mode == AgencyBadgeMode.lessonPending) {
      activeCount += math.min(state.pendingCount, 2);
    }
    if (state.mode == AgencyBadgeMode.goalCompleted) activeCount = 3;
    if (state.mode == AgencyBadgeMode.multipleItems) activeCount = 3;
    
    // Map 0-3+ items to 0-95% of circle (leave 5% gap)
    if (activeCount == 0) return 0.0;
    if (activeCount == 1) return 0.33;
    if (activeCount == 2) return 0.66;
    return 0.95; // 3+ items
  }

  /// Get color based on agency state priority
  Color _getColor(AgencyBadgeState state) {
    const purple = Color(0xFFB8A1EA);
    const amber = Color(0xFFF59E0B);
    const emerald = Color(0xFF10B981);
    
    // Priority: Attention > Success > Activity
    if (state.mode == AgencyBadgeMode.lessonPending) return amber;
    if (state.mode == AgencyBadgeMode.goalCompleted) return emerald;
    return purple; // Default for active states
  }

  /// Get base glow intensity (before animation)
  double _getGlowIntensity(AgencyBadgeState state) {
    if (state.mode == AgencyBadgeMode.lessonPending) {
      return 0.8; // Strong glow for attention
    }
    if (state.mode == AgencyBadgeMode.goalCompleted) {
      return 0.7; // Strong glow for success
    }
    return 0.4; // Subtle glow for normal activity
  }

  /// Determine if glow should pulse
  bool _shouldPulse(AgencyBadgeState state) {
    // Only pulse for attention-needed states
    return state.mode == AgencyBadgeMode.lessonPending ||
           state.mode == AgencyBadgeMode.goalCompleted;
  }
}

/// Custom painter for the agency ring segment
class _AgencyRingPainter extends CustomPainter {
  final double arcLength;
  final Color color;
  final double glowIntensity;

  _AgencyRingPainter({
    required this.arcLength,
    required this.color,
    required this.glowIntensity,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (arcLength == 0.0) return;

    // Match radial gradient center: Alignment(0, -0.1) = upper body focus
    final center = Offset(size.width / 2, size.height * 0.45);
    final radius = size.width / 2 - 6; // Reduced gap for integration
    final strokeWidth = 2.5; // Thinner, more elegant
    
    final rect = Rect.fromCircle(center: center, radius: radius);
    
    // Start at top (270 degrees / -90 degrees)
    final startAngle = -math.pi / 2;
    final sweepAngle = 2 * math.pi * arcLength;

    // Draw soft glow layers (organic, integrated feel)
    if (glowIntensity > 0) {
      // Outer glow - very soft
      final outerGlowPaint = Paint()
        ..color = color.withValues(alpha: 0.08 * glowIntensity)
        ..strokeWidth = strokeWidth + 6
        ..style = PaintingStyle.stroke
        ..strokeCap = StrokeCap.round
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 8)
        ..blendMode = BlendMode.screen; // Blend with emotion glow
      
      canvas.drawArc(rect, startAngle, sweepAngle, false, outerGlowPaint);
      
      // Mid glow
      final midGlowPaint = Paint()
        ..color = color.withValues(alpha: 0.15 * glowIntensity)
        ..strokeWidth = strokeWidth + 3
        ..style = PaintingStyle.stroke
        ..strokeCap = StrokeCap.round
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 4)
        ..blendMode = BlendMode.screen;
      
      canvas.drawArc(rect, startAngle, sweepAngle, false, midGlowPaint);
    }

    // Draw main ring with uniform opacity (no confusing brightness variation)
    final mainPaint = Paint()
      ..color = color.withValues(alpha: 0.5)
      ..strokeWidth = strokeWidth
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 1.5)
      ..blendMode = BlendMode.screen;
    
    canvas.drawArc(rect, startAngle, sweepAngle, false, mainPaint);
  }

  @override
  bool shouldRepaint(_AgencyRingPainter oldDelegate) {
    return oldDelegate.arcLength != arcLength ||
           oldDelegate.color != color ||
           oldDelegate.glowIntensity != glowIntensity;
  }
}
