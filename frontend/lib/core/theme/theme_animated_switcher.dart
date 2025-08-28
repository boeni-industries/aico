import 'package:aico_frontend/core/theme/design_tokens.dart';
import 'package:flutter/material.dart';

/// Animated theme switcher widget for smooth theme transitions
/// Provides elegant animations when switching between light/dark themes
class ThemeAnimatedSwitcher extends StatelessWidget {
  final Widget child;
  final Duration? duration;
  final Curve? curve;

  const ThemeAnimatedSwitcher({
    super.key,
    required this.child,
    this.duration,
    this.curve,
  });

  @override
  Widget build(BuildContext context) {
    return AnimatedSwitcher(
      duration: duration ?? AicoDesignTokens.durationThemeTransition,
      switchInCurve: curve ?? AicoDesignTokens.easeInOut,
      switchOutCurve: curve ?? AicoDesignTokens.easeInOut,
      transitionBuilder: (child, animation) {
        return FadeTransition(
          opacity: animation,
          child: child,
        );
      },
      child: child,
    );
  }
}

/// Theme transition builder for custom animations
class ThemeTransitionBuilder extends StatelessWidget {
  final Widget Function(BuildContext context, Animation<double> animation) builder;
  final Duration duration;
  final Curve curve;

  const ThemeTransitionBuilder({
    super.key,
    required this.builder,
    this.duration = const Duration(milliseconds: 200),
    this.curve = Curves.easeInOut,
  });

  @override
  Widget build(BuildContext context) {
    return TweenAnimationBuilder<double>(
      duration: duration,
      curve: curve,
      tween: Tween(begin: 0.0, end: 1.0),
      builder: (context, value, child) {
        final animation = AlwaysStoppedAnimation<double>(value);
        return builder(context, animation);
      },
    );
  }
}

/// Animated theme-aware container
class AnimatedThemeContainer extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry? padding;
  final EdgeInsetsGeometry? margin;
  final Color? color;
  final Decoration? decoration;
  final double? width;
  final double? height;
  final Duration duration;
  final Curve curve;

  const AnimatedThemeContainer({
    super.key,
    required this.child,
    this.padding,
    this.margin,
    this.color,
    this.decoration,
    this.width,
    this.height,
    this.duration = const Duration(milliseconds: 200),
    this.curve = Curves.easeInOut,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    
    return AnimatedContainer(
      duration: duration,
      curve: curve,
      width: width,
      height: height,
      padding: padding,
      margin: margin,
      decoration: decoration ?? BoxDecoration(
        color: color ?? theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(AicoDesignTokens.radiusMedium),
      ),
      child: child,
    );
  }
}
