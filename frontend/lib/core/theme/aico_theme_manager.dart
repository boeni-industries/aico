import 'dart:async';

// import 'package:aico_frontend/core/di/service_locator.dart'; // TODO: Remove - no longer needed
import 'package:aico_frontend/core/theme/theme_data_factory.dart';
import 'package:aico_frontend/core/theme/theme_manager.dart';
// import 'package:aico_frontend/presentation/blocs/settings/settings_bloc.dart'; // TODO: Replace with Riverpod settings provider
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/// Concrete implementation of ThemeManager for AICO
/// TODO: Migrate to Riverpod providers for settings management
class AicoThemeManager implements ThemeManager {
  // final SettingsBloc _settingsBloc; // TODO: Replace with Riverpod settings provider
  final StreamController<ThemeMode> _themeController = StreamController<ThemeMode>.broadcast();
  // StreamSubscription<SettingsState>? _settingsSubscription; // TODO: Replace with Riverpod listener
  
  ThemeMode _currentMode = ThemeMode.system;
  bool _isHighContrast = false;
  ThemeData? _cachedLightTheme;
  ThemeData? _cachedDarkTheme;
  ThemeData? _cachedHighContrastLightTheme;
  ThemeData? _cachedHighContrastDarkTheme;
  bool _disposed = false;

  AicoThemeManager() {
    // TODO: Initialize from Riverpod settings provider
    _initializeFromSettings();
    // TODO: Listen to Riverpod settings changes
    // _listenToSettingsChanges();
  }

  /// Factory constructor using service locator
  // TODO: Remove when migrated to Riverpod providers
  // factory AicoThemeManager.fromServiceLocator() {
  //   return AicoThemeManager(
  //     settingsBloc: ref.read(settingsBlocProvider),
  //   );
  // }

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
    
    // TODO: Persist theme change to Riverpod settings provider
    // ref.read(settingsProvider.notifier).updateTheme(_themeModeToString(mode));
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
    
    // TODO: Persist high contrast change to Riverpod settings provider
    // ref.read(settingsProvider.notifier).updateHighContrast(enabled);
    
    await _updateSystemUIOverlay();
    _themeController.add(_currentMode);
  }

  @override
  Future<void> resetTheme() async {
    _currentMode = ThemeMode.system;
    _isHighContrast = false;
    _clearThemeCache();
    
    // TODO: Reset in Riverpod settings provider
    // ref.read(settingsProvider.notifier).resetTheme();
    
    await _updateSystemUIOverlay();
  }

  /// Initialize theme settings from Riverpod settings provider
  void _initializeFromSettings() {
    // TODO: Initialize from Riverpod settings provider
    // final settings = ref.read(settingsProvider);
    // _currentMode = _stringToThemeMode(settings.theme);
    // _isHighContrast = settings.highContrastEnabled;
    
    // Default values for now
    _currentMode = ThemeMode.system;
    _isHighContrast = false;
    
    // Update system UI overlay
    _updateSystemUIOverlay();
  }

  // TODO: Remove - replaced with Riverpod listeners
  // void _listenToSettingsChanges() {
  //   // Will be replaced with Riverpod ref.listen in widget context
  // }

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
    
    // TODO: Remove when migrated to Riverpod
    // _settingsSubscription?.cancel();
    // _settingsSubscription = null;
    
    if (!_themeController.isClosed) {
      _themeController.close();
    }
  }
}
