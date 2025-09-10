import 'package:aico_frontend/core/services/storage_service.dart';

/// Service for managing application settings
class SettingsService {
  final StorageService _storageService;
  
  static const String _settingsPrefix = 'settings_';
  
  // Default settings
  static const Map<String, dynamic> _defaults = {
    'theme_mode': 'system',
    'api_base_url': 'http://localhost:8771/api/v1',
    'websocket_url': 'ws://localhost:8771/ws',
    'auto_connect': true,
    'encryption_enabled': true,
    'offline_mode': false,
    'debug_mode': false,
    'max_retry_attempts': 3,
    'connection_timeout': 30,
    'heartbeat_interval': 30,
  };

  SettingsService({required StorageService storageService})
      : _storageService = storageService;

  /// Initialize the settings service
  Future<void> initialize() async {
    // Ensure storage service is initialized
    if (!_storageService.isInitialized) {
      await _storageService.initialize();
    }
    
    // Set default values for any missing settings
    await _ensureDefaults();
  }

  /// Get a setting value with type safety
  T getSetting<T>(String key, {T? defaultValue}) {
    final storageKey = _settingsPrefix + key;
    
    // Try to get from storage first
    final storedValue = _getStoredValue<T>(storageKey);
    if (storedValue != null) {
      return storedValue;
    }
    
    // Fall back to provided default or global default
    if (defaultValue != null) {
      return defaultValue;
    }
    
    // Fall back to global defaults
    if (_defaults.containsKey(key)) {
      return _defaults[key] as T;
    }
    
    throw ArgumentError('No default value found for setting: $key');
  }

  /// Set a setting value
  Future<bool> setSetting<T>(String key, T value) async {
    final storageKey = _settingsPrefix + key;
    return await _setStoredValue<T>(storageKey, value);
  }

  /// Remove a setting (revert to default)
  Future<bool> removeSetting(String key) async {
    final storageKey = _settingsPrefix + key;
    return await _storageService.remove(storageKey);
  }

  /// Get all settings as a map
  Map<String, dynamic> getAllSettings() {
    final settings = <String, dynamic>{};
    final keys = _storageService.getKeys();
    
    for (final key in keys) {
      if (key.startsWith(_settingsPrefix)) {
        final settingKey = key.substring(_settingsPrefix.length);
        final value = _getStoredValue(key);
        if (value != null) {
          settings[settingKey] = value;
        }
      }
    }
    
    // Add defaults for missing keys
    for (final entry in _defaults.entries) {
      if (!settings.containsKey(entry.key)) {
        settings[entry.key] = entry.value;
      }
    }
    
    return settings;
  }

  /// Reset all settings to defaults
  Future<void> resetToDefaults() async {
    final keys = _storageService.getKeys();
    
    // Remove all settings keys
    for (final key in keys) {
      if (key.startsWith(_settingsPrefix)) {
        await _storageService.remove(key);
      }
    }
    
    // Restore defaults
    await _ensureDefaults();
  }

  /// Export settings as JSON
  Map<String, dynamic> exportSettings() {
    return getAllSettings();
  }

  /// Import settings from JSON
  Future<void> importSettings(Map<String, dynamic> settings) async {
    for (final entry in settings.entries) {
      await setSetting(entry.key, entry.value);
    }
  }

  // Convenience getters for common settings
  String get themeMode => getSetting<String>('theme_mode');
  String get apiBaseUrl => getSetting<String>('api_base_url');
  String get websocketUrl => getSetting<String>('websocket_url');
  bool get autoConnect => getSetting<bool>('auto_connect');
  bool get encryptionEnabled => getSetting<bool>('encryption_enabled');
  bool get offlineMode => getSetting<bool>('offline_mode');
  bool get debugMode => getSetting<bool>('debug_mode');
  int get maxRetryAttempts => getSetting<int>('max_retry_attempts');
  int get connectionTimeout => getSetting<int>('connection_timeout');
  int get heartbeatInterval => getSetting<int>('heartbeat_interval');

  // Convenience setters for common settings
  Future<bool> setThemeMode(String mode) => setSetting('theme_mode', mode);
  Future<bool> setApiBaseUrl(String url) => setSetting('api_base_url', url);
  Future<bool> setWebsocketUrl(String url) => setSetting('websocket_url', url);
  Future<bool> setAutoConnect(bool enabled) => setSetting('auto_connect', enabled);
  Future<bool> setEncryptionEnabled(bool enabled) => setSetting('encryption_enabled', enabled);
  Future<bool> setOfflineMode(bool enabled) => setSetting('offline_mode', enabled);
  Future<bool> setDebugMode(bool enabled) => setSetting('debug_mode', enabled);
  Future<bool> setMaxRetryAttempts(int attempts) => setSetting('max_retry_attempts', attempts);
  Future<bool> setConnectionTimeout(int timeout) => setSetting('connection_timeout', timeout);
  Future<bool> setHeartbeatInterval(int interval) => setSetting('heartbeat_interval', interval);

  /// Ensure default values are set
  Future<void> _ensureDefaults() async {
    for (final entry in _defaults.entries) {
      final storageKey = _settingsPrefix + entry.key;
      if (!_storageService.containsKey(storageKey)) {
        await _setStoredValue(storageKey, entry.value);
      }
    }
  }

  /// Get stored value with type handling
  T? _getStoredValue<T>(String key) {
    if (T == String) {
      return _storageService.getString(key) as T?;
    } else if (T == int) {
      return _storageService.getInt(key) as T?;
    } else if (T == bool) {
      return _storageService.getBool(key) as T?;
    } else if (T == double) {
      return _storageService.getDouble(key) as T?;
    } else if (T == List<String>) {
      return _storageService.getStringList(key) as T?;
    } else {
      // Try JSON for complex types
      final json = _storageService.getJson(key);
      return json as T?;
    }
  }

  /// Set stored value with type handling
  Future<bool> _setStoredValue<T>(String key, T value) async {
    if (T == String) {
      return await _storageService.setString(key, value as String);
    } else if (T == int) {
      return await _storageService.setInt(key, value as int);
    } else if (T == bool) {
      return await _storageService.setBool(key, value as bool);
    } else if (T == double) {
      return await _storageService.setDouble(key, value as double);
    } else if (T == List<String>) {
      return await _storageService.setStringList(key, value as List<String>);
    } else {
      // Store as JSON for complex types
      return await _storageService.setJson(key, value as Map<String, dynamic>);
    }
  }

  /// Dispose of resources
  Future<void> dispose() async {
    // Settings service doesn't need explicit disposal
  }
}
