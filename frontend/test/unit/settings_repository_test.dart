import 'package:aico_frontend/core/services/local_storage.dart';
import 'package:aico_frontend/features/settings/models/settings_state.dart';
import 'package:aico_frontend/features/settings/repositories/settings_repository.dart';
import 'package:flutter_test/flutter_test.dart';

class FakeLocalStorage extends LocalStorage {
  final Map<String, Map<String, dynamic>> _storage = {};
  final bool shouldThrow;

  FakeLocalStorage({this.shouldThrow = false});

  @override
  Future<void> saveState(String key, Map<String, dynamic> data) async {
    if (shouldThrow) throw Exception('Storage save failed');
    _storage[key] = Map.from(data);
  }

  @override
  Future<Map<String, dynamic>?> loadState(String key) async {
    if (shouldThrow) throw Exception('Storage load failed');
    return _storage[key];
  }

  @override
  Future<void> savePreferences(Map<String, dynamic> preferences) async {
    if (shouldThrow) throw Exception('Storage save failed');
    _storage['preferences'] = Map.from(preferences);
  }

  @override
  Future<Map<String, dynamic>?> loadPreferences() async {
    if (shouldThrow) throw Exception('Storage load failed');
    return _storage['preferences'];
  }

  @override
  Future<void> saveCache(String key, Map<String, dynamic> data) async {
    if (shouldThrow) throw Exception('Storage save failed');
    _storage['cache_$key'] = Map.from(data);
  }

  @override
  Future<Map<String, dynamic>?> loadCache(String key) async {
    if (shouldThrow) throw Exception('Storage load failed');
    return _storage['cache_$key'];
  }

  @override
  Future<void> saveOfflineQueueItem(String id, Map<String, dynamic> item) async {
    if (shouldThrow) throw Exception('Storage save failed');
    _storage['queue_$id'] = Map.from(item);
  }

  @override
  Future<List<Map<String, dynamic>>> loadOfflineQueue() async {
    if (shouldThrow) throw Exception('Storage load failed');
    return _storage.entries
        .where((e) => e.key.startsWith('queue_'))
        .map((e) => e.value)
        .toList();
  }

  @override
  Future<void> removeOfflineQueueItem(String id) async {
    if (shouldThrow) throw Exception('Storage remove failed');
    _storage.remove('queue_$id');
  }

  @override
  Future<void> clearCache() async {
    if (shouldThrow) throw Exception('Storage clear failed');
    _storage.removeWhere((key, value) => key.startsWith('cache_'));
  }

  @override
  Future<void> clearAllState() async {
    if (shouldThrow) throw Exception('Storage clear all failed');
    _storage.clear();
  }

  @override
  Future<StorageStats> getStorageStats() async {
    if (shouldThrow) throw Exception('Storage stats failed');
    return const StorageStats(
      stateSize: 1024,
      cacheSize: 512,
      queueSize: 256,
      totalSize: 1792,
    );
  }
}

