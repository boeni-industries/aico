import 'package:flutter/material.dart';

@immutable
class AicoColors {
  // Base colors
  final Color background;
  final Color surface;
  final Color shadow;
  
  // Brand & accents
  final Color primary;
  final Color onPrimary;
  final Color secondary;
  final Color onSecondary;
  
  // Supporting colors
  final Color success;
  final Color error;
  final Color warning;
  final Color onError;
  
  // Text colors
  final Color onSurface;
  final Color onBackground;
  final Color outline;

  const AicoColors({
    required this.background,
    required this.surface,
    required this.shadow,
    required this.primary,
    required this.onPrimary,
    required this.secondary,
    required this.onSecondary,
    required this.success,
    required this.error,
    required this.warning,
    required this.onError,
    required this.onSurface,
    required this.onBackground,
    required this.outline,
  });

  static const light = AicoColors(
    background: Color(0xFFF5F6FA),
    surface: Color(0xFFFFFFFF),
    shadow: Color(0x17243455),
    primary: Color(0xFFB8A1EA),
    onPrimary: Color(0xFFFFFFFF),
    secondary: Color(0xFF8DD6B8),
    onSecondary: Color(0xFF000000),
    success: Color(0xFF8DD686),
    error: Color(0xFFED7867),
    warning: Color(0xFFFFB74D),
    onError: Color(0xFFFFFFFF),
    onSurface: Color(0xFF1A1C1E),
    onBackground: Color(0xFF1A1C1E),
    outline: Color(0xFFE0E3E7),
  );

  static const dark = AicoColors(
    background: Color(0xFF181A21),
    surface: Color(0xFF21242E),
    shadow: Color(0x33000000),
    primary: Color(0xFFB9A7E6),
    onPrimary: Color(0xFF000000),
    secondary: Color(0xFF8DD6B8),
    onSecondary: Color(0xFF000000),
    success: Color(0xFF8DD686),
    error: Color(0xFFED7867),
    warning: Color(0xFFFFB74D),
    onError: Color(0xFF000000),
    onSurface: Color(0xFFE6E1E5),
    onBackground: Color(0xFFE6E1E5),
    outline: Color(0xFF49454F),
  );
}

@immutable
class AicoTextTheme {
  final TextStyle? headlineLarge;
  final TextStyle? headlineMedium;
  final TextStyle? titleLarge;
  final TextStyle? titleMedium;
  final TextStyle? bodyLarge;
  final TextStyle? bodyMedium;
  final TextStyle? bodySmall;
  final TextStyle? labelLarge;
  final TextStyle? labelMedium;
  final TextStyle? labelSmall;

  const AicoTextTheme({
    this.headlineLarge,
    this.headlineMedium,
    this.titleLarge,
    this.titleMedium,
    this.bodyLarge,
    this.bodyMedium,
    this.bodySmall,
    this.labelLarge,
    this.labelMedium,
    this.labelSmall,
  });

  static const base = AicoTextTheme(
    headlineLarge: TextStyle(
      fontFamily: 'Inter',
      fontSize: 32,
      fontWeight: FontWeight.w700,
      letterSpacing: 0.02,
      height: 1.5,
    ),
    headlineMedium: TextStyle(
      fontFamily: 'Inter',
      fontSize: 24,
      fontWeight: FontWeight.w600,
      letterSpacing: 0.02,
      height: 1.5,
    ),
    titleLarge: TextStyle(
      fontFamily: 'Inter',
      fontSize: 18,
      fontWeight: FontWeight.w500,
      height: 1.5,
    ),
    titleMedium: TextStyle(
      fontFamily: 'Inter',
      fontSize: 16,
      fontWeight: FontWeight.w500,
      height: 1.5,
    ),
    bodyLarge: TextStyle(
      fontFamily: 'Inter',
      fontSize: 16,
      fontWeight: FontWeight.w400,
      height: 1.5,
    ),
    bodyMedium: TextStyle(
      fontFamily: 'Inter',
      fontSize: 14,
      fontWeight: FontWeight.w400,
      height: 1.5,
    ),
    bodySmall: TextStyle(
      fontFamily: 'Inter',
      fontSize: 12,
      fontWeight: FontWeight.w400,
      height: 1.5,
    ),
    labelLarge: TextStyle(
      fontFamily: 'Inter',
      fontSize: 16,
      fontWeight: FontWeight.w600,
      height: 1.5,
    ),
    labelMedium: TextStyle(
      fontFamily: 'Inter',
      fontSize: 14,
      fontWeight: FontWeight.w500,
      height: 1.5,
    ),
    labelSmall: TextStyle(
      fontFamily: 'Inter',
      fontSize: 12,
      fontWeight: FontWeight.w500,
      height: 1.5,
    ),
  );
}

@immutable
class AicoThemeExtension extends ThemeExtension<AicoThemeExtension> {
  final AicoColors colors;
  final AicoTextTheme textTheme;

  const AicoThemeExtension({
    required this.colors,
    required this.textTheme,
  });

  @override
  AicoThemeExtension copyWith({
    AicoColors? colors,
    AicoTextTheme? textTheme,
  }) {
    return AicoThemeExtension(
      colors: colors ?? this.colors,
      textTheme: textTheme ?? this.textTheme,
    );
  }

  @override
  AicoThemeExtension lerp(AicoThemeExtension? other, double t) {
    if (other is! AicoThemeExtension) {
      return this;
    }
    return AicoThemeExtension(
      colors: colors, // Colors don't interpolate well, use discrete values
      textTheme: textTheme, // Text themes don't interpolate
    );
  }
}

class AicoTheme {
  static ThemeData light() {
    const colors = AicoColors.light;
    const textTheme = AicoTextTheme.base;
    
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      colorScheme: ColorScheme.light(
        primary: colors.primary,
        onPrimary: colors.onPrimary,
        secondary: colors.secondary,
        onSecondary: colors.onSecondary,
        surface: colors.surface,
        onSurface: colors.onSurface,
        error: colors.error,
        onError: colors.onError,
        outline: colors.outline,
      ),
      scaffoldBackgroundColor: colors.background,
      cardColor: colors.surface,
      extensions: const [
        AicoThemeExtension(
          colors: colors,
          textTheme: textTheme,
        ),
      ],
    );
  }

  static ThemeData dark() {
    const colors = AicoColors.dark;
    const textTheme = AicoTextTheme.base;
    
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      colorScheme: ColorScheme.dark(
        primary: colors.primary,
        onPrimary: colors.onPrimary,
        secondary: colors.secondary,
        onSecondary: colors.onSecondary,
        surface: colors.surface,
        onSurface: colors.onSurface,
        error: colors.error,
        onError: colors.onError,
        outline: colors.outline,
      ),
      scaffoldBackgroundColor: colors.background,
      cardColor: colors.surface,
      extensions: const [
        AicoThemeExtension(
          colors: colors,
          textTheme: textTheme,
        ),
      ],
    );
  }
}
