import 'package:flutter/material.dart';

/// Micro-interaction theme system for AICO
/// 
/// Provides theme-aware timing, colors, and behaviors for all interactive elements.
/// Follows AICO principles: Simplicity First, DRY, KISS, Explicit over Implicit.
/// 
/// Usage:
/// ```dart
/// final microTheme = MicroInteractionTheme.of(context);
/// final buttonTheme = microTheme.button;
/// ```
class MicroInteractionTheme {
  final MicroInteractionButtonTheme button;
  final MicroInteractionIconTheme icon;
  final MicroInteractionInputTheme input;
  final MicroInteractionFeedbackTheme feedback;
  final MicroInteractionTimings timings;
  
  const MicroInteractionTheme({
    required this.button,
    required this.icon,
    required this.input,
    required this.feedback,
    required this.timings,
  });
  
  /// Get theme-aware micro-interaction configuration
  static MicroInteractionTheme of(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final isHighContrast = MediaQuery.of(context).highContrast;
    final reduceMotion = MediaQuery.of(context).disableAnimations;
    
    return MicroInteractionTheme(
      button: MicroInteractionButtonTheme.fromTheme(
        theme: theme,
        isDark: isDark,
        isHighContrast: isHighContrast,
      ),
      icon: MicroInteractionIconTheme.fromTheme(
        theme: theme,
        isDark: isDark,
        isHighContrast: isHighContrast,
      ),
      input: MicroInteractionInputTheme.fromTheme(
        theme: theme,
        isDark: isDark,
        isHighContrast: isHighContrast,
      ),
      feedback: MicroInteractionFeedbackTheme.fromTheme(
        theme: theme,
        isDark: isDark,
        isHighContrast: isHighContrast,
      ),
      timings: MicroInteractionTimings(reduceMotion: reduceMotion),
    );
  }
}

/// Button micro-interaction theme
/// Defines colors, scales, and shadows for button states
class MicroInteractionButtonTheme {
  // Scale values
  final double defaultScale;
  final double hoverScale;
  final double pressedScale;
  final double successScaleMax;
  
  // Colors
  final Color defaultColor;
  final Color hoverColor;
  final Color pressedColor;
  final Color successColor;
  final Color disabledColor;
  
  // Shadows and glows
  final List<BoxShadow> defaultShadows;
  final List<BoxShadow> hoverShadows;
  final List<BoxShadow> pressedShadows;
  
  const MicroInteractionButtonTheme({
    required this.defaultScale,
    required this.hoverScale,
    required this.pressedScale,
    required this.successScaleMax,
    required this.defaultColor,
    required this.hoverColor,
    required this.pressedColor,
    required this.successColor,
    required this.disabledColor,
    required this.defaultShadows,
    required this.hoverShadows,
    required this.pressedShadows,
  });
  
  factory MicroInteractionButtonTheme.fromTheme({
    required ThemeData theme,
    required bool isDark,
    required bool isHighContrast,
  }) {
    final accentColor = const Color(0xFFB8A1EA); // Soft purple
    final successColor = const Color(0xFF10B981); // Emerald green
    
    // Subtle scale changes - barely perceptible
    final hoverScale = isHighContrast ? 1.04 : 1.02;
    final pressedScale = isHighContrast ? 0.97 : 0.98;
    
    // Adjust colors for theme
    final defaultColor = accentColor;
    final hoverColor = _adjustBrightness(accentColor, isDark ? 0.15 : 0.10);
    final pressedColor = _adjustBrightness(accentColor, isDark ? -0.10 : -0.05);
    final disabledColor = theme.colorScheme.onSurface.withValues(alpha: 0.3);
    
    // Shadows: more subtle in light mode, more prominent in dark mode
    final shadowOpacity = isDark ? 0.4 : 0.2;
    final glowOpacity = isDark ? 0.3 : 0.2;
    
    return MicroInteractionButtonTheme(
      defaultScale: 1.0,
      hoverScale: hoverScale,
      pressedScale: pressedScale,
      successScaleMax: 1.02, // Barely perceptible
      defaultColor: defaultColor,
      hoverColor: hoverColor,
      pressedColor: pressedColor,
      successColor: successColor,
      disabledColor: disabledColor,
      defaultShadows: [
        BoxShadow(
          color: accentColor.withValues(alpha: shadowOpacity),
          blurRadius: 8,
          offset: const Offset(0, 4),
        ),
      ],
      hoverShadows: [
        BoxShadow(
          color: accentColor.withValues(alpha: shadowOpacity + 0.1),
          blurRadius: 12,
          offset: const Offset(0, 4),
        ),
        BoxShadow(
          color: accentColor.withValues(alpha: glowOpacity),
          blurRadius: 16,
          spreadRadius: 2,
        ),
      ],
      pressedShadows: [
        BoxShadow(
          color: accentColor.withValues(alpha: shadowOpacity - 0.1),
          blurRadius: 4,
          offset: const Offset(0, 2),
        ),
      ],
    );
  }
}

