import 'dart:ui';

import 'package:flutter/material.dart';

/// Elegant glassmorphic toast notification that fades in and out
/// Replaces ugly snackbars with beautiful, subtle feedback
class GlassmorphicToast extends StatefulWidget {
  final String message;
  final IconData? icon;
  final Color accentColor;
  final Duration duration;

  const GlassmorphicToast({
    super.key,
    required this.message,
    this.icon,
    required this.accentColor,
    this.duration = const Duration(seconds: 2),
  });

  /// Show toast as overlay
  static void show(
    BuildContext context, {
    required String message,
    IconData? icon,
    required Color accentColor,
    Duration duration = const Duration(seconds: 2),
  }) {
    final overlay = Overlay.of(context);
    final overlayEntry = OverlayEntry(
      builder: (context) => Positioned(
        bottom: 80,
        left: 0,
        right: 0,
        child: Center(
          child: GlassmorphicToast(
            message: message,
            icon: icon,
            accentColor: accentColor,
            duration: duration,
          ),
        ),
      ),
    );

    overlay.insert(overlayEntry);

    // Auto-remove after duration
    Future.delayed(duration + const Duration(milliseconds: 500), () {
      overlayEntry.remove();
    });
  }

  @override
  State<GlassmorphicToast> createState() => _GlassmorphicToastState();
}

class _GlassmorphicToastState extends State<GlassmorphicToast>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _fadeAnimation;
  late Animation<double> _slideAnimation;

  @override
  void initState() {
    super.initState();

    _controller = AnimationController(
      duration: const Duration(milliseconds: 300),
      vsync: this,
    );

    _fadeAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeOut),
    );

    _slideAnimation = Tween<double>(begin: 20.0, end: 0.0).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeOutCubic),
    );

    // Fade in
    _controller.forward();

    // Fade out before duration ends
    Future.delayed(widget.duration - const Duration(milliseconds: 300), () {
      if (mounted) {
        _controller.reverse();
      }
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        return Opacity(
          opacity: _fadeAnimation.value,
          child: Transform.translate(
            offset: Offset(0, _slideAnimation.value),
            child: child,
          ),
        );
      },
      child: ClipRRect(
        borderRadius: BorderRadius.circular(24),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 20, sigmaY: 20),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
            decoration: BoxDecoration(
              color: isDark
                  ? Colors.white.withValues(alpha: 0.08)
                  : Colors.white.withValues(alpha: 0.75),
              borderRadius: BorderRadius.circular(24),
              border: Border.all(
                color: isDark
                    ? Colors.white.withValues(alpha: 0.15)
                    : Colors.white.withValues(alpha: 0.4),
                width: 1.5,
              ),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: isDark ? 0.3 : 0.08),
                  blurRadius: 20,
                  offset: const Offset(0, 8),
                  spreadRadius: -4,
                ),
              ],
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (widget.icon != null) ...[
                  Icon(
                    widget.icon,
                    size: 20,
                    color: widget.accentColor,
                  ),
                  const SizedBox(width: 12),
                ],
                Text(
                  widget.message,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    fontWeight: FontWeight.w500,
                    color: theme.colorScheme.onSurface.withValues(alpha: 0.9),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
