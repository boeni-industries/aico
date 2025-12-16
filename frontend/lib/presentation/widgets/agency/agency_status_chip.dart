import 'package:aico_frontend/presentation/providers/agency_state_provider.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Modern inline status chip for agency state
/// Displays clear, contextual information with icon + text
/// Positioned below avatar, non-overlapping, following 2024 UX best practices
class AgencyStatusChip extends ConsumerStatefulWidget {
  final VoidCallback? onTap;
  
  const AgencyStatusChip({
    super.key,
    this.onTap,
  });

  @override
  ConsumerState<AgencyStatusChip> createState() => _AgencyStatusChipState();
}

class _AgencyStatusChipState extends ConsumerState<AgencyStatusChip>
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
      begin: 0.95,
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
    
    final chipData = _getChipData(badgeState, isDark);
    
    return AnimatedBuilder(
      animation: _pulseAnimation,
      builder: (context, child) {
        return Transform.scale(
          scale: chipData.shouldPulse ? _pulseAnimation.value : 1.0,
          child: GestureDetector(
            onTap: widget.onTap,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              decoration: BoxDecoration(
                color: isDark
                  ? chipData.color.withValues(alpha: 0.15)
                  : chipData.color.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                  color: isDark
                    ? chipData.color.withValues(alpha: 0.4)
                    : chipData.color.withValues(alpha: 0.3),
                  width: 1.5,
                ),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  // Icon
                  Icon(
                    chipData.icon,
                    size: 16,
                    color: isDark
                      ? chipData.color.withValues(alpha: 0.9)
                      : chipData.color,
                  ),
                  const SizedBox(width: 8),
                  // Text
                  Flexible(
                    child: Text(
                      chipData.label,
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: isDark
                          ? chipData.color.withValues(alpha: 0.95)
                          : chipData.color.withValues(alpha: 0.9),
                        letterSpacing: 0.2,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  // Count badge if applicable
                  if (chipData.count != null) ...[
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: chipData.color,
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Text(
                        chipData.count!,
                        style: const TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                          color: Colors.white,
                          height: 1.2,
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  _ChipData _getChipData(AgencyBadgeState state, bool isDark) {
    const purple = Color(0xFFB8A1EA);
    const amber = Color(0xFFF59E0B);
    const emerald = Color(0xFF10B981);
    
    switch (state.mode) {
      case AgencyBadgeMode.none:
        return _ChipData(
          icon: Icons.circle,
          label: '',
          color: Colors.transparent,
          shouldPulse: false,
        );
        
      case AgencyBadgeMode.activeIntention:
        final summary = state.intentionSummary ?? 'Active intention';
        return _ChipData(
          icon: Icons.psychology_outlined,
          label: summary,
          color: purple,
          shouldPulse: true,
        );
        
      case AgencyBadgeMode.lessonPending:
        final count = state.pendingCount;
        final label = count > 1 ? 'Lessons ready' : 'Lesson ready';
        return _ChipData(
          icon: Icons.school_outlined,
          label: label,
          color: amber,
          count: count > 1 ? count.toString() : null,
          shouldPulse: true,
        );
        
      case AgencyBadgeMode.goalProgress:
        final percent = (state.intensity * 100).round();
        final goalName = state.metadata['goalName'] as String?;
        final label = goalName ?? 'Goal in progress';
        return _ChipData(
          icon: Icons.track_changes_outlined,
          label: '$label: $percent%',
          color: purple,
          shouldPulse: false,
        );
        
      case AgencyBadgeMode.goalCompleted:
        final goalName = state.metadata['goalName'] as String?;
        final label = goalName != null ? 'Completed: $goalName' : 'Goal completed!';
        return _ChipData(
          icon: Icons.check_circle_outline,
          label: label,
          color: emerald,
          shouldPulse: false,
        );
        
      case AgencyBadgeMode.multipleItems:
        return _ChipData(
          icon: Icons.notifications_outlined,
          label: 'Agency updates',
          color: purple,
          count: state.pendingCount.toString(),
          shouldPulse: true,
        );
    }
  }
}

class _ChipData {
  final IconData icon;
  final String label;
  final Color color;
  final String? count;
  final bool shouldPulse;

  _ChipData({
    required this.icon,
    required this.label,
    required this.color,
    this.count,
    required this.shouldPulse,
  });
}
