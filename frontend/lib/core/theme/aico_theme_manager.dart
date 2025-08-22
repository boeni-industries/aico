import 'dart:async';

import 'package:aico_frontend/core/di/service_locator.dart';
import 'package:aico_frontend/core/theme/theme_data_factory.dart';
import 'package:aico_frontend/core/theme/theme_manager.dart';
import 'package:aico_frontend/features/settings/bloc/settings_bloc.dart';
import 'package:aico_frontend/features/settings/models/settings_event.dart';
import 'package:aico_frontend/features/settings/models/settings_state.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/// Concrete implementation of ThemeManager for AICO
/// Integrates with SettingsBloc for theme persistence and state management
class AicoThemeManager implements ThemeManager {
  final SettingsBloc _settingsBloc;
  final StreamController<ThemeMode> _themeController = StreamController<ThemeMode>.broadcast();
  StreamSubscription<SettingsState>? _settingsSubscription;
  
  ThemeMode _currentMode = ThemeMode.system;
  bool _isHighContrast = false;
  ThemeData? _cachedLightTheme;
  ThemeData? _cachedDarkTheme;
  ThemeData? _cachedHighContrastLightTheme;
  ThemeData? _cachedHighContrastDarkTheme;
  bool _disposed = false;

  AicoThemeManager({required SettingsBloc settingsBloc}) : _settingsBloc = settingsBloc {
    _initializeFromSettings();
    _listenToSettingsChanges();
  }

  /// Factory constructor using service locator
  factory AicoThemeManager.fromServiceLocator() {
    return AicoThemeManager(
      settingsBloc: ServiceLocator.get<SettingsBloc>(),
    );
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
    if (_currentMode == mode) return;

    _currentMode = mode;
    
    // Update settings bloc
    _settingsBloc.add(SettingsUpdateTheme(_themeModeToString(mode)));

    // Update system UI overlay style
    await _updateSystemUIOverlay();
    
    // Notify listeners
    _themeController.add(mode);
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
    if (_isHighContrast == enabled) return;

    _isHighContrast = enabled;
    
    // Clear cached themes to force regeneration
    _clearThemeCache();
    
    // Update settings bloc with custom setting
    _settingsBloc.add(SettingsUpdateCustom('highContrast', enabled));

    // Notify listeners
    _themeController.add(_currentMode);
  }

  @override
  Future<void> resetTheme() async {
    _currentMode = ThemeMode.system;
    _isHighContrast = false;
    _clearThemeCache();
    
    // Reset in settings
    _settingsBloc.add(SettingsUpdateTheme('system'));
    _settingsBloc.add(SettingsUpdateCustom('highContrast', false));
    
    await _updateSystemUIOverlay();
    _themeController.add(_currentMode);
  }

  /// Initialize theme settings from SettingsBloc state
  void _initializeFromSettings() {
    final state = _settingsBloc.state;
    if (state is SettingsLoaded) {
      // Load theme mode
      _currentMode = _stringToThemeMode(state.settings.theme);
      
      // Load high contrast setting
      _isHighContrast = state.settings.customSettings['highContrast'] as bool? ?? false;
      
      // Update system UI overlay
      _updateSystemUIOverlay();
    }
  }

  /// Listen to settings changes and update theme accordingly
  void _listenToSettingsChanges() {
    _settingsSubscription = _settingsBloc.stream.listen((state) {
      if (_disposed) return;
      
      if (state is SettingsLoaded) {
        bool hasChanges = false;
        
        // Check theme mode changes
        final newThemeMode = _stringToThemeMode(state.settings.theme);
        if (_currentMode != newThemeMode) {
          _currentMode = newThemeMode;
          hasChanges = true;
        }
        
        // Check high contrast changes
        final newHighContrast = state.settings.customSettings['highContrast'] as bool? ?? false;
        if (_isHighContrast != newHighContrast) {
          _isHighContrast = newHighContrast;
          _clearThemeCache();
          hasChanges = true;
        }
        
        if (hasChanges && !_disposed) {
          _updateSystemUIOverlay();
          if (!_themeController.isClosed) {
            _themeController.add(_currentMode);
          }
        }
      }
    });
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

  /// Convert ThemeMode to string for persistence
  String _themeModeToString(ThemeMode mode) {
    switch (mode) {
      case ThemeMode.light:
        return 'light';
      case ThemeMode.dark:
        return 'dark';
      case ThemeMode.system:
        return 'system';
    }
  }

  /// Convert string to ThemeMode from persistence
  ThemeMode _stringToThemeMode(String? modeString) {
    switch (modeString) {
      case 'light':
        return ThemeMode.light;
      case 'dark':
        return ThemeMode.dark;
      case 'system':
      default:
        return ThemeMode.system;
    }
  }

  /// Dispose resources
  void dispose() {
    _disposed = true;
    _settingsSubscription?.cancel();
    _settingsSubscription = null;
    if (!_themeController.isClosed) {
      _themeController.close();
    }
  }
}
