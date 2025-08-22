import 'package:flutter/material.dart';

/// Abstract interface for theme management
/// Follows clean architecture principles with dependency inversion
abstract class ThemeManager {
  /// Get current theme mode
  ThemeMode get currentThemeMode;

  /// Get current theme brightness
  Brightness get currentBrightness;

  /// Check if system theme detection is enabled
  bool get isSystemThemeEnabled;

  /// Check if high contrast mode is enabled
  bool get isHighContrastEnabled;

  /// Generate light theme data
  ThemeData generateLightTheme();

  /// Generate dark theme data
  ThemeData generateDarkTheme();

  /// Generate high contrast light theme
  ThemeData generateHighContrastLightTheme();

  /// Generate high contrast dark theme
  ThemeData generateHighContrastDarkTheme();

  /// Set theme mode
  Future<void> setThemeMode(ThemeMode mode);

  /// Toggle between light and dark themes
  Future<void> toggleTheme();

  /// Enable/disable system theme detection
  Future<void> setSystemThemeEnabled(bool enabled);

  /// Enable/disable high contrast mode
  Future<void> setHighContrastEnabled(bool enabled);

  /// Reset theme to default settings
  Future<void> resetTheme();

  /// Stream of theme changes for reactive updates
  Stream<ThemeMode> get themeChanges;
}