void main() {
  group('SettingsRepository', () {
    late SettingsRepository repository;
    late FakeLocalStorage localStorage;

    setUp(() {
      localStorage = FakeLocalStorage();
      repository = SettingsRepository(localStorage: localStorage);
    });

    group('loadSettings', () {
      test('returns default settings when no data exists', () async {
        final settings = await repository.loadSettings();
        expect(settings, isA<AppSettings>());
        expect(settings.theme, 'system');
        expect(settings.language, 'en');
      });

      test('returns saved settings when data exists', () async {
        // Pre-populate storage
        await localStorage.saveState('app_settings', {
          'theme': 'dark',
          'language': 'es',
          'customSettings': {'key1': 'value1'},
        });

        final settings = await repository.loadSettings();
        expect(settings.theme, 'dark');
        expect(settings.language, 'es');
        expect(settings.customSettings['key1'], 'value1');
      });

      test('returns defaults when data is cleared', () async {
        // Pre-populate storage
        await localStorage.saveState('app_settings', {
          'theme': 'dark',
          'language': 'es',
          'customSettings': {'key1': 'value1'},
        });

        await repository.resetSettings();

        final settings = await repository.loadSettings();
        expect(settings.theme, 'system'); // default
        expect(settings.language, 'en'); // default
      });

      test('throws SettingsException when storage fails', () async {
        localStorage = FakeLocalStorage(shouldThrow: true);
        repository = SettingsRepository(localStorage: localStorage);

        expect(
          () => repository.loadSettings(),
          throwsA(isA<SettingsException>()),
        );
      });
    });

    group('saveSettings', () {
      test('saves settings to storage', () async {
        const settings = AppSettings(
          theme: 'light',
          customSettings: {'test': 'value'},
        );

        await repository.saveSettings(settings);

        // Verify storage was called
        final stored = await localStorage.loadState('app_settings');
        expect(stored!['theme'], 'light');
        expect(stored['customSettings']['test'], 'value');
      });

      test('resets settings to defaults', () async {
        // First save some settings
        const settings = AppSettings(
          theme: 'dark',
          language: 'es',
        );
        await repository.saveSettings(settings);

        // Reset settings
        await repository.resetSettings();

        // Verify settings are reset to defaults
        final resetSettings = await repository.loadSettings();
        expect(resetSettings.theme, 'system'); // default
        expect(resetSettings.language, 'en'); // default
      });

      test('throws SettingsException when storage fails', () async {
        localStorage = FakeLocalStorage(shouldThrow: true);
        repository = SettingsRepository(localStorage: localStorage);

        const settings = AppSettings();
        expect(
          () => repository.saveSettings(settings),
          throwsA(isA<SettingsException>()),
        );
      });
    });

    group('resetSettings', () {
      test('resets settings to defaults', () async {
        // Pre-populate storage
        await localStorage.saveState('app_settings', {'theme': 'dark'});

        await repository.resetSettings();

        final resetSettings = await repository.loadSettings();
        expect(resetSettings.theme, 'system'); // default
      });

      test('throws SettingsException when storage fails', () async {
        localStorage = FakeLocalStorage(shouldThrow: true);
        repository = SettingsRepository(localStorage: localStorage);

        expect(
          () => repository.resetSettings(),
          throwsA(isA<SettingsException>()),
        );
      });
    });

    group('exportSettings', () {
      test('returns settings data for export', () async {
        const settings = AppSettings(
          theme: 'dark',
          language: 'fr',
        );
        await repository.saveSettings(settings);

        final exported = await repository.exportSettings();
        expect(exported['settings']['theme'], 'dark');
        expect(exported['exportedAt'], isA<String>());
        expect(exported['version'], '1.0.0');
      });

      test('throws SettingsException when load fails', () async {
        localStorage = FakeLocalStorage(shouldThrow: true);
        repository = SettingsRepository(localStorage: localStorage);

        expect(
          () => repository.exportSettings(),
          throwsA(isA<SettingsException>()),
        );
      });
    });

    group('importSettings', () {
      test('imports valid settings data', () async {
        final importData = {
          'settings': {
            'theme': 'light',
            'language': 'ja',
            'customSettings': {'imported': 'value'},
          },
        };

        await repository.importSettings(importData);

        final settings = await repository.loadSettings();
        expect(settings.theme, 'light');
        expect(settings.language, 'ja');
        expect(settings.customSettings['imported'], 'value');
      });

      test('throws SettingsException for invalid import data', () async {
        final invalidData = {'invalid': 'data'};

        expect(
          () => repository.importSettings(invalidData),
          throwsA(isA<SettingsException>()),
        );
      });

      test('throws SettingsException when save fails', () async {
        localStorage = FakeLocalStorage(shouldThrow: true);
        repository = SettingsRepository(localStorage: localStorage);

        final importData = {
          'settings': {
            'theme': 'light',
            'language': 'en',
          },
        };

        expect(
          () => repository.importSettings(importData),
          throwsA(isA<SettingsException>()),
        );
      });
    });

    group('hasSettings', () {
      test('returns true when settings exist', () async {
        await localStorage.saveState('app_settings', {'theme': 'dark'});

        final hasSettings = await repository.hasSettings();
        expect(hasSettings, isTrue);
      });

      test('returns false when no settings exist', () async {
        final hasSettings = await repository.hasSettings();
        expect(hasSettings, isFalse);
      });

      test('returns false when storage fails', () async {
        localStorage = FakeLocalStorage(shouldThrow: true);
        repository = SettingsRepository(localStorage: localStorage);

        final hasSettings = await repository.hasSettings();
        expect(hasSettings, isFalse);
      });
    });

    group('getSetting', () {
      test('returns specific setting value', () async {
        const settings = AppSettings(
          theme: 'dark',
          language: 'es',
        );
        await repository.saveSettings(settings);

        final theme = await repository.getSetting<String>('theme');
        final language = await repository.getSetting<String>('language');

        expect(theme, 'dark');
        expect(language, 'es');
      });

      test('returns null for non-existent setting', () async {
        const settings = AppSettings();
        await repository.saveSettings(settings);

        final nonExistent = await repository.getSetting<String>('non_existent');
        expect(nonExistent, isNull);
      });

      test('throws SettingsException when load fails', () async {
        localStorage = FakeLocalStorage(shouldThrow: true);
        repository = SettingsRepository(localStorage: localStorage);

        expect(
          () => repository.getSetting<String>('theme'),
          throwsA(isA<SettingsException>()),
        );
      });
    });

    group('setSetting', () {
      test('updates specific setting value', () async {
        const initialSettings = AppSettings(theme: 'light');
        await repository.saveSettings(initialSettings);

        await repository.setSetting('theme', 'dark');

        final updatedSettings = await repository.loadSettings();
        expect(updatedSettings.theme, 'dark');
      });

      test('adds custom setting', () async {
        const initialSettings = AppSettings();
        await repository.saveSettings(initialSettings);

        await repository.setSetting('new_custom', 'new_value');

        final updatedSettings = await repository.loadSettings();
        expect(updatedSettings.customSettings['new_custom'], 'new_value');
      });

      test('throws SettingsException when load fails', () async {
        localStorage = FakeLocalStorage(shouldThrow: true);
        repository = SettingsRepository(localStorage: localStorage);

        expect(
          () => repository.setSetting('theme', 'dark'),
          throwsA(isA<SettingsException>()),
        );
      });
    });

    group('dispose', () {
      test('completes without error', () async {
        await expectLater(repository.dispose(), completes);
      });
    });
  });
}
