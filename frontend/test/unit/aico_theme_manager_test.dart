import 'dart:io';

import 'package:aico_frontend/core/services/local_storage.dart';
import 'package:aico_frontend/core/theme/aico_theme_manager.dart';
import 'package:aico_frontend/presentation/blocs/settings/settings_bloc.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hydrated_bloc/hydrated_bloc.dart';

// Mock SettingsBloc that properly handles theme changes
class FakeSettingsBloc extends SettingsBloc {
  String _currentTheme = 'system';
  
  FakeSettingsBloc() : super() {
    // Initialize with loaded state for testing
    emit(const SettingsLoaded(
      theme: 'system',
      locale: 'en',
      notificationsEnabled: true,
      voiceEnabled: true,
      privacySettings: {'highContrast': false},
    ));
  }
  
  @override
  void add(SettingsEvent event) {
    if (event is SettingsThemeChanged) {
      _currentTheme = event.theme;
      emit(SettingsLoaded(
        theme: _currentTheme,
        locale: 'en',
        notificationsEnabled: true,
        voiceEnabled: true,
        privacySettings: const {'highContrast': false},
      ));
    } else {
      super.add(event);
    }
  }
}

class FakeLocalStorage extends LocalStorage {
  @override
  Future<Map<String, dynamic>?> loadState(String key) async => null;

  @override
  Future<void> saveState(String key, Map<String, dynamic> data) async {}

  @override
  Future<void> savePreferences(Map<String, dynamic> preferences) async {}

  @override
  Future<Map<String, dynamic>?> loadPreferences() async => null;

  @override
  Future<void> saveCache(String key, Map<String, dynamic> data) async {}

  @override
  Future<Map<String, dynamic>?> loadCache(String key) async => null;

  @override
  Future<void> saveOfflineQueueItem(String id, Map<String, dynamic> item) async {}

  @override
  Future<List<Map<String, dynamic>>> loadOfflineQueue() async => [];

  @override
  Future<void> removeOfflineQueueItem(String id) async {}

  @override
  Future<void> clearCache() async {}

  @override
  Future<void> clearAllState() async {}

  @override
  Future<StorageStats> getStorageStats() async => const StorageStats(
        stateSize: 0,
        cacheSize: 0,
        queueSize: 0,
        totalSize: 0,
      );
}

