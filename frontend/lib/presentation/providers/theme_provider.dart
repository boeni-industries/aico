import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:aico_frontend/core/theme/aico_theme_manager.dart';

/// Theme manager provider
final themeManagerProvider = Provider<AicoThemeManager>((ref) {
  return AicoThemeManager();
});

/// Current theme data provider
final currentThemeProvider = Provider<ThemeData>((ref) {
  final themeManager = ref.watch(themeManagerProvider);
  return themeManager.getCurrentTheme();
});

/// Light theme provider
final lightThemeProvider = Provider<ThemeData>((ref) {
  final themeManager = ref.watch(themeManagerProvider);
  return themeManager.generateLightTheme();
});

/// Dark theme provider
final darkThemeProvider = Provider<ThemeData>((ref) {
  final themeManager = ref.watch(themeManagerProvider);
  return themeManager.generateDarkTheme();
});

/// High contrast light theme provider
final highContrastLightThemeProvider = Provider<ThemeData>((ref) {
  final themeManager = ref.watch(themeManagerProvider);
  return themeManager.generateHighContrastLightTheme();
});

/// High contrast dark theme provider
final highContrastDarkThemeProvider = Provider<ThemeData>((ref) {
  final themeManager = ref.watch(themeManagerProvider);
  return themeManager.generateHighContrastDarkTheme();
});

/// Theme controller provider for managing theme changes
final themeControllerProvider = StateNotifierProvider<ThemeController, ThemeState>((ref) {
  final themeManager = ref.read(themeManagerProvider);
  return ThemeController(themeManager);
});

/// Theme state
class ThemeState {
  final ThemeMode themeMode;
  final bool isHighContrast;
  final Brightness currentBrightness;

  const ThemeState({
    required this.themeMode,
    required this.isHighContrast,
    required this.currentBrightness,
  });

  ThemeState copyWith({
    ThemeMode? themeMode,
    bool? isHighContrast,
    Brightness? currentBrightness,
  }) {
    return ThemeState(
      themeMode: themeMode ?? this.themeMode,
      isHighContrast: isHighContrast ?? this.isHighContrast,
      currentBrightness: currentBrightness ?? this.currentBrightness,
    );
  }
}

/// Theme controller for managing theme operations
class ThemeController extends StateNotifier<ThemeState> {
  final AicoThemeManager _themeManager;

  ThemeController(this._themeManager) 
    : super(ThemeState(
        themeMode: ThemeMode.system,
        isHighContrast: false,
        currentBrightness: Brightness.light,
      )) {
    _initializeTheme();
  }

  void _initializeTheme() {
    state = ThemeState(
      themeMode: _themeManager.currentThemeMode,
      isHighContrast: _themeManager.isHighContrastEnabled,
      currentBrightness: _themeManager.currentBrightness,
    );
  }

  Future<void> setThemeMode(ThemeMode mode) async {
    await _themeManager.setThemeMode(mode);
    _themeManager.updateThemeMode(mode);
    state = state.copyWith(
      themeMode: mode,
      currentBrightness: _themeManager.currentBrightness,
    );
  }

  Future<void> toggleTheme() async {
    final ThemeMode newMode;
    switch (state.themeMode) {
      case ThemeMode.light:
        newMode = ThemeMode.dark;
        break;
      case ThemeMode.dark:
        newMode = ThemeMode.light;
        break;
      case ThemeMode.system:
        // If system mode, toggle to the opposite of current system brightness
        newMode = state.currentBrightness == Brightness.light 
            ? ThemeMode.dark 
            : ThemeMode.light;
        break;
    }
    await setThemeMode(newMode);
  }

  Future<void> setSystemThemeEnabled(bool enabled) async {
    final newMode = enabled ? ThemeMode.system : ThemeMode.light;
    await setThemeMode(newMode);
  }

  Future<void> setHighContrastEnabled(bool enabled) async {
    await _themeManager.setHighContrastEnabled(enabled);
    _themeManager.updateHighContrast(enabled);
    state = state.copyWith(isHighContrast: enabled);
  }

  Future<void> resetTheme() async {
    await _themeManager.resetTheme();
    _themeManager.updateThemeMode(ThemeMode.system);
    _themeManager.updateHighContrast(false);
    state = ThemeState(
      themeMode: ThemeMode.system,
      isHighContrast: false,
      currentBrightness: _themeManager.currentBrightness,
    );
  }
}
