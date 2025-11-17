import 'dart:ui';
import 'package:flutter/material.dart';

/// Glassmorphism design system for AICO
/// Provides immersive, depth-rich UI components with frosted glass effects
class GlassTheme {
  // Glass blur intensities
  static const double blurLight = 10.0;
  static const double blurMedium = 20.0;
  static const double blurHeavy = 30.0;
  
  // Glass opacity levels
  static const double opacitySubtle = 0.05;
  static const double opacityLight = 0.1;
  static const double opacityMedium = 0.15;
  static const double opacityStrong = 0.25;
  
  // Border radius
  static const double radiusSmall = 12.0;
  static const double radiusMedium = 20.0;
  static const double radiusLarge = 28.0;
  static const double radiusXLarge = 36.0;
  
  // Glow effects
  static const double glowBlurSoft = 24.0;
  static const double glowBlurMedium = 40.0;
  static const double glowBlurIntense = 60.0;
  
  /// Creates a glass container with frosted effect
  static BoxDecoration glass({
    required bool isDark,
    double blur = blurMedium,
    double opacity = opacityMedium,
    double radius = radiusMedium,
    Color? tint,
    bool addBorder = true,
    List<BoxShadow>? shadows,
  }) {
    final baseColor = isDark 
        ? Colors.white.withValues(alpha: opacity)
        : Colors.black.withValues(alpha: opacity * 0.5);
    
    final borderColor = isDark
        ? Colors.white.withValues(alpha: 0.1)
        : Colors.black.withValues(alpha: 0.05);
    
    return BoxDecoration(
      color: tint ?? baseColor,
      borderRadius: BorderRadius.circular(radius),
      border: addBorder ? Border.all(
        color: borderColor,
        width: 1.0,
      ) : null,
      boxShadow: shadows ?? [
        BoxShadow(
          color: Colors.black.withValues(alpha: isDark ? 0.3 : 0.1),
          blurRadius: 20,
          offset: const Offset(0, 10),
        ),
      ],
    );
  }
  
  /// Creates an elevated glass card with depth
  static BoxDecoration glassCard({
    required bool isDark,
    double blur = blurMedium,
    double opacity = opacityMedium,
    double radius = radiusLarge,
    Color? accentColor,
  }) {
    return glass(
      isDark: isDark,
      blur: blur,
      opacity: opacity,
      radius: radius,
      tint: accentColor?.withValues(alpha: opacity * 0.3),
      shadows: [
        BoxShadow(
          color: Colors.black.withValues(alpha: isDark ? 0.4 : 0.15),
          blurRadius: 30,
          offset: const Offset(0, 15),
          spreadRadius: -5,
        ),
        if (accentColor != null)
          BoxShadow(
            color: accentColor.withValues(alpha: 0.2),
            blurRadius: 40,
            offset: const Offset(0, 0),
          ),
      ],
    );
  }
  
  /// Creates a subtle glass panel for backgrounds
  static BoxDecoration glassPanel({
    required bool isDark,
    double radius = radiusMedium,
  }) {
    return glass(
      isDark: isDark,
      blur: blurLight,
      opacity: opacitySubtle,
      radius: radius,
      addBorder: true,
      shadows: [
        BoxShadow(
          color: Colors.black.withValues(alpha: isDark ? 0.2 : 0.05),
          blurRadius: 10,
          offset: const Offset(0, 4),
        ),
      ],
    );
  }
  
  /// Creates an ambient glow effect
  static List<BoxShadow> ambientGlow({
    required Color color,
    double intensity = 0.4,
    double blur = glowBlurMedium,
  }) {
    return [
      BoxShadow(
        color: color.withValues(alpha: intensity),
        blurRadius: blur,
        spreadRadius: blur * 0.3,
      ),
      BoxShadow(
        color: color.withValues(alpha: intensity * 0.5),
        blurRadius: blur * 1.5,
        spreadRadius: blur * 0.5,
      ),
    ];
  }
  
