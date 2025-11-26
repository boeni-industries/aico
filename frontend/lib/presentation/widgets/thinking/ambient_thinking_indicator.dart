import 'package:flutter/material.dart';

/// Ambient thinking indicator for collapsed right drawer state
/// Centered gradient line with sharp horizontal glow that pulses during thinking
/// Glassmorphic badge centered showing thought count
class AmbientThinkingIndicator extends StatefulWidget {
  final bool isStreaming;
  final int thoughtCount;
  final VoidCallback onTap;
  final VoidCallback? onHoverStart;
  final VoidCallback? onHoverEnd;

  const AmbientThinkingIndicator({
    super.key,
    required this.isStreaming,
    required this.thoughtCount,
    required this.onTap,
    this.onHoverStart,
    this.onHoverEnd,
  });

  @override
  State<AmbientThinkingIndicator> createState() => _AmbientThinkingIndicatorState();
}

class _AmbientThinkingIndicatorState extends State<AmbientThinkingIndicator>
    with SingleTickerProviderStateMixin {
  late AnimationController _glowController;
  late Animation<double> _glowAnimation;

  @override
  void initState() {
    super.initState();

    // Sharp pulsing glow animation for thinking state (2s cycle)
    _glowController = AnimationController(
      duration: const Duration(milliseconds: 2000),
      vsync: this,
    );
    _glowAnimation = Tween<double>(begin: 0.3, end: 1.0).animate(
      CurvedAnimation(parent: _glowController, curve: Curves.easeInOut),
    );

    // Start animation if streaming
    if (widget.isStreaming) {
      _glowController.repeat(reverse: true);
    }
  }

  @override
  void didUpdateWidget(AmbientThinkingIndicator oldWidget) {
    super.didUpdateWidget(oldWidget);

    // Handle streaming state changes with mounted check
    if (widget.isStreaming && !oldWidget.isStreaming) {
      // Start pulsing when thinking stream starts
      if (mounted) {
        _glowController.repeat(reverse: true);
      }
    } else if (!widget.isStreaming && oldWidget.isStreaming) {
      // Stop pulsing when thinking stream ends
      if (mounted) {
        _glowController.stop();
        _glowController.value = 0.0; // Reset to begin value (0.3)
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

    return MouseRegion(
      onEnter: (_) => widget.onHoverStart?.call(),
      onExit: (_) => widget.onHoverEnd?.call(),
      child: GestureDetector(
        onTap: widget.onTap,
        child: Semantics(
          label: 'Right drawer',
          hint: widget.isStreaming
              ? 'AICO is actively thinking. Press to view reasoning and emotions.'
              : widget.thoughtCount > 0
                  ? 'AICO has ${widget.thoughtCount} thoughts. Press to view thinking and emotions.'
                  : 'Press to view AICO\'s emotional journey.',
          button: true,
          child: SizedBox(
            width: 72, // Full drawer width
            height: double.infinity,
            child: Stack(
              alignment: Alignment.center,
              children: [
                // Centered gradient line with sharp horizontal glow
                Center(
                  child: _buildCenteredGradientLine(purpleAccent, isDark),
                ),

                // Centered badge with glassmorphism
                if (widget.thoughtCount > 0)
                  Center(
                    child: _buildGlassmorphicBadge(purpleAccent, isDark),
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
            // Always use the animation value, but it will be static when not streaming
            final glowIntensity = _glowAnimation.value;
            
            // Visual symmetry: match the top spacing
            // Top has SafeArea + rounded corner, so bottom should match
            const topMargin = 50.0; 
            const bottomMargin = 50.0; // Match top for visual symmetry
            
            return Container(
              width: 4, // Thin centered line
              height: constraints.maxHeight - topMargin - bottomMargin,
              margin: const EdgeInsets.only(top: topMargin, bottom: bottomMargin),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(2),
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [
                    purpleAccent.withValues(alpha: 0.0), // Fade out at top
                    purpleAccent.withValues(alpha: 0.4),
                    purpleAccent.withValues(alpha: 0.6), // Full opacity in center
                    purpleAccent.withValues(alpha: 0.4),
                    purpleAccent.withValues(alpha: 0.0), // Fade out at bottom
                  ],
                  stops: const [0.0, 0.2, 0.5, 0.8, 1.0],
                ),
                boxShadow: [
                  // Sharp horizontal glow that pulses
                  BoxShadow(
                    color: purpleAccent.withValues(alpha: 0.3 * glowIntensity),
                    blurRadius: 40 * glowIntensity,
                    spreadRadius: 15 * glowIntensity, // Restored spread (reduced from 20 to be safer)
                    offset: Offset.zero,
                  ),
                  BoxShadow(
                    color: purpleAccent.withValues(alpha: 0.5 * glowIntensity),
                    blurRadius: 20 * glowIntensity,
                    spreadRadius: 8 * glowIntensity, // Restored spread (reduced from 10 to be safer)
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

  Widget _buildGlassmorphicBadge(Color purpleAccent, bool isDark) {
    // Match chevron size and style exactly
    return Container(
      width: 32,
      height: 32,
      decoration: BoxDecoration(
        color: isDark
            ? Colors.white.withValues(alpha: 0.06)
            : Colors.white.withValues(alpha: 0.8),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: isDark
              ? Colors.white.withValues(alpha: 0.1)
              : Colors.white.withValues(alpha: 0.3),
          width: 1,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: isDark ? 0.3 : 0.1),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Center(
        child: Text(
          '${widget.thoughtCount}',
          style: TextStyle(
            color: purpleAccent.withValues(alpha: 0.6),
            fontSize: 12,
            fontWeight: FontWeight.w500,
            letterSpacing: -0.1,
          ),
        ),
      ),
    );
  }
}
