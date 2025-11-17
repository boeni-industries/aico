import 'package:flutter/material.dart';

/// Environmental background with radial gradient and avatar mood glow
/// 
/// Provides the immersive atmospheric layer for the home screen with:
/// - Rich depth gradient (purple-blue tones for glassmorphism)
/// - Localized avatar mood glow (subtle atmospheric hint)
/// - Animated transitions via external controller
class HomeBackground extends StatelessWidget {
  final AnimationController animationController;
  final Color moodColor;
  final Widget child;

  const HomeBackground({
    super.key,
    required this.animationController,
    required this.moodColor,
    required this.child,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return AnimatedBuilder(
      animation: animationController,
      builder: (context, _) {
        return Container(
          decoration: BoxDecoration(
            gradient: RadialGradient(
              center: const Alignment(0, -0.4),
              radius: 1.2,
              colors: isDark
                  ? const [
                      // Rich center - purple-blue for depth
                      Color(0xFF2D3B5C),
                      // Mid-range - blue-grey transition
                      Color(0xFF1F2A3E),
                      // Outer - deep blue-grey
                      Color(0xFF151D2A),
                      // Edges - darkest
                      Color(0xFF0F1419),
                    ]
                  : const [
                      // Light mode: soft purple-blue pastels
                      Color(0xFFF0F0FF),
                      Color(0xFFE8ECFA),
                      Color(0xFFDDE2F0),
                      Color(0xFFD5DAE8),
                    ],
              stops: const [0.0, 0.35, 0.7, 1.0],
            ),
          ),
          child: Stack(
            children: [
              // Localized avatar mood glow - subtle atmospheric hint
              Positioned(
                top: 0,
                left: 0,
                right: 0,
                height: 350,
                child: IgnorePointer(
                  child: Container(
                    decoration: BoxDecoration(
                      gradient: RadialGradient(
                        center: const Alignment(0, -0.25),
                        radius: 0.5,
                        colors: [
                          moodColor.withValues(alpha: 0.08),
                          moodColor.withValues(alpha: 0.04),
                          moodColor.withValues(alpha: 0.015),
                          Colors.transparent,
                        ],
                        stops: const [0.0, 0.35, 0.65, 1.0],
                      ),
                    ),
                  ),
                ),
              ),
              // Main content
              child,
            ],
          ),
        );
      },
    );
  }
}
