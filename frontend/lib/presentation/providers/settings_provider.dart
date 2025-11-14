import 'package:aico_frontend/core/providers.dart';
import 'package:flutter/material.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:shared_preferences/shared_preferences.dart';

part 'settings_provider.g.dart';

/// Settings state model
class SettingsState {
  final ThemeMode themeMode;
  final bool highContrastEnabled;
  final bool notificationsEnabled;
  final bool showThinking; // Show AI thinking in right drawer
  final String language;

  const SettingsState({
    this.themeMode = ThemeMode.system,
    this.highContrastEnabled = false,
    this.notificationsEnabled = true,
    this.showThinking = true, // Default to showing thinking
    this.language = 'en',
  });

  SettingsState copyWith({
    ThemeMode? themeMode,
    bool? highContrastEnabled,
    bool? notificationsEnabled,
    bool? showThinking,
    String? language,
  }) {
    return SettingsState(
      themeMode: themeMode ?? this.themeMode,
      highContrastEnabled: highContrastEnabled ?? this.highContrastEnabled,
      notificationsEnabled: notificationsEnabled ?? this.notificationsEnabled,
      showThinking: showThinking ?? this.showThinking,
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

/// Settings provider using Notifier
@riverpod
class SettingsNotifier extends _$SettingsNotifier {
  late final SharedPreferences _prefs;

  @override
  SettingsState build() {
    _prefs = ref.watch(sharedPreferencesProvider);
    _loadSettings();
    return const SettingsState();
  }

  void _loadSettings() {
    final themeString = _prefs.getString('theme') ?? 'system';
    final themeMode = _stringToThemeMode(themeString);
    final highContrast = _prefs.getBool('high_contrast') ?? false;
    final notifications = _prefs.getBool('notifications') ?? true;
    final showThinking = _prefs.getBool('show_thinking') ?? true;
    final language = _prefs.getString('language') ?? 'en';

    state = SettingsState(
      themeMode: themeMode,
      highContrastEnabled: highContrast,
      notificationsEnabled: notifications,
      showThinking: showThinking,
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

  Future<void> updateShowThinking(bool enabled) async {
    await _prefs.setBool('show_thinking', enabled);
    state = state.copyWith(showThinking: enabled);
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

/// Theme mode provider (convenience)
@riverpod
ThemeMode themeMode(Ref ref) {
  return ref.watch(settingsProvider).themeMode;
}

/// High contrast provider (convenience)
@riverpod
bool highContrast(Ref ref) {
  return ref.watch(settingsProvider).highContrastEnabled;
}

/// Show thinking provider (convenience)
@riverpod
bool showThinking(Ref ref) {
  return ref.watch(settingsProvider).showThinking;
}
