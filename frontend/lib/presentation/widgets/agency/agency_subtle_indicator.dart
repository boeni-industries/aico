import 'package:aico_frontend/presentation/providers/agency_state_provider.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Subtle, non-intrusive agency indicator
/// Appears as a small pulsing dot with minimal text, only when there's something to show
/// Designed to not break immersion - blends into the UI naturally
class AgencySubtleIndicator extends ConsumerStatefulWidget {
  final VoidCallback? onTap;
  
  const AgencySubtleIndicator({
    super.key,
    this.onTap,
  });

  @override
  ConsumerState<AgencySubtleIndicator> createState() => _AgencySubtleIndicatorState();
}

class _AgencySubtleIndicatorState extends ConsumerState<AgencySubtleIndicator>
    with SingleTickerProviderStateMixin {
  late AnimationController _pulseController;
  late Animation<double> _pulseAnimation;

  @override
  void initState() {
    super.initState();
    
    _pulseController = AnimationController(
      duration: const Duration(milliseconds: 2000),
      vsync: this,
    );
    
    _pulseAnimation = Tween<double>(
      begin: 0.6,
      end: 1.0,
    ).animate(CurvedAnimation(
      parent: _pulseController,
      curve: Curves.easeInOut,
    ));
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  void _updateAnimation(AgencyBadgeMode mode) {
    switch (mode) {
      case AgencyBadgeMode.none:
        _pulseController.stop();
        break;
      case AgencyBadgeMode.activeIntention:
      case AgencyBadgeMode.lessonPending:
      case AgencyBadgeMode.multipleItems:
        if (!_pulseController.isAnimating) {
          _pulseController.repeat(reverse: true);
        }
        break;
      case AgencyBadgeMode.goalProgress:
      case AgencyBadgeMode.goalCompleted:
        _pulseController.stop();
        break;
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final badgeState = ref.watch(agencyBadgeStateProvider);
    
    // Update animations when mode changes
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _updateAnimation(badgeState.mode);
    });
    
    if (!badgeState.isVisible) {
      return const SizedBox.shrink();
    }
    
    final indicatorData = _getIndicatorData(badgeState, isDark);
    
    return AnimatedBuilder(
      animation: _pulseAnimation,
      builder: (context, child) {
        return GestureDetector(
          onTap: widget.onTap,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
            decoration: BoxDecoration(
              color: isDark
                ? Colors.white.withValues(alpha: 0.03)
                : Colors.black.withValues(alpha: 0.02),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                color: indicatorData.color.withValues(
                  alpha: indicatorData.shouldPulse 
                    ? _pulseAnimation.value * 0.3
                    : 0.2
                ),
                width: 1,
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                // Pulsing dot
                Container(
                  width: 6,
                  height: 6,
                  decoration: BoxDecoration(
                    color: indicatorData.color.withValues(
                      alpha: indicatorData.shouldPulse 
                        ? _pulseAnimation.value 
                        : 0.8
                    ),
                    shape: BoxShape.circle,
                    boxShadow: indicatorData.shouldPulse ? [
                      BoxShadow(
                        color: indicatorData.color.withValues(
                          alpha: _pulseAnimation.value * 0.4
                        ),
                        blurRadius: 4,
                        spreadRadius: 1,
                      ),
                    ] : null,
                  ),
                ),
                if (indicatorData.count != null) ...[
                  const SizedBox(width: 6),
                  Text(
                    indicatorData.count!,
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                      color: indicatorData.color.withValues(alpha: 0.8),
                    ),
                  ),
                ],
              ],
            ),
          ),
        );
      },
    );
  }

  _IndicatorData _getIndicatorData(AgencyBadgeState state, bool isDark) {
    const purple = Color(0xFFB8A1EA);
    const amber = Color(0xFFF59E0B);
    const emerald = Color(0xFF10B981);
    
    switch (state.mode) {
      case AgencyBadgeMode.none:
        return _IndicatorData(
          color: Colors.transparent,
          shouldPulse: false,
        );
        
      case AgencyBadgeMode.activeIntention:
        return _IndicatorData(
          color: purple,
          shouldPulse: true,
        );
        
      case AgencyBadgeMode.lessonPending:
        final count = state.pendingCount;
        return _IndicatorData(
          color: amber,
          count: count > 1 ? count.toString() : null,
          shouldPulse: true,
        );
        
      case AgencyBadgeMode.goalProgress:
        return _IndicatorData(
          color: purple,
          shouldPulse: false,
        );
        
      case AgencyBadgeMode.goalCompleted:
        return _IndicatorData(
          color: emerald,
          shouldPulse: false,
        );
        
      case AgencyBadgeMode.multipleItems:
        return _IndicatorData(
          color: purple,
          count: state.pendingCount.toString(),
          shouldPulse: true,
        );
    }
  }
}

class _IndicatorData {
  final Color color;
  final String? count;
  final bool shouldPulse;

  _IndicatorData({
    required this.color,
    this.count,
    required this.shouldPulse,
  });
}
