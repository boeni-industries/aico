import 'package:flutter_test/flutter_test.dart';
import 'package:bloc_test/bloc_test.dart';
import 'package:aico_ui/features/settings/bloc/settings_bloc.dart';
import 'package:aico_ui/features/settings/models/settings_event.dart';
import 'package:aico_ui/features/settings/models/settings_state.dart';
import 'package:aico_ui/features/settings/repositories/settings_repository.dart';
import 'package:hydrated_bloc/hydrated_bloc.dart';
import 'dart:io';

class FakeSettingsRepository implements SettingsRepository {
  final bool shouldThrow;
  final bool shouldThrowOnSave;
  final bool shouldThrowOnReset;
  final bool shouldThrowOnImport;
  final bool shouldThrowOnExport;
  AppSettings _currentSettings;
  
  FakeSettingsRepository({
    this.shouldThrow = false,
    this.shouldThrowOnSave = false,
    this.shouldThrowOnReset = false,
    this.shouldThrowOnImport = false,
    this.shouldThrowOnExport = false,
    AppSettings? initialSettings,
  }) : _currentSettings = initialSettings ?? const AppSettings();

  @override
  Future<AppSettings> loadSettings() async {
    if (shouldThrow) throw Exception('Load failed');
    return _currentSettings;
  }

  @override
  Future<void> saveSettings(AppSettings settings) async {
    if (shouldThrowOnSave) throw Exception('Save failed');
    _currentSettings = settings;
  }
  
  @override
  Future<void> resetSettings() async {
    if (shouldThrowOnReset) throw Exception('Reset failed');
    _currentSettings = const AppSettings();
  }
  
  @override
  Future<Map<String, dynamic>> exportSettings() async {
    if (shouldThrowOnExport) throw Exception('Export failed');
    return {
      'settings': _currentSettings.toJson(),
      'version': '1.0.0',
      'exportedAt': DateTime.now().toIso8601String(),
    };
  }
  
  @override
  Future<void> importSettings(Map<String, dynamic> data) async {
    if (shouldThrowOnImport) throw Exception('Import failed');
    final settingsData = data['settings'] as Map<String, dynamic>;
    _currentSettings = AppSettings.fromJson(settingsData);
  }
  
  @override
  Future<bool> hasSettings() async => true;
  
  @override
  Future<T?> getSetting<T>(String key) async => null;
  
  @override
  Future<void> setSetting<T>(String key, T value) async {}
  
  @override
  Future<void> dispose() async {}
}


