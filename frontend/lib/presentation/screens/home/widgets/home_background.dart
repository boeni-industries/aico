import 'package:flutter/material.dart';

/// Environmental background with neutral radial gradient
/// 
/// Provides the immersive atmospheric layer for the home screen with:
/// - Neutral depth gradient (blue-grey tones for glassmorphism)
/// - Animated transitions via external controller
/// - Avatar ring shows state colors directly (no background glow needed)
class HomeBackground extends StatelessWidget {
  final AnimationController animationController;
  final Widget child;

  const HomeBackground({
    super.key,
    required this.animationController,
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
                      // Neutral dark gradient - no purple tint
                      Color(0xFF1F2A3E),
                      Color(0xFF1A2332),
                      Color(0xFF151D2A),
                      Color(0xFF0F1419),
                    ]
                  : const [
                      // Neutral light gradient - no purple tint
                      Color(0xFFF5F6FA),
                      Color(0xFFECEDF1),
                      Color(0xFFE3E5EA),
                      Color(0xFFD5DAE8),
                    ],
              stops: const [0.0, 0.35, 0.7, 1.0],
            ),
          ),
          child: child,
        );
      },
    );
  }
}
