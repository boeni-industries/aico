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
  FakeSettingsRepository({this.shouldThrow = false});

  @override
  Future<AppSettings> loadSettings() async {
    if (shouldThrow) throw Exception('error');
    return const AppSettings();
  }

  // Implement other methods as no-ops for test compatibility
  @override
  Future<void> saveSettings(AppSettings settings) async {}
  @override
  Future<void> resetSettings() async {}
  @override
  Future<Map<String, dynamic>> exportSettings() async => <String, dynamic>{};
  @override
  Future<void> importSettings(Map<String, dynamic> data) async {}
  @override
  Future<bool> hasSettings() async => false;
  @override
  Future<T?> getSetting<T>(String key) async => null;
  @override
  Future<void> dispose() async {}

  @override
  Future<void> setSetting<T>(String key, T value) async {}
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
    blocTest<SettingsBloc, SettingsState>(
      'emits [loading, loaded] when LoadSettings is added and repository returns data',
      build: () => SettingsBloc(repository: FakeSettingsRepository()),
      act: (bloc) => bloc.add(SettingsLoad()),
      expect: () => [isA<SettingsLoading>(), isA<SettingsLoaded>()],
    );

    blocTest<SettingsBloc, SettingsState>(
      'emits [loading, error] when LoadSettings fails',
      build: () => SettingsBloc(repository: FakeSettingsRepository(shouldThrow: true)),
      act: (bloc) => bloc.add(SettingsLoad()),
      expect: () => [isA<SettingsLoading>(), isA<SettingsError>()],
    );
  });
}

