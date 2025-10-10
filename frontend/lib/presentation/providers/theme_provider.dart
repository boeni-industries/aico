import 'package:aico_frontend/core/theme/aico_theme_manager.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'theme_provider.g.dart';

/// Theme manager provider
@riverpod
AicoThemeManager themeManager(Ref ref) {
  return AicoThemeManager();
}

/// Current theme data provider
@riverpod
ThemeData currentTheme(Ref ref) {
  final themeManager = ref.watch(themeManagerProvider);
  return themeManager.getCurrentTheme();
}

/// Light theme provider
@riverpod
ThemeData lightTheme(Ref ref) {
  final themeManager = ref.watch(themeManagerProvider);
  return themeManager.generateLightTheme();
}

/// Dark theme provider
@riverpod
ThemeData darkTheme(Ref ref) {
  final themeManager = ref.watch(themeManagerProvider);
  return themeManager.generateDarkTheme();
}

/// High contrast light theme provider
@riverpod
ThemeData highContrastLightTheme(Ref ref) {
  final themeManager = ref.watch(themeManagerProvider);
  return themeManager.generateHighContrastLightTheme();
}

/// High contrast dark theme provider
@riverpod
ThemeData highContrastDarkTheme(Ref ref) {
  final themeManager = ref.watch(themeManagerProvider);
  return themeManager.generateHighContrastDarkTheme();
}

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
@riverpod
class ThemeController extends _$ThemeController {
  late final AicoThemeManager _themeManager;

  @override
  ThemeState build() {
    _themeManager = ref.read(themeManagerProvider);
    _initializeTheme();
    return ThemeState(
      themeMode: ThemeMode.system,
      isHighContrast: false,
      currentBrightness: Brightness.light,
    );
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
