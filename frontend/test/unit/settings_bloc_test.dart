import 'package:aico_frontend/presentation/blocs/settings/settings_bloc.dart';
import 'package:bloc_test/bloc_test.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('SettingsBloc', () {
    late SettingsBloc settingsBloc;

    setUp(() {
      settingsBloc = SettingsBloc();
    });

    tearDown(() {
      settingsBloc.close();
    });

    test('initial state is SettingsInitial', () {
      expect(settingsBloc.state, equals(const SettingsInitial()));
    });

    group('SettingsLoad', () {
      blocTest<SettingsBloc, SettingsState>(
        'emits [SettingsLoading, SettingsLoaded] when load succeeds',
        build: () => SettingsBloc(),
        act: (bloc) => bloc.add(const SettingsLoad()),
        expect: () => [
          const SettingsLoading(),
          const SettingsLoaded(
            theme: 'system',
            locale: 'en',
            notificationsEnabled: true,
            voiceEnabled: true,
            privacySettings: {
              'dataCollection': true,
              'analytics': false,
              'personalization': true,
            },
          ),
        ],
      );
    });

    group('SettingsThemeChanged', () {
      blocTest<SettingsBloc, SettingsState>(
        'updates theme when in loaded state',
        build: () => SettingsBloc(),
        seed: () => const SettingsLoaded(
          theme: 'light',
          locale: 'en',
          notificationsEnabled: true,
          voiceEnabled: true,
          privacySettings: {},
        ),
        act: (bloc) => bloc.add(const SettingsThemeChanged('dark')),
        expect: () => [
          const SettingsLoaded(
            theme: 'dark',
            locale: 'en',
            notificationsEnabled: true,
            voiceEnabled: true,
            privacySettings: {},
          ),
        ],
      );

      blocTest<SettingsBloc, SettingsState>(
        'does nothing when not in loaded state',
        build: () => SettingsBloc(),
        act: (bloc) => bloc.add(const SettingsThemeChanged('dark')),
        expect: () => [],
      );
    });

    group('SettingsLocaleChanged', () {
      blocTest<SettingsBloc, SettingsState>(
        'updates locale when in loaded state',
        build: () => SettingsBloc(),
        seed: () => const SettingsLoaded(
          theme: 'system',
          locale: 'en',
          notificationsEnabled: true,
          voiceEnabled: true,
          privacySettings: {},
        ),
        act: (bloc) => bloc.add(const SettingsLocaleChanged('es')),
        expect: () => [
          const SettingsLoaded(
            theme: 'system',
            locale: 'es',
            notificationsEnabled: true,
            voiceEnabled: true,
            privacySettings: {},
          ),
        ],
      );

      blocTest<SettingsBloc, SettingsState>(
        'does nothing when not in loaded state',
        build: () => SettingsBloc(),
        act: (bloc) => bloc.add(const SettingsLocaleChanged('es')),
        expect: () => [],
      );
    });

    group('SettingsNotificationsChanged', () {
      blocTest<SettingsBloc, SettingsState>(
        'updates notifications when in loaded state',
        build: () => SettingsBloc(),
        seed: () => const SettingsLoaded(
          theme: 'system',
          locale: 'en',
          notificationsEnabled: true,
          voiceEnabled: true,
          privacySettings: {},
        ),
        act: (bloc) => bloc.add(const SettingsNotificationsChanged(false)),
        expect: () => [
          const SettingsLoaded(
            theme: 'system',
            locale: 'en',
            notificationsEnabled: false,
            voiceEnabled: true,
            privacySettings: {},
          ),
        ],
      );

      blocTest<SettingsBloc, SettingsState>(
        'does nothing when not in loaded state',
        build: () => SettingsBloc(),
        act: (bloc) => bloc.add(const SettingsNotificationsChanged(false)),
        expect: () => [],
      );
    });

    group('SettingsVoiceChanged', () {
      blocTest<SettingsBloc, SettingsState>(
        'updates voice when in loaded state',
        build: () => SettingsBloc(),
        seed: () => const SettingsLoaded(
          theme: 'system',
          locale: 'en',
          notificationsEnabled: true,
          voiceEnabled: true,
          privacySettings: {},
        ),
        act: (bloc) => bloc.add(const SettingsVoiceChanged(false)),
        expect: () => [
          const SettingsLoaded(
            theme: 'system',
            locale: 'en',
            notificationsEnabled: true,
            voiceEnabled: false,
            privacySettings: {},
          ),
        ],
      );

      blocTest<SettingsBloc, SettingsState>(
        'does nothing when not in loaded state',
        build: () => SettingsBloc(),
        act: (bloc) => bloc.add(const SettingsVoiceChanged(false)),
        expect: () => [],
      );
    });

    group('SettingsPrivacyChanged', () {
      blocTest<SettingsBloc, SettingsState>(
        'updates privacy settings when in loaded state',
        build: () => SettingsBloc(),
        seed: () => const SettingsLoaded(
          theme: 'system',
          locale: 'en',
          notificationsEnabled: true,
          voiceEnabled: true,
          privacySettings: {'analytics': true},
        ),
        act: (bloc) => bloc.add(const SettingsPrivacyChanged({'analytics': false, 'tracking': true})),
        expect: () => [
          const SettingsLoaded(
            theme: 'system',
            locale: 'en',
            notificationsEnabled: true,
            voiceEnabled: true,
            privacySettings: {'analytics': false, 'tracking': true},
          ),
        ],
      );

      blocTest<SettingsBloc, SettingsState>(
        'does nothing when not in loaded state',
        build: () => SettingsBloc(),
        act: (bloc) => bloc.add(const SettingsPrivacyChanged({'analytics': false})),
        expect: () => [],
      );
    });
  });
}

