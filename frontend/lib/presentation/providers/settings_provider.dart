import 'package:aico_frontend/core/providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Settings state model
class SettingsState {
  final ThemeMode themeMode;
  final bool highContrastEnabled;
  final bool notificationsEnabled;
  final String language;

  const SettingsState({
    this.themeMode = ThemeMode.system,
    this.highContrastEnabled = false,
    this.notificationsEnabled = true,
    this.language = 'en',
  });

  SettingsState copyWith({
    ThemeMode? themeMode,
    bool? highContrastEnabled,
    bool? notificationsEnabled,
    String? language,
  }) {
    return SettingsState(
      themeMode: themeMode ?? this.themeMode,
      highContrastEnabled: highContrastEnabled ?? this.highContrastEnabled,
      notificationsEnabled: notificationsEnabled ?? this.notificationsEnabled,
      language: language ?? this.language,
    );
  }

  String get theme {
    switch (themeMode) {
      case ThemeMode.light:
        return 'light';
      case ThemeMode.dark:
        return 'dark';
      case ThemeMode.system:
        return 'system';
    }
  }
}

/// Settings provider using StateNotifier
class SettingsNotifier extends StateNotifier<SettingsState> {
  final SharedPreferences _prefs;

  SettingsNotifier(this._prefs) : super(const SettingsState()) {
    _loadSettings();
  }

  void _loadSettings() {
    final themeString = _prefs.getString('theme') ?? 'system';
    final themeMode = _stringToThemeMode(themeString);
    final highContrast = _prefs.getBool('high_contrast') ?? false;
    final notifications = _prefs.getBool('notifications') ?? true;
    final language = _prefs.getString('language') ?? 'en';

    state = SettingsState(
      themeMode: themeMode,
      highContrastEnabled: highContrast,
      notificationsEnabled: notifications,
      language: language,
    );
  }

  Future<void> updateTheme(String theme) async {
    final themeMode = _stringToThemeMode(theme);
    await _prefs.setString('theme', theme);
    state = state.copyWith(themeMode: themeMode);
  }

  Future<void> updateThemeMode(ThemeMode themeMode) async {
    final themeString = _themeModeToString(themeMode);
    await _prefs.setString('theme', themeString);
    state = state.copyWith(themeMode: themeMode);
  }

  Future<void> updateHighContrast(bool enabled) async {
    await _prefs.setBool('high_contrast', enabled);
    state = state.copyWith(highContrastEnabled: enabled);
  }

  Future<void> updateNotifications(bool enabled) async {
    await _prefs.setBool('notifications', enabled);
    state = state.copyWith(notificationsEnabled: enabled);
  }

  Future<void> updateLanguage(String language) async {
    await _prefs.setString('language', language);
    state = state.copyWith(language: language);
  }

  Future<void> resetTheme() async {
    await _prefs.setString('theme', 'system');
    await _prefs.setBool('high_contrast', false);
    state = state.copyWith(
      themeMode: ThemeMode.system,
      highContrastEnabled: false,
    );
  }

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
}

/// Settings provider
final settingsProvider = StateNotifierProvider<SettingsNotifier, SettingsState>((ref) {
  final prefs = ref.watch(sharedPreferencesProvider);
  return SettingsNotifier(prefs);
});

/// Theme mode provider (convenience)
final themeModeProvider = Provider<ThemeMode>((ref) {
  return ref.watch(settingsProvider).themeMode;
});

/// High contrast provider (convenience)
final highContrastProvider = Provider<bool>((ref) {
  return ref.watch(settingsProvider).highContrastEnabled;
});
