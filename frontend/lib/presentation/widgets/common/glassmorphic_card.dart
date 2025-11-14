import 'package:flutter/material.dart';

/// Glassmorphic card with hover effects and modern depth styling
class GlassmorphicCard extends StatefulWidget {
  final Widget child;
  final VoidCallback? onTap;
  final bool enabled;
  final EdgeInsets? padding;
  final double? width;
  final double? height;
  
  const GlassmorphicCard({
    super.key,
    required this.child,
    this.onTap,
    this.enabled = true,
    this.padding,
    this.width,
    this.height,
  });

  @override
  State<GlassmorphicCard> createState() => _GlassmorphicCardState();
}

class _GlassmorphicCardState extends State<GlassmorphicCard> with SingleTickerProviderStateMixin {
  late AnimationController _hoverController;
  late Animation<double> _hoverAnimation;
  bool _isHovered = false;
  bool _isPressed = false;

  @override
  void initState() {
    super.initState();
    _hoverController = AnimationController(
      duration: const Duration(milliseconds: 150),
      vsync: this,
    );
    _hoverAnimation = CurvedAnimation(
      parent: _hoverController,
      curve: Curves.easeOut,
    );
  }

  @override
  void dispose() {
    _hoverController.dispose();
    super.dispose();
  }

  void _onHoverStart() {
    if (!widget.enabled) return;
    setState(() => _isHovered = true);
    _hoverController.forward();
  }

  void _onHoverEnd() {
    setState(() => _isHovered = false);
    _hoverController.reverse();
  }

  void _onTapDown() {
    if (!widget.enabled) return;
    setState(() => _isPressed = true);
  }

  void _onTapUp() {
    setState(() => _isPressed = false);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final accentColor = theme.colorScheme.primary;

    return MouseRegion(
      onEnter: (_) => _onHoverStart(),
      onExit: (_) => _onHoverEnd(),
      cursor: widget.enabled ? SystemMouseCursors.click : SystemMouseCursors.basic,
      child: GestureDetector(
        onTapDown: (_) => _onTapDown(),
        onTapUp: (_) => _onTapUp(),
        onTapCancel: () => _onTapUp(),
        onTap: widget.enabled ? widget.onTap : null,
        child: AnimatedBuilder(
          animation: _hoverAnimation,
          builder: (context, child) {
            // Subtle scale on hover
            final scale = _isPressed ? 0.98 : (_isHovered ? 1.02 : 1.0);
            
            return Transform.scale(
              scale: scale,
              child: Container(
              width: widget.width,
              height: widget.height,
              padding: widget.padding ?? const EdgeInsets.all(16),
              decoration: BoxDecoration(
                // Background opacity changes on hover/press
                color: _isPressed
                    ? (isDark ? accentColor.withValues(alpha: 0.15) : accentColor.withValues(alpha: 0.12))
                    : _isHovered
                        ? (isDark ? accentColor.withValues(alpha: 0.12) : accentColor.withValues(alpha: 0.10))
                        : (isDark ? accentColor.withValues(alpha: 0.08) : accentColor.withValues(alpha: 0.06)),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(
                  color: Colors.white.withValues(
                    alpha: _isPressed ? 0.25 : _isHovered ? 0.20 : 0.15,
                  ),
                  width: 1.5,
                ),
                boxShadow: _isPressed
                    ? [
                        // Compressed shadow when pressed
                        BoxShadow(
                          color: accentColor.withValues(alpha: 0.15),
                          blurRadius: 4,
                          offset: const Offset(0, 1),
                        ),
                      ]
                    : _isHovered
                        ? [
                            // Elevated shadow on hover
                            BoxShadow(
                              color: Colors.black.withValues(alpha: 0.12),
                              blurRadius: 12,
                              offset: const Offset(0, 4),
                            ),
                            BoxShadow(
                              color: accentColor.withValues(alpha: 0.25),
                              blurRadius: 20,
                              spreadRadius: 0,
                            ),
                          ]
                        : [
                            // Default shadow
                            BoxShadow(
                              color: Colors.black.withValues(alpha: 0.08),
                              blurRadius: 8,
                              offset: const Offset(0, 2),
                            ),
                            BoxShadow(
                              color: accentColor.withValues(alpha: 0.12),
                              blurRadius: 12,
                              spreadRadius: 0,
                            ),
                          ],
                // Gradient overlay for depth
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [
                    Colors.white.withValues(alpha: 0.08),
                    Colors.transparent,
                    Colors.black.withValues(alpha: 0.05),
                  ],
                  stops: const [0.0, 0.5, 1.0],
                ),
              ),
                child: widget.child,
              ),
            );
          },
        ),
      ),
    );
  }
}
