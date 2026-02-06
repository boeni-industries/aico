import 'package:aico_frontend/presentation/providers/proactive_state_provider.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Ambient indicator for collapsed right drawer
/// Vertical pill showing thinking count and notification count
class AmbientDrawerIndicator extends ConsumerStatefulWidget {
  final bool isStreaming;
  final int thoughtCount;
  final VoidCallback onTap;
  final VoidCallback? onHoverStart;
  final VoidCallback? onHoverEnd;

  const AmbientDrawerIndicator({
    super.key,
    required this.isStreaming,
    required this.thoughtCount,
    required this.onTap,
    this.onHoverStart,
    this.onHoverEnd,
  });

  @override
  ConsumerState<AmbientDrawerIndicator> createState() => _AmbientDrawerIndicatorState();
}

class _AmbientDrawerIndicatorState extends ConsumerState<AmbientDrawerIndicator>
    with SingleTickerProviderStateMixin {
  late AnimationController _glowController;
  late Animation<double> _glowAnimation;

  @override
  void initState() {
    super.initState();

    _glowController = AnimationController(
      duration: const Duration(milliseconds: 2000),
      vsync: this,
    );
    _glowAnimation = Tween<double>(begin: 0.3, end: 1.0).animate(
      CurvedAnimation(parent: _glowController, curve: Curves.easeInOut),
    );

    if (widget.isStreaming) {
      _glowController.repeat(reverse: true);
    }
  }

  @override
  void didUpdateWidget(AmbientDrawerIndicator oldWidget) {
    super.didUpdateWidget(oldWidget);

    if (widget.isStreaming && !oldWidget.isStreaming) {
      if (mounted) {
        _glowController.repeat(reverse: true);
      }
    } else if (!widget.isStreaming && oldWidget.isStreaming) {
      if (mounted) {
        _glowController.stop();
        _glowController.value = 0.0;
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
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final purpleAccent = isDark ? const Color(0xFFB9A7E6) : const Color(0xFFB8A1EA);
    final proactiveState = ref.watch(proactiveStateProvider);
    final notificationCount = proactiveState.pendingInitiations.length;

    return MouseRegion(
      onEnter: (_) => widget.onHoverStart?.call(),
      onExit: (_) => widget.onHoverEnd?.call(),
      child: GestureDetector(
        onTap: widget.onTap,
        child: Semantics(
          label: 'Right drawer',
          hint: widget.isStreaming
              ? 'AICO is actively thinking. Press to view.'
              : 'Press to view thinking, emotions, and notifications.',
          button: true,
          child: SizedBox(
            width: 72,
            height: double.infinity,
            child: Stack(
              alignment: Alignment.center,
              children: [
                // Centered gradient line
                Center(
                  child: _buildCenteredGradientLine(purpleAccent, isDark),
                ),

                // Vertical pill with both counts
                Center(
                  child: _buildVerticalPill(purpleAccent, isDark, notificationCount),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildCenteredGradientLine(Color purpleAccent, bool isDark) {
    return LayoutBuilder(
      builder: (context, constraints) {
        return AnimatedBuilder(
          animation: _glowAnimation,
          builder: (context, child) {
            final glowIntensity = _glowAnimation.value;
            
            const topMargin = 50.0; 
            const bottomMargin = 50.0;
            
            return Container(
              width: 4,
              height: constraints.maxHeight - topMargin - bottomMargin,
              margin: const EdgeInsets.only(top: topMargin, bottom: bottomMargin),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(2),
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [
                    purpleAccent.withValues(alpha: 0.0),
                    purpleAccent.withValues(alpha: 0.4),
                    purpleAccent.withValues(alpha: 0.6),
                    purpleAccent.withValues(alpha: 0.4),
                    purpleAccent.withValues(alpha: 0.0),
                  ],
                  stops: const [0.0, 0.2, 0.5, 0.8, 1.0],
                ),
                boxShadow: [
                  BoxShadow(
                    color: purpleAccent.withValues(alpha: 0.3 * glowIntensity),
                    blurRadius: 40 * glowIntensity,
                    spreadRadius: 15 * glowIntensity,
                    offset: Offset.zero,
                  ),
                  BoxShadow(
                    color: purpleAccent.withValues(alpha: 0.5 * glowIntensity),
                    blurRadius: 20 * glowIntensity,
                    spreadRadius: 8 * glowIntensity,
                    offset: Offset.zero,
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  Widget _buildVerticalPill(Color purpleAccent, bool isDark, int notificationCount) {
    final hasThoughts = widget.thoughtCount > 0;
    final hasNotifications = notificationCount > 0;
    
    if (!hasThoughts && !hasNotifications) {
      return const SizedBox.shrink();
    }

    return Container(
      width: 48,
      padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 8),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: isDark
              ? [
                  Colors.white.withValues(alpha: 0.10),
                  Colors.white.withValues(alpha: 0.06),
                ]
              : [
                  Colors.white.withValues(alpha: 0.95),
                  Colors.white.withValues(alpha: 0.85),
                ],
        ),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(
          color: isDark
              ? Colors.white.withValues(alpha: 0.18)
              : Colors.white.withValues(alpha: 0.5),
          width: 1.5,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: isDark ? 0.5 : 0.08),
            blurRadius: 16,
            offset: const Offset(0, 4),
            spreadRadius: -2,
          ),
          BoxShadow(
            color: purpleAccent.withValues(alpha: 0.2),
            blurRadius: 24,
            spreadRadius: -4,
          ),
        ],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Thinking count
          if (hasThoughts) ...[
            Container(
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: purpleAccent.withValues(alpha: 0.12),
                shape: BoxShape.circle,
              ),
              child: Icon(
                Icons.psychology_outlined,
                size: 16,
                color: purpleAccent,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              '${widget.thoughtCount}',
              style: TextStyle(
                color: isDark ? Colors.white.withValues(alpha: 0.95) : Colors.black.withValues(alpha: 0.9),
                fontSize: 14,
                fontWeight: FontWeight.w700,
                letterSpacing: -0.3,
                height: 1.0,
              ),
            ),
          ],
          
          // Divider if both present
          if (hasThoughts && hasNotifications) ...[
            const SizedBox(height: 10),
            Container(
              width: 24,
              height: 2,
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [
                    Colors.transparent,
                    isDark
                        ? Colors.white.withValues(alpha: 0.2)
                        : Colors.black.withValues(alpha: 0.2),
                    Colors.transparent,
                  ],
                ),
                borderRadius: BorderRadius.circular(1),
              ),
            ),
            const SizedBox(height: 10),
          ],
          
          // Notification count
          if (hasNotifications) ...[
            Container(
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: purpleAccent.withValues(alpha: 0.12),
                shape: BoxShape.circle,
              ),
              child: Icon(
                Icons.chat_bubble_outline,
                size: 16,
                color: purpleAccent,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              '$notificationCount',
              style: TextStyle(
                color: isDark ? Colors.white.withValues(alpha: 0.95) : Colors.black.withValues(alpha: 0.9),
                fontSize: 14,
                fontWeight: FontWeight.w700,
                letterSpacing: -0.3,
                height: 1.0,
              ),
            ),
          ],
        ],
      ),
    );
  }
}