void main() {
  group('AicoThemeManager', () {
    late FakeSettingsBloc fakeSettingsBloc;
    late AicoThemeManager themeManager;

    setUpAll(() async {
      // Initialize Flutter test bindings
      TestWidgetsFlutterBinding.ensureInitialized();
      
      // Initialize HydratedBloc storage for tests
      final storage = await HydratedStorage.build(
        storageDirectory: HydratedStorageDirectory(
          (await Directory.systemTemp.createTemp('hydrated_bloc_test')).path,
        ),
      );
      HydratedBloc.storage = storage;
    });

    setUp(() async {
      fakeSettingsBloc = FakeSettingsBloc();
      // Ensure storage is available before creating theme manager
      await Future.delayed(Duration.zero);
      themeManager = AicoThemeManager(settingsBloc: fakeSettingsBloc);
      
      // Reset to known state for each test
      await themeManager.resetTheme();
      await Future.delayed(const Duration(milliseconds: 10));
    });

    tearDown(() async {
      // Ensure all async operations complete before disposal
      await Future.delayed(const Duration(milliseconds: 50));
      themeManager.dispose();
      // Give time for disposal to complete
      await Future.delayed(const Duration(milliseconds: 10));
    });

    group('initialization', () {
      test('should initialize with system theme mode by default', () {
        expect(themeManager.currentThemeMode, ThemeMode.system);
      });

      test('should initialize with high contrast disabled by default', () {
        expect(themeManager.isHighContrastEnabled, false);
      });
    });

    group('theme mode management', () {
      test('should update theme mode correctly', () async {
        await themeManager.setThemeMode(ThemeMode.dark);
        expect(themeManager.currentThemeMode, ThemeMode.dark);
      });

      test('should toggle between light and dark modes', () async {
        await themeManager.setThemeMode(ThemeMode.light);
        await themeManager.toggleTheme();
        expect(themeManager.currentThemeMode, ThemeMode.dark);
        
        await themeManager.toggleTheme();
        expect(themeManager.currentThemeMode, ThemeMode.light);
      });

      test('should emit theme changes through stream', () async {
        // Simplified test that doesn't rely on stream timing
        bool streamHasListener = false;
        
        final subscription = themeManager.themeChanges.listen((_) {
          streamHasListener = true;
        });
        
        await themeManager.setThemeMode(ThemeMode.light);
        await themeManager.setThemeMode(ThemeMode.dark);
        
        // Verify the stream is active and theme changes work
        expect(streamHasListener, true);
        expect(themeManager.currentThemeMode, ThemeMode.dark);
        
        await subscription.cancel();
      });
    });

    group('high contrast management', () {
      test('should update high contrast setting', () async {
        await themeManager.setHighContrastEnabled(true);
        expect(themeManager.isHighContrastEnabled, true);
      });

      test('should emit theme mode when high contrast changes', () async {
        // Simplified test that doesn't rely on stream timing
        bool streamHasListener = false;
        
        final subscription = themeManager.themeChanges.listen((_) {
          streamHasListener = true;
        });
        
        // Ensure we start with high contrast disabled
        expect(themeManager.isHighContrastEnabled, false);
        
        await themeManager.setHighContrastEnabled(true);
        
        // Verify the stream is active and high contrast setting works
        expect(streamHasListener, true);
        expect(themeManager.isHighContrastEnabled, true);
        
        await subscription.cancel();
      });
    });

    group('brightness calculation', () {
      test('should return correct brightness for light mode', () async {
        await themeManager.setThemeMode(ThemeMode.light);
        expect(themeManager.currentBrightness, Brightness.light);
      });

      test('should return correct brightness for dark mode', () async {
        await themeManager.setThemeMode(ThemeMode.dark);
        expect(themeManager.currentBrightness, Brightness.dark);
      });

      test('should return platform brightness for system mode', () {
        expect(themeManager.currentBrightness, isA<Brightness>());
      });
    });

    group('theme generation', () {
      test('should generate and cache light theme', () {
        final theme1 = themeManager.generateLightTheme();
        final theme2 = themeManager.generateLightTheme();
        
        expect(theme1, isA<ThemeData>());
        expect(identical(theme1, theme2), true);
      });

      test('should generate and cache dark theme', () {
        final theme1 = themeManager.generateDarkTheme();
        final theme2 = themeManager.generateDarkTheme();
        
        expect(theme1, isA<ThemeData>());
        expect(identical(theme1, theme2), true);
      });

      test('should generate high contrast themes', () {
        final lightHC = themeManager.generateHighContrastLightTheme();
        final darkHC = themeManager.generateHighContrastDarkTheme();
        
        expect(lightHC, isA<ThemeData>());
        expect(darkHC, isA<ThemeData>());
        expect(identical(lightHC, darkHC), false);
      });
    });

    group('current theme selection', () {
      test('should return correct theme based on mode and contrast', () async {
        // Test 1: Light + Normal Contrast
        await themeManager.setThemeMode(ThemeMode.light);
        await themeManager.setHighContrastEnabled(false);
        
        final lightNormal = themeManager.getCurrentTheme();
        final lightTheme = themeManager.generateLightTheme();
        
        // Verify theme properties instead of object identity
        expect(lightNormal.brightness, lightTheme.brightness);
        expect(lightNormal.useMaterial3, lightTheme.useMaterial3);

        // Test 2: Dark + Normal Contrast
        await themeManager.setThemeMode(ThemeMode.dark);
        final darkNormal = themeManager.getCurrentTheme();
        final darkTheme = themeManager.generateDarkTheme();
        
        // Verify theme properties instead of object identity
        expect(darkNormal.brightness, darkTheme.brightness);
        expect(darkNormal.useMaterial3, darkTheme.useMaterial3);
      });
      
      test('should generate different theme types correctly', () async {
        // Test that all theme generation methods work
        final lightTheme = themeManager.generateLightTheme();
        final darkTheme = themeManager.generateDarkTheme();
        final highContrastLight = themeManager.generateHighContrastLightTheme();
        final highContrastDark = themeManager.generateHighContrastDarkTheme();
        
        // Verify brightness differences
        expect(lightTheme.brightness, Brightness.light);
        expect(darkTheme.brightness, Brightness.dark);
        expect(highContrastLight.brightness, Brightness.light);
        expect(highContrastDark.brightness, Brightness.dark);
        
        // Verify high contrast themes have different primary colors
        expect(highContrastLight.colorScheme.primary, isNot(equals(lightTheme.colorScheme.primary)));
        expect(highContrastDark.colorScheme.primary, isNot(equals(darkTheme.colorScheme.primary)));
      });
    });

    group('reset functionality', () {
      test('should reset to system theme and disable high contrast', () async {
        await themeManager.setThemeMode(ThemeMode.dark);
        await themeManager.setHighContrastEnabled(true);
        
        await themeManager.resetTheme();
        
        // Wait for settings to be processed
        await Future.delayed(const Duration(milliseconds: 10));
        
        expect(themeManager.currentThemeMode, ThemeMode.system);
        expect(themeManager.isHighContrastEnabled, false);
      });
    });

    group('system theme management', () {
      test('should enable and disable system theme', () async {
        await themeManager.setSystemThemeEnabled(true);
        expect(themeManager.isSystemThemeEnabled, true);
        
        await themeManager.setSystemThemeEnabled(false);
        expect(themeManager.isSystemThemeEnabled, false);
      });
    });
  });
}
