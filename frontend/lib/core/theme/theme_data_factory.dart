import 'package:aico_frontend/core/theme/design_tokens.dart';
import 'package:flutter/material.dart';

/// Factory for creating Material 3 ThemeData with AICO branding
/// Generates consistent, accessible themes following design tokens
class AicoThemeDataFactory {
  AicoThemeDataFactory._();

  /// Generate light theme with AICO branding
  static ThemeData generateLightTheme() {
    // Create custom color scheme following AICO design principles
    const colorScheme = ColorScheme.light(
      // Brand & Accents - Soft Lavender as primary
      primary: Color(0xFFB8A1EA), // Soft Lavender from design principles
      onPrimary: Colors.white,
      
      // Secondary accents
      secondary: Color(0xFF8DD6B8), // Mint
      onSecondary: Colors.black,
      
      // Surface colors - Pure white for cards/panels
      surface: Color(0xFFFFFFFF), // Pure white
      onSurface: Color(0xFF1A1C1E),
      
      // Error states
      error: Color(0xFFED7867), // Coral
      onError: Colors.white,
      
      // Outline colors
      outline: Color(0xFFE0E3E7),
      outlineVariant: Color(0xFFE0E3E7),
      
      // Shadow
      shadow: Color.fromRGBO(36, 52, 85, 0.09),
    );

    return _createBaseTheme(colorScheme);
  }

  /// Generate dark theme with AICO branding
  static ThemeData generateDarkTheme() {
    // Create custom dark color scheme following AICO design principles
    const colorScheme = ColorScheme.dark(
      // Brand & Accents - Soft Lavender variant for dark mode
      primary: Color(0xFFB9A7E6), // Dark mode equivalent from design principles
      onPrimary: Colors.black,
      
      // Secondary accents
      secondary: Color(0xFF8DD6B8), // Mint
      onSecondary: Colors.black,
      
      // Surface colors
      surface: Color(0xFF21242E), // Dark surface from design principles
      onSurface: Color(0xFFE6E1E5),
      
      // Error states
      error: Color(0xFFED7867), // Coral
      onError: Colors.black,
      
      // Outline colors
      outline: Color(0xFF49454F),
      outlineVariant: Color(0xFF49454F),
      
      // Shadow
      shadow: Color.fromRGBO(0, 0, 0, 0.33),
    );

    return _createBaseTheme(colorScheme);
  }

  /// Generate high contrast light theme
  static ThemeData generateHighContrastLightTheme() {
    const colorScheme = ColorScheme(
      brightness: Brightness.light,
      primary: Colors.black,
      onPrimary: Colors.white,
      secondary: Colors.black,
      onSecondary: Colors.white,
      tertiary: Colors.black,
      onTertiary: Colors.white,
      error: Color(0xFFD32F2F),
      onError: Colors.white,
      surface: Colors.white,
      onSurface: Colors.black,
      surfaceContainerHighest: Color(0xFFF5F5F5),
      onSurfaceVariant: Colors.black,
      outline: Colors.black,
      outlineVariant: Color(0xFF757575),
      shadow: Colors.black,
      scrim: Colors.black,
      inverseSurface: Colors.black,
      onInverseSurface: Colors.white,
      inversePrimary: Colors.white,
      surfaceTint: Colors.black,
    );

    return _createBaseTheme(colorScheme, isHighContrast: true);
  }

  /// Generate high contrast dark theme  
  static ThemeData generateHighContrastDarkTheme() {
    const colorScheme = ColorScheme(
      brightness: Brightness.dark,
      primary: Colors.white,
      onPrimary: Colors.black,
      secondary: Colors.white,
      onSecondary: Colors.black,
      tertiary: Colors.white,
      onTertiary: Colors.black,
      error: Color(0xFFFF5252),
      onError: Colors.black,
      surface: Colors.black,
      onSurface: Colors.white,
      surfaceContainerHighest: Color(0xFF1A1A1A),
      onSurfaceVariant: Colors.white,
      outline: Colors.white,
      outlineVariant: Color(0xFF9E9E9E),
      shadow: Colors.black,
      scrim: Colors.black,
      inverseSurface: Colors.white,
      onInverseSurface: Colors.black,
      inversePrimary: Colors.black,
      surfaceTint: Colors.white,
    );

    return _createBaseTheme(colorScheme, isHighContrast: true);
  }

