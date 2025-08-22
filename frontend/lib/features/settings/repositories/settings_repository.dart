import '../../../core/services/local_storage.dart';
import '../../../core/utils/repository_factory.dart';
import '../models/settings_state.dart';

/// Repository for managing app settings persistence
/// Handles local storage of user preferences and configuration
class SettingsRepository implements Disposable {
  final LocalStorage _localStorage;

  SettingsRepository({
    required LocalStorage localStorage,
  }) : _localStorage = localStorage;

  /// Load settings from local storage
  Future<AppSettings> loadSettings() async {
    try {
      final data = await _localStorage.loadState('app_settings');
      if (data != null) {
        return AppSettings.fromJson(data);
      }
      return const AppSettings(); // Return default settings
    } catch (e) {
      throw SettingsException('Failed to load settings: $e');
    }
  }

  /// Save settings to local storage
  Future<void> saveSettings(AppSettings settings) async {
    try {
      await _localStorage.saveState('app_settings', settings.toJson());
    } catch (e) {
      throw SettingsException('Failed to save settings: $e');
    }
  }

  /// Reset settings to defaults
  Future<void> resetSettings() async {
    try {
      const defaultSettings = AppSettings();
      await saveSettings(defaultSettings);
    } catch (e) {
      throw SettingsException('Failed to reset settings: $e');
    }
  }

  /// Export settings as JSON
  Future<Map<String, dynamic>> exportSettings() async {
    try {
      final settings = await loadSettings();
      return {
        'version': '1.0.0',
        'exportedAt': DateTime.now().toIso8601String(),
        'settings': settings.toJson(),
      };
    } catch (e) {
      throw SettingsException('Failed to export settings: $e');
    }
  }

  /// Import settings from JSON
  Future<void> importSettings(Map<String, dynamic> data) async {
    try {
      // Validate import data
      if (!data.containsKey('settings')) {
        throw SettingsException('Invalid import data: missing settings');
      }

      final settingsData = data['settings'] as Map<String, dynamic>;
      final settings = AppSettings.fromJson(settingsData);
      
      await saveSettings(settings);
    } catch (e) {
      throw SettingsException('Failed to import settings: $e');
    }
  }

  /// Get specific setting value
  Future<T?> getSetting<T>(String key) async {
    try {
      final settings = await loadSettings();
      
      // Check built-in settings first
      switch (key) {
        case 'theme':
          return settings.theme as T;
        case 'language':
          return settings.language as T;
        case 'notificationsEnabled':
          return settings.notificationsEnabled as T;
        case 'autoConnect':
          return settings.autoConnect as T;
        case 'defaultServerUrl':
          return settings.defaultServerUrl as T;
        default:
          // Check custom settings
          return settings.customSettings[key] as T?;
      }
    } catch (e) {
      throw SettingsException('Failed to get setting $key: $e');
    }
  }

  /// Set specific setting value
  Future<void> setSetting<T>(String key, T value) async {
    try {
      final currentSettings = await loadSettings();
      AppSettings updatedSettings;

      // Update built-in settings
      switch (key) {
        case 'theme':
          updatedSettings = currentSettings.copyWith(theme: value as String);
          break;
        case 'language':
          updatedSettings = currentSettings.copyWith(language: value as String);
          break;
        case 'notificationsEnabled':
          updatedSettings = currentSettings.copyWith(notificationsEnabled: value as bool);
          break;
        case 'autoConnect':
          updatedSettings = currentSettings.copyWith(autoConnect: value as bool);
          break;
        case 'defaultServerUrl':
          updatedSettings = currentSettings.copyWith(defaultServerUrl: value as String);
          break;
        default:
          // Update custom settings
          final customSettings = Map<String, dynamic>.from(currentSettings.customSettings);
          customSettings[key] = value;
          updatedSettings = currentSettings.copyWith(customSettings: customSettings);
          break;
      }

      await saveSettings(updatedSettings);
    } catch (e) {
      throw SettingsException('Failed to set setting $key: $e');
    }
  }

  /// Check if settings exist in storage
  Future<bool> hasSettings() async {
    try {
      final data = await _localStorage.loadState('app_settings');
      return data != null;
    } catch (e) {
      return false;
    }
  }

  @override
  Future<void> dispose() async {
    // Clean up any resources if needed
  }
}

/// Exception for settings-related errors
class SettingsException implements Exception {
  final String message;
  const SettingsException(this.message);

  @override
  String toString() => 'SettingsException: $message';
}