/// Icon micro-interaction theme
/// Defines colors, scales, and effects for icon states
class MicroInteractionIconTheme {
  final double defaultScale;
  final double hoverScale;
  final double pressedScale;
  final double activeScale;
  
  final Color defaultColor;
  final Color hoverColor;
  final Color pressedColor;
  final Color activeColor;
  
  final Color defaultBackground;
  final Color hoverBackground;
  final Color pressedBackground;
  final Color activeBackground;
  
  final List<BoxShadow>? hoverGlow;
  final List<BoxShadow>? activeGlow;
  
  const MicroInteractionIconTheme({
    required this.defaultScale,
    required this.hoverScale,
    required this.pressedScale,
    required this.activeScale,
    required this.defaultColor,
    required this.hoverColor,
    required this.pressedColor,
    required this.activeColor,
    required this.defaultBackground,
    required this.hoverBackground,
    required this.pressedBackground,
    required this.activeBackground,
    this.hoverGlow,
    this.activeGlow,
  });
  
  factory MicroInteractionIconTheme.fromTheme({
    required ThemeData theme,
    required bool isDark,
    required bool isHighContrast,
  }) {
    final accentColor = const Color(0xFFB8A1EA);
    final defaultColor = theme.colorScheme.onSurface.withValues(alpha: 0.7);
    
    return MicroInteractionIconTheme(
      defaultScale: 1.0,
      hoverScale: isHighContrast ? 1.12 : 1.1,
      pressedScale: isHighContrast ? 0.92 : 0.95,
      activeScale: 1.0,
      defaultColor: defaultColor,
      hoverColor: accentColor,
      pressedColor: _adjustBrightness(accentColor, -0.1),
      activeColor: accentColor,
      defaultBackground: Colors.transparent,
      hoverBackground: accentColor.withValues(alpha: 0.05),
      pressedBackground: accentColor.withValues(alpha: 0.1),
      activeBackground: accentColor.withValues(alpha: 0.1),
      hoverGlow: isDark ? [
        BoxShadow(
          color: accentColor.withValues(alpha: 0.2),
          blurRadius: 8,
          spreadRadius: 0,
        ),
      ] : null,
      activeGlow: isDark ? [
        BoxShadow(
          color: accentColor.withValues(alpha: 0.15),
          blurRadius: 12,
          spreadRadius: 0,
        ),
      ] : null,
    );
  }
}

/// Input field micro-interaction theme
class MicroInteractionInputTheme {
  final Color focusBorderColor;
  final Color errorBorderColor;
  final double focusScale;
  final List<BoxShadow> focusGlow;
  final List<BoxShadow> errorGlow;
  
  const MicroInteractionInputTheme({
    required this.focusBorderColor,
    required this.errorBorderColor,
    required this.focusScale,
    required this.focusGlow,
    required this.errorGlow,
  });
  