  /// Generate high contrast dark theme for accessibility
  static ThemeData createHighContrastDarkTheme() {
    final colorScheme = ColorScheme.fromSeed(
      seedColor: AicoDesignTokens.darkAccent,
      brightness: Brightness.dark,
      surface: Colors.black,
      primary: Colors.white,
      onPrimary: Colors.black,
      secondary: Colors.white70,
      onSecondary: Colors.black,
    );

    return _createBaseTheme(colorScheme, isHighContrast: true);
  }

  /// Create base theme with common styling
  static ThemeData _createBaseTheme(
    ColorScheme colorScheme, {
    bool isHighContrast = false,
  }) {
    return ThemeData(
      useMaterial3: true,
      brightness: colorScheme.brightness, // Explicitly set brightness
      colorScheme: colorScheme,
      
      // Typography following AICO design principles
      textTheme: _createTextTheme(colorScheme),
      
      // Component themes
      appBarTheme: _createAppBarTheme(colorScheme),
      elevatedButtonTheme: _createElevatedButtonTheme(colorScheme),
      textButtonTheme: _createTextButtonTheme(colorScheme),
      outlinedButtonTheme: _createOutlinedButtonTheme(colorScheme),
      inputDecorationTheme: _createInputDecorationTheme(colorScheme),
      cardTheme: _createCardTheme(colorScheme),
      bottomNavigationBarTheme: _createBottomNavigationBarTheme(colorScheme),
      navigationBarTheme: _createNavigationBarTheme(colorScheme),
      floatingActionButtonTheme: _createFABTheme(colorScheme),
      
      // Set scaffold background color to match design principles
      scaffoldBackgroundColor: colorScheme.surface,
      
      // Shape themes
      
      // Animation themes
      pageTransitionsTheme: const PageTransitionsTheme(
        builders: {
          TargetPlatform.android: CupertinoPageTransitionsBuilder(),
          TargetPlatform.iOS: CupertinoPageTransitionsBuilder(),
          TargetPlatform.macOS: CupertinoPageTransitionsBuilder(),
          TargetPlatform.windows: FadeUpwardsPageTransitionsBuilder(),
          TargetPlatform.linux: FadeUpwardsPageTransitionsBuilder(),
        },
      ),
      
      // Accessibility enhancements for high contrast
      visualDensity: isHighContrast 
          ? VisualDensity.comfortable 
          : VisualDensity.adaptivePlatformDensity,
    );
  }

  /// Create text theme following AICO typography tokens
  static TextTheme _createTextTheme(ColorScheme colorScheme) {
    return TextTheme(
      // Headlines
      headlineLarge: TextStyle(
        fontFamily: AicoDesignTokens.fontFamily,
        fontSize: AicoDesignTokens.fontSizeHeadline1,
        fontWeight: AicoDesignTokens.fontWeightHeadline1,
        letterSpacing: AicoDesignTokens.letterSpacingHeadlines,
        height: AicoDesignTokens.lineHeightMultiplier,
        color: colorScheme.onSurface,
      ),
      headlineMedium: TextStyle(
        fontFamily: AicoDesignTokens.fontFamily,
        fontSize: AicoDesignTokens.fontSizeHeadline2,
        fontWeight: AicoDesignTokens.fontWeightHeadline2,
        letterSpacing: AicoDesignTokens.letterSpacingHeadlines,
        height: AicoDesignTokens.lineHeightMultiplier,
        color: colorScheme.onSurface,
      ),
      
      // Subtitles
      titleLarge: TextStyle(
        fontFamily: AicoDesignTokens.fontFamily,
        fontSize: AicoDesignTokens.fontSizeSubtitle,
        fontWeight: AicoDesignTokens.fontWeightSubtitle,
        height: AicoDesignTokens.lineHeightMultiplier,
        color: colorScheme.onSurface,
      ),
      
      // Body text
      bodyLarge: TextStyle(
        fontFamily: AicoDesignTokens.fontFamily,
        fontSize: AicoDesignTokens.fontSizeBody,
        fontWeight: AicoDesignTokens.fontWeightBody,
        height: AicoDesignTokens.lineHeightMultiplier,
        color: colorScheme.onSurface,
      ),
      bodyMedium: TextStyle(
        fontFamily: AicoDesignTokens.fontFamily,
        fontSize: AicoDesignTokens.fontSizeBody,
        fontWeight: AicoDesignTokens.fontWeightBody,
        height: AicoDesignTokens.lineHeightMultiplier,
        color: colorScheme.onSurface,
      ),
      
      // Caption
      bodySmall: TextStyle(
        fontFamily: AicoDesignTokens.fontFamily,
        fontSize: AicoDesignTokens.fontSizeCaption,
        fontWeight: AicoDesignTokens.fontWeightCaption,
        height: AicoDesignTokens.lineHeightMultiplier,
        color: colorScheme.onSurface.withValues(alpha: 0.7),
      ),
      
      // Labels
      labelLarge: TextStyle(
        fontFamily: AicoDesignTokens.fontFamily,
        fontSize: AicoDesignTokens.fontSizeButton,
        fontWeight: AicoDesignTokens.fontWeightButton,
        height: AicoDesignTokens.lineHeightMultiplier,
        color: colorScheme.onSurface,
      ),
    );
  }

