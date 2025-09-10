import 'dart:async';

import 'package:aico_frontend/core/theme/theme_data_factory.dart';
import 'package:aico_frontend/core/theme/theme_manager.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/// Concrete implementation of ThemeManager for AICO
/// Migrated to work with Riverpod ThemeController
class AicoThemeManager implements ThemeManager {
  final StreamController<ThemeMode> _themeController = StreamController<ThemeMode>.broadcast();
  
  ThemeMode _currentMode = ThemeMode.system;
  bool _isHighContrast = false;
  ThemeData? _cachedLightTheme;
  ThemeData? _cachedDarkTheme;
  ThemeData? _cachedHighContrastLightTheme;
  ThemeData? _cachedHighContrastDarkTheme;
  bool _disposed = false;

  AicoThemeManager() {
    _initializeFromSettings();
  }


  @override
  ThemeMode get currentThemeMode => _currentMode;

  @override
  bool get isHighContrastEnabled => _isHighContrast;

  @override
  Brightness get currentBrightness {
    switch (_currentMode) {
      case ThemeMode.light:
        return Brightness.light;
      case ThemeMode.dark:
        return Brightness.dark;
      case ThemeMode.system:
        return WidgetsBinding.instance.platformDispatcher.platformBrightness;
    }
  }

  @override
  bool get isSystemThemeEnabled => _currentMode == ThemeMode.system;

  @override
  Stream<ThemeMode> get themeChanges => _themeController.stream;

  @override
  ThemeData generateLightTheme() {
    return _cachedLightTheme ??= AicoThemeDataFactory.generateLightTheme();
  }

  @override
  ThemeData generateDarkTheme() {
    return _cachedDarkTheme ??= AicoThemeDataFactory.generateDarkTheme();
  }

  @override
  ThemeData generateHighContrastLightTheme() {
    return _cachedHighContrastLightTheme ??= AicoThemeDataFactory.generateHighContrastLightTheme();
  }

  @override
  ThemeData generateHighContrastDarkTheme() {
    return _cachedHighContrastDarkTheme ??= AicoThemeDataFactory.generateHighContrastDarkTheme();
  }

  /// Get current theme data based on mode and contrast settings
  ThemeData getCurrentTheme() {
    final brightness = currentBrightness;
    if (_isHighContrast) {
      return brightness == Brightness.light 
          ? generateHighContrastLightTheme()
          : generateHighContrastDarkTheme();
    }
    return brightness == Brightness.light 
        ? generateLightTheme()
        : generateDarkTheme();
  }

  @override
  Future<void> setThemeMode(ThemeMode mode) async {
    if (_disposed) return;
    
    _currentMode = mode;
    _themeController.add(mode);
    
    // Theme persistence handled by ThemeController
  }

  @override
  Future<void> toggleTheme() async {
    final newMode = _currentMode == ThemeMode.light 
        ? ThemeMode.dark 
        : ThemeMode.light;
    await setThemeMode(newMode);
  }

  @override
  Future<void> setSystemThemeEnabled(bool enabled) async {
    final newMode = enabled ? ThemeMode.system : ThemeMode.light;
    await setThemeMode(newMode);
  }

  @override
  Future<void> setHighContrastEnabled(bool enabled) async {
    if (_disposed) return;
    
    _isHighContrast = enabled;
    _clearThemeCache();
    
    // High contrast persistence handled by ThemeController
    
    await _updateSystemUIOverlay();
    _themeController.add(_currentMode);
  }

  @override
  Future<void> resetTheme() async {
    _currentMode = ThemeMode.system;
    _isHighContrast = false;
    _clearThemeCache();
    
    // Theme reset handled by ThemeController
    
    await _updateSystemUIOverlay();
  }

  /// Initialize theme settings with defaults
  void _initializeFromSettings() {
    // Default values - will be overridden by ThemeController
    _currentMode = ThemeMode.system;
    _isHighContrast = false;
    
    // Update system UI overlay
    _updateSystemUIOverlay();
  }

  /// Update theme mode (called by ThemeController)
  void updateThemeMode(ThemeMode mode) {
    _currentMode = mode;
    _updateSystemUIOverlay();
  }

  /// Update high contrast setting (called by ThemeController)
  void updateHighContrast(bool enabled) {
    _isHighContrast = enabled;
    _clearThemeCache();
    _updateSystemUIOverlay();
  }


  /// Update system UI overlay style based on current theme
  Future<void> _updateSystemUIOverlay() async {
    final brightness = currentBrightness;
    final theme = getCurrentTheme();
    
    SystemChrome.setSystemUIOverlayStyle(SystemUiOverlayStyle(
      statusBarColor: Colors.transparent,
      statusBarBrightness: brightness == Brightness.light 
          ? Brightness.dark 
          : Brightness.light,
      statusBarIconBrightness: brightness == Brightness.light 
          ? Brightness.dark 
          : Brightness.light,
      systemNavigationBarColor: theme.colorScheme.surface,
      systemNavigationBarIconBrightness: brightness == Brightness.light 
          ? Brightness.dark 
          : Brightness.light,
    ));
  }

  /// Clear cached themes to force regeneration
  void _clearThemeCache() {
    _cachedLightTheme = null;
    _cachedDarkTheme = null;
    _cachedHighContrastLightTheme = null;
    _cachedHighContrastDarkTheme = null;
  }


  /// Dispose resources
  void dispose() {
    if (_disposed) return;
    _disposed = true;
    
    // Cleanup handled by ThemeController
    
    if (!_themeController.isClosed) {
      _themeController.close();
    }
  }
}