  factory MicroInteractionInputTheme.fromTheme({
    required ThemeData theme,
    required bool isDark,
    required bool isHighContrast,
  }) {
    final accentColor = const Color(0xFFB8A1EA);
    final errorColor = const Color(0xFFED7867);
    
    return MicroInteractionInputTheme(
      focusBorderColor: accentColor,
      errorBorderColor: errorColor,
      focusScale: isHighContrast ? 1.03 : 1.02,
      focusGlow: [
        BoxShadow(
          color: accentColor.withValues(alpha: isDark ? 0.3 : 0.2),
          blurRadius: 12,
          spreadRadius: 0,
        ),
      ],
      errorGlow: [
        BoxShadow(
          color: errorColor.withValues(alpha: isDark ? 0.3 : 0.2),
          blurRadius: 12,
          spreadRadius: 0,
        ),
      ],
    );
  }
}

/// Feedback micro-interaction theme (success, error, loading)
class MicroInteractionFeedbackTheme {
  final Color successColor;
  final Color errorColor;
  final Color loadingColor;
  
  final Duration successDuration;
  final Duration errorDuration;
  
  const MicroInteractionFeedbackTheme({
    required this.successColor,
    required this.errorColor,
    required this.loadingColor,
    required this.successDuration,
    required this.errorDuration,
  });
  
  factory MicroInteractionFeedbackTheme.fromTheme({
    required ThemeData theme,
    required bool isDark,
    required bool isHighContrast,
  }) {
    return const MicroInteractionFeedbackTheme(
      successColor: Color(0xFF10B981), // Emerald
      errorColor: Color(0xFFED7867),   // Coral
      loadingColor: Color(0xFF3B82F6), // Sapphire
      successDuration: Duration(milliseconds: 400),
      errorDuration: Duration(milliseconds: 600),
    );
  }
}

/// Timing constants for micro-interactions
/// Respects reduced motion preferences
class MicroInteractionTimings {
  final bool reduceMotion;
  
  // Micro-interactions (<200ms)
  final Duration hoverDuration;
  final Duration pressDuration;
  final Duration releaseDuration;
  
  // Transitions (200-400ms)
  final Duration transitionDuration;
  final Duration colorTransitionDuration;
  
  // Contextual (400-800ms)
  final Duration successDuration;
  final Duration errorDuration;
  
  // Curves
  final Curve hoverCurve;
  final Curve pressCurve;
  final Curve releaseCurve;
  final Curve transitionCurve;
  final Curve successCurve;
  
  MicroInteractionTimings({required this.reduceMotion})
      : hoverDuration = reduceMotion 
          ? Duration.zero 
          : const Duration(milliseconds: 150),
        pressDuration = reduceMotion 
          ? Duration.zero 
          : const Duration(milliseconds: 80),
        releaseDuration = reduceMotion 
          ? Duration.zero 
          : const Duration(milliseconds: 120),
        transitionDuration = reduceMotion 
          ? const Duration(milliseconds: 100) 
          : const Duration(milliseconds: 300),
        colorTransitionDuration = reduceMotion 
          ? const Duration(milliseconds: 100) 
          : const Duration(milliseconds: 200),
        successDuration = reduceMotion 
          ? const Duration(milliseconds: 200) 
          : const Duration(milliseconds: 400),
        errorDuration = reduceMotion 
          ? const Duration(milliseconds: 200) 
          : const Duration(milliseconds: 600),
        hoverCurve = Curves.easeOut,
        pressCurve = Curves.easeInOut,
        releaseCurve = Curves.easeOutBack,
        transitionCurve = Curves.easeInOutCubic,
        successCurve = Curves.easeInOutCubic;
}

/// Helper function to adjust color brightness
Color _adjustBrightness(Color color, double amount) {
  final hsl = HSLColor.fromColor(color);
  final lightness = (hsl.lightness + amount).clamp(0.0, 1.0);
  return hsl.withLightness(lightness).toColor();
}