  /// Creates a pulsing glow animation
  static List<BoxShadow> pulsingGlow({
    required Color color,
    required double animationValue, // 0.0 to 1.0
    double baseIntensity = 0.3,
    double pulseIntensity = 0.6,
    double blur = glowBlurMedium,
  }) {
    final intensity = baseIntensity + (pulseIntensity - baseIntensity) * animationValue;
    return ambientGlow(color: color, intensity: intensity, blur: blur);
  }
  
  /// Wraps a widget with backdrop blur filter
  static Widget withBlur({
    required Widget child,
    double blur = blurMedium,
  }) {
    return ClipRRect(
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: blur, sigmaY: blur),
        child: child,
      ),
    );
  }
  
  /// Creates a gradient overlay for depth
  static BoxDecoration gradientOverlay({
    required bool isDark,
    required Alignment begin,
    required Alignment end,
    List<Color>? colors,
    double radius = radiusMedium,
  }) {
    return BoxDecoration(
      borderRadius: BorderRadius.circular(radius),
      gradient: LinearGradient(
        begin: begin,
        end: end,
        colors: colors ?? (isDark
            ? [
                Colors.white.withValues(alpha: 0.1),
                Colors.white.withValues(alpha: 0.0),
              ]
            : [
                Colors.black.withValues(alpha: 0.05),
                Colors.black.withValues(alpha: 0.0),
              ]),
      ),
    );
  }
  
  /// Organic gradient for hero sections
  static BoxDecoration organicGradient({
    required List<Color> colors,
    double radius = radiusLarge,
    AlignmentGeometry center = Alignment.center,
  }) {
    return BoxDecoration(
      borderRadius: BorderRadius.circular(radius),
      gradient: RadialGradient(
        center: center,
        radius: 1.2,
        colors: colors,
        stops: const [0.0, 0.5, 1.0],
      ),
    );
  }
}

/// Animated glass container with hover effects
class GlassContainer extends StatefulWidget {
  final Widget child;
  final bool isDark;
  final double blur;
  final double opacity;
  final double radius;
  final Color? tint;
  final EdgeInsets? padding;
  final bool enableHover;
  final VoidCallback? onTap;
  
  const GlassContainer({
    super.key,
    required this.child,
    required this.isDark,
    this.blur = GlassTheme.blurMedium,
    this.opacity = GlassTheme.opacityMedium,
    this.radius = GlassTheme.radiusMedium,
    this.tint,
    this.padding,
    this.enableHover = false,
    this.onTap,
  });
  
  @override
  State<GlassContainer> createState() => _GlassContainerState();
}

class _GlassContainerState extends State<GlassContainer> 
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _scaleAnimation;
  late Animation<double> _opacityAnimation;
  
  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 200),
      vsync: this,
    );
    
    _scaleAnimation = Tween<double>(begin: 1.0, end: 1.02).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeOut),
    );
    
    _opacityAnimation = Tween<double>(
      begin: widget.opacity,
      end: widget.opacity * 1.3,
    ).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeOut),
    );
  }
  
  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }
  
  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      onEnter: widget.enableHover ? (_) => _controller.forward() : null,
      onExit: widget.enableHover ? (_) => _controller.reverse() : null,
      child: GestureDetector(
        onTap: widget.onTap,
        child: AnimatedBuilder(
          animation: _controller,
          builder: (context, child) {
            return Transform.scale(
              scale: _scaleAnimation.value,
              child: ClipRRect(
                borderRadius: BorderRadius.circular(widget.radius),
                child: BackdropFilter(
                  filter: ImageFilter.blur(
                    sigmaX: widget.blur,
                    sigmaY: widget.blur,
                  ),
                  child: Container(
                    padding: widget.padding,
                    decoration: GlassTheme.glass(
                      isDark: widget.isDark,
                      blur: widget.blur,
                      opacity: _opacityAnimation.value,
                      radius: widget.radius,
                      tint: widget.tint,
                    ),
                    child: widget.child,
                  ),
                ),
              ),
            );
          },
        ),
      ),
    );
  }
}