void main() {
  setUpAll(() async {
    TestWidgetsFlutterBinding.ensureInitialized();
    final storage = await HydratedStorage.build(
      storageDirectory: HydratedStorageDirectory((await Directory.systemTemp.createTemp('hydrated_bloc_test')).path),
    );
    HydratedBloc.storage = storage;
  });
  
  group('SettingsBloc', () {
    group('SettingsLoad', () {
      blocTest<SettingsBloc, SettingsState>(
        'emits [loading, loaded] when LoadSettings succeeds',
        build: () => SettingsBloc(repository: FakeSettingsRepository()),
        act: (bloc) => bloc.add(const SettingsLoad()),
        expect: () => [isA<SettingsLoading>(), isA<SettingsLoaded>()],
      );

      blocTest<SettingsBloc, SettingsState>(
        'emits [loading, error] when LoadSettings fails',
        build: () => SettingsBloc(repository: FakeSettingsRepository(shouldThrow: true)),
        act: (bloc) => bloc.add(const SettingsLoad()),
        expect: () => [isA<SettingsLoading>(), isA<SettingsError>()],
      );
    });

    group('SettingsUpdateTheme', () {
      blocTest<SettingsBloc, SettingsState>(
        'updates theme when in loaded state',
        build: () => SettingsBloc(repository: FakeSettingsRepository()),
        seed: () => const SettingsLoaded(settings: AppSettings()),
        act: (bloc) => bloc.add(const SettingsUpdateTheme('dark')),
        expect: () => [
          isA<SettingsLoaded>().having(
            (state) => state.settings.theme,
            'theme',
            'dark',
          ),
        ],
      );

      blocTest<SettingsBloc, SettingsState>(
        'loads settings first when not in loaded state',
        build: () => SettingsBloc(repository: FakeSettingsRepository()),
        act: (bloc) => bloc.add(const SettingsUpdateTheme('dark')),
        expect: () => [isA<SettingsLoaded>()],
      );

      blocTest<SettingsBloc, SettingsState>(
        'emits error when save fails',
        build: () => SettingsBloc(repository: FakeSettingsRepository(shouldThrowOnSave: true)),
        seed: () => const SettingsLoaded(settings: AppSettings()),
        act: (bloc) => bloc.add(const SettingsUpdateTheme('dark')),
        expect: () => [isA<SettingsError>()],
      );
    });

    group('SettingsUpdateLanguage', () {
      blocTest<SettingsBloc, SettingsState>(
        'updates language when in loaded state',
        build: () => SettingsBloc(repository: FakeSettingsRepository()),
        seed: () => const SettingsLoaded(settings: AppSettings()),
        act: (bloc) => bloc.add(const SettingsUpdateLanguage('es')),
        expect: () => [
          isA<SettingsLoaded>().having(
            (state) => state.settings.language,
            'language',
            'es',
          ),
        ],
      );
    });

    group('SettingsUpdateNotifications', () {
      blocTest<SettingsBloc, SettingsState>(
        'updates notifications when in loaded state',
        build: () => SettingsBloc(repository: FakeSettingsRepository()),
        seed: () => const SettingsLoaded(settings: AppSettings()),
        act: (bloc) => bloc.add(const SettingsUpdateNotifications(false)),
        expect: () => [
          isA<SettingsLoaded>().having(
            (state) => state.settings.notificationsEnabled,
            'notificationsEnabled',
            false,
          ),
        ],
      );
    });

    group('SettingsUpdateAutoConnect', () {
      blocTest<SettingsBloc, SettingsState>(
        'updates autoConnect when in loaded state',
        build: () => SettingsBloc(repository: FakeSettingsRepository()),
        seed: () => const SettingsLoaded(settings: AppSettings()),
        act: (bloc) => bloc.add(const SettingsUpdateAutoConnect(false)),
        expect: () => [
          isA<SettingsLoaded>().having(
            (state) => state.settings.autoConnect,
            'autoConnect',
            false,
          ),
        ],
      );
    });

    group('SettingsUpdateServerUrl', () {
      blocTest<SettingsBloc, SettingsState>(
        'updates server URL when in loaded state',
        build: () => SettingsBloc(repository: FakeSettingsRepository()),
        seed: () => const SettingsLoaded(settings: AppSettings()),
        act: (bloc) => bloc.add(const SettingsUpdateServerUrl('http://custom:8000')),
        expect: () => [
          isA<SettingsLoaded>().having(
            (state) => state.settings.defaultServerUrl,
            'defaultServerUrl',
            'http://custom:8000',
          ),
        ],
      );
    });

    group('SettingsUpdateCustom', () {
      blocTest<SettingsBloc, SettingsState>(
        'updates custom setting when in loaded state',
        build: () => SettingsBloc(repository: FakeSettingsRepository()),
        seed: () => const SettingsLoaded(settings: AppSettings()),
        act: (bloc) => bloc.add(const SettingsUpdateCustom('customKey', 'customValue')),
        expect: () => [
          isA<SettingsLoaded>().having(
            (state) => state.settings.customSettings['customKey'],
            'customSettings[customKey]',
            'customValue',
          ),
        ],
      );
    });

    group('SettingsReset', () {
      blocTest<SettingsBloc, SettingsState>(
        'resets settings to defaults',
        build: () => SettingsBloc(repository: FakeSettingsRepository()),
        act: (bloc) => bloc.add(const SettingsReset()),
        expect: () => [
          isA<SettingsLoaded>().having(
            (state) => state.settings.theme,
            'theme',
            'system',
          ),
        ],
      );

      blocTest<SettingsBloc, SettingsState>(
        'emits error when reset fails',
        build: () => SettingsBloc(repository: FakeSettingsRepository(shouldThrowOnReset: true)),
        act: (bloc) => bloc.add(const SettingsReset()),
        expect: () => [isA<SettingsError>()],
      );
    });

    group('SettingsSave', () {
      blocTest<SettingsBloc, SettingsState>(
        'saves settings when in loaded state',
        build: () => SettingsBloc(repository: FakeSettingsRepository()),
        seed: () => const SettingsLoaded(settings: AppSettings(theme: 'dark')),
        act: (bloc) => bloc.add(const SettingsSave()),
        expect: () => [],
      );

      blocTest<SettingsBloc, SettingsState>(
        'emits error when save fails',
        build: () => SettingsBloc(repository: FakeSettingsRepository(shouldThrowOnSave: true)),
        seed: () => const SettingsLoaded(settings: AppSettings()),
        act: (bloc) => bloc.add(const SettingsSave()),
        expect: () => [isA<SettingsError>()],
      );

      blocTest<SettingsBloc, SettingsState>(
        'does nothing when not in loaded state',
        build: () => SettingsBloc(repository: FakeSettingsRepository()),
        act: (bloc) => bloc.add(const SettingsSave()),
        expect: () => [],
      );
    });

    group('SettingsImport', () {
      blocTest<SettingsBloc, SettingsState>(
        'imports settings successfully',
        build: () => SettingsBloc(repository: FakeSettingsRepository()),
        act: (bloc) => bloc.add(SettingsImport(const {
          'settings': {
            'theme': 'dark',
            'language': 'es',
          },
        })),
        expect: () => [
          isA<SettingsLoaded>().having(
            (state) => state.settings.theme,
            'theme',
            'dark',
          ),
        ],
      );

      blocTest<SettingsBloc, SettingsState>(
        'emits error when import fails',
        build: () => SettingsBloc(repository: FakeSettingsRepository(shouldThrowOnImport: true)),
        act: (bloc) => bloc.add(const SettingsImport({'settings': {}})),
        expect: () => [isA<SettingsError>()],
      );
    });

    group('SettingsExport', () {
      blocTest<SettingsBloc, SettingsState>(
        'exports settings without changing state',
        build: () => SettingsBloc(repository: FakeSettingsRepository()),
        act: (bloc) => bloc.add(const SettingsExport()),
        expect: () => [],
      );

      blocTest<SettingsBloc, SettingsState>(
        'emits error when export fails',
        build: () => SettingsBloc(repository: FakeSettingsRepository(shouldThrowOnExport: true)),
        act: (bloc) => bloc.add(const SettingsExport()),
        expect: () => [isA<SettingsError>()],
      );
    });

    group('JSON serialization', () {
      test('fromJson returns correct state for initial', () {
        final bloc = SettingsBloc(repository: FakeSettingsRepository());
        final state = bloc.fromJson({'type': 'initial'});
        expect(state, isA<SettingsInitial>());
      });

      test('fromJson returns correct state for loading', () {
        final bloc = SettingsBloc(repository: FakeSettingsRepository());
        final state = bloc.fromJson({'type': 'loading'});
        expect(state, isA<SettingsLoading>());
      });

      test('fromJson returns correct state for loaded', () {
        final bloc = SettingsBloc(repository: FakeSettingsRepository());
        final state = bloc.fromJson({
          'type': 'loaded',
          'settings': {
            'theme': 'dark',
            'language': 'es',
            'notificationsEnabled': false,
            'autoConnect': false,
            'defaultServerUrl': 'http://test:8000',
            'customSettings': {'key': 'value'},
          },
        });
        expect(state, isA<SettingsLoaded>());
        final loadedState = state as SettingsLoaded;
        expect(loadedState.settings.theme, 'dark');
        expect(loadedState.settings.language, 'es');
      });

      test('fromJson returns correct state for error', () {
        final bloc = SettingsBloc(repository: FakeSettingsRepository());
        final now = DateTime.now();
        final state = bloc.fromJson({
          'type': 'error',
          'message': 'Test error',
          'occurredAt': now.toIso8601String(),
        });
        expect(state, isA<SettingsError>());
        final errorState = state as SettingsError;
        expect(errorState.message, 'Test error');
        expect(errorState.occurredAt, now);
      });

      test('fromJson returns null for invalid data', () {
        final bloc = SettingsBloc(repository: FakeSettingsRepository());
        final state = bloc.fromJson({'invalid': 'data'});
        expect(state, isNull);
      });

      test('toJson returns correct JSON for states', () {
        final bloc = SettingsBloc(repository: FakeSettingsRepository());
        
        // Test initial state
        final initialJson = bloc.toJson(const SettingsInitial());
        expect(initialJson, {'type': 'initial'});
        
        // Test loaded state
        const settings = AppSettings(theme: 'dark');
        final loadedJson = bloc.toJson(const SettingsLoaded(settings: settings));
        expect(loadedJson!['type'], 'loaded');
        expect(loadedJson['settings']['theme'], 'dark');
      });
    });
  });
}