  /// Create app bar theme
  static AppBarTheme _createAppBarTheme(ColorScheme colorScheme) {
    return AppBarTheme(
      elevation: AicoDesignTokens.elevationLevel0,
      backgroundColor: colorScheme.surface,
      foregroundColor: colorScheme.onSurface,
      centerTitle: true,
      titleTextStyle: TextStyle(
        fontFamily: AicoDesignTokens.fontFamily,
        fontSize: AicoDesignTokens.fontSizeHeadline2,
        fontWeight: AicoDesignTokens.fontWeightHeadline2,
        color: colorScheme.onSurface,
      ),
    );
  }

  /// Create elevated button theme
  static ElevatedButtonThemeData _createElevatedButtonTheme(ColorScheme colorScheme) {
    return ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: colorScheme.primary,
        foregroundColor: colorScheme.onPrimary,
        elevation: AicoDesignTokens.elevationLevel1,
        padding: const EdgeInsets.symmetric(
          horizontal: AicoDesignTokens.paddingButtonH,
          vertical: AicoDesignTokens.paddingButtonV,
        ),
        minimumSize: const Size(
          AicoDesignTokens.minTouchTarget,
          AicoDesignTokens.minTouchTarget,
        ),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AicoDesignTokens.radiusLarge),
        ),
        textStyle: const TextStyle(
          fontFamily: AicoDesignTokens.fontFamily,
          fontSize: AicoDesignTokens.fontSizeButton,
          fontWeight: AicoDesignTokens.fontWeightButton,
        ),
        animationDuration: AicoDesignTokens.durationButtonPress,
      ),
    );
  }

  /// Create text button theme
  static TextButtonThemeData _createTextButtonTheme(ColorScheme colorScheme) {
    return TextButtonThemeData(
      style: TextButton.styleFrom(
        foregroundColor: colorScheme.primary,
        padding: const EdgeInsets.symmetric(
          horizontal: AicoDesignTokens.paddingButtonH,
          vertical: AicoDesignTokens.paddingButtonV,
        ),
        minimumSize: const Size(
          AicoDesignTokens.minTouchTarget,
          AicoDesignTokens.minTouchTarget,
        ),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AicoDesignTokens.radiusLarge),
        ),
        textStyle: const TextStyle(
          fontFamily: AicoDesignTokens.fontFamily,
          fontSize: AicoDesignTokens.fontSizeButton,
          fontWeight: AicoDesignTokens.fontWeightButton,
        ),
        animationDuration: AicoDesignTokens.durationButtonPress,
      ),
    );
  }

  /// Create outlined button theme
  static OutlinedButtonThemeData _createOutlinedButtonTheme(ColorScheme colorScheme) {
    return OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: colorScheme.primary,
        side: BorderSide(color: colorScheme.primary),
        padding: const EdgeInsets.symmetric(
          horizontal: AicoDesignTokens.paddingButtonH,
          vertical: AicoDesignTokens.paddingButtonV,
        ),
        minimumSize: const Size(
          AicoDesignTokens.minTouchTarget,
          AicoDesignTokens.minTouchTarget,
        ),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AicoDesignTokens.radiusLarge),
        ),
        textStyle: const TextStyle(
          fontFamily: AicoDesignTokens.fontFamily,
          fontSize: AicoDesignTokens.fontSizeButton,
          fontWeight: AicoDesignTokens.fontWeightButton,
        ),
        animationDuration: AicoDesignTokens.durationButtonPress,
      ),
    );
  }

  /// Create input decoration theme
  static InputDecorationTheme _createInputDecorationTheme(ColorScheme colorScheme) {
    return InputDecorationTheme(
      filled: true,
      fillColor: colorScheme.surface,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AicoDesignTokens.radiusMedium),
        borderSide: BorderSide(color: colorScheme.outline),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AicoDesignTokens.radiusMedium),
        borderSide: BorderSide(color: colorScheme.outline),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AicoDesignTokens.radiusMedium),
        borderSide: BorderSide(color: colorScheme.primary, width: 2),
      ),
      errorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AicoDesignTokens.radiusMedium),
        borderSide: BorderSide(color: colorScheme.error),
      ),
      contentPadding: const EdgeInsets.all(AicoDesignTokens.spaceMd),
      labelStyle: TextStyle(
        fontFamily: AicoDesignTokens.fontFamily,
        color: colorScheme.onSurface.withValues(alpha: 0.7),
      ),
      hintStyle: TextStyle(
        fontFamily: AicoDesignTokens.fontFamily,
        color: colorScheme.onSurface.withValues(alpha: 0.5),
      ),
    );
  }

  /// Create card theme
  static CardThemeData _createCardTheme(ColorScheme colorScheme) {
    return CardThemeData(
      color: colorScheme.surface,
      elevation: AicoDesignTokens.elevationLevel1,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AicoDesignTokens.radiusMedium),
      ),
      margin: const EdgeInsets.all(AicoDesignTokens.spaceSm),
    );
  }

  /// Create bottom navigation bar theme
  static BottomNavigationBarThemeData _createBottomNavigationBarTheme(ColorScheme colorScheme) {
    return BottomNavigationBarThemeData(
      backgroundColor: colorScheme.surface,
      selectedItemColor: colorScheme.primary,
      unselectedItemColor: colorScheme.onSurface.withValues(alpha: 0.6),
      type: BottomNavigationBarType.fixed,
      elevation: AicoDesignTokens.elevationLevel2,
    );
  }

  /// Create navigation bar theme (Material 3)
  static NavigationBarThemeData _createNavigationBarTheme(ColorScheme colorScheme) {
    return NavigationBarThemeData(
      backgroundColor: colorScheme.surface,
      indicatorColor: colorScheme.primary.withValues(alpha: 0.12),
      labelTextStyle: WidgetStateProperty.resolveWith((states) {
        if (states.contains(WidgetState.selected)) {
          return TextStyle(
            fontFamily: AicoDesignTokens.fontFamily,
            fontSize: AicoDesignTokens.fontSizeCaption,
            fontWeight: FontWeight.w600,
            color: colorScheme.primary,
          );
        }
        return TextStyle(
          fontFamily: AicoDesignTokens.fontFamily,
          fontSize: AicoDesignTokens.fontSizeCaption,
          color: colorScheme.onSurface.withValues(alpha: 0.6),
        );
      }),
    );
  }

  /// Create floating action button theme
  static FloatingActionButtonThemeData _createFABTheme(ColorScheme colorScheme) {
    return FloatingActionButtonThemeData(
      backgroundColor: colorScheme.primary,
      foregroundColor: colorScheme.onPrimary,
      elevation: AicoDesignTokens.elevationLevel3,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AicoDesignTokens.radiusMedium),
      ),
    );
  }
}
