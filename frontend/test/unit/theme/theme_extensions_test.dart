import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import '../../../lib/core/theme/theme_extensions.dart';
import '../../../lib/core/theme/theme_data_factory.dart';
import '../../../lib/core/theme/design_tokens.dart';
import '../../../lib/core/di/service_locator.dart';
import '../../../lib/core/theme/theme_manager.dart';
import '../../../lib/features/settings/bloc/settings_bloc.dart';
import '../../../lib/features/settings/repositories/settings_repository.dart';
import '../../../lib/core/services/local_storage.dart';
import '../../../lib/core/utils/aico_paths.dart';
import 'package:hydrated_bloc/hydrated_bloc.dart';
import 'package:get_it/get_it.dart';
import 'dart:io';

// Mock implementations for testing
class MockThemeManager implements ThemeManager {
  bool _isHighContrast = false;
  ThemeMode _currentMode = ThemeMode.light;
  bool _isSystemThemeEnabled = false;
  
  @override
  ThemeMode get currentThemeMode => _currentMode;
  
  @override
  bool get isHighContrastEnabled => _isHighContrast;
  
  @override
  bool get isSystemThemeEnabled => _isSystemThemeEnabled;
  
  @override
  Brightness get currentBrightness => _currentMode == ThemeMode.dark ? Brightness.dark : Brightness.light;
  
  @override
  Stream<ThemeMode> get themeChanges => Stream.value(_currentMode);
  
  @override
  ThemeData generateLightTheme() => ThemeData.light();
  
  @override
  ThemeData generateDarkTheme() => ThemeData.dark();
  
  @override
  ThemeData generateHighContrastLightTheme() => ThemeData.light();
  
  @override
  ThemeData generateHighContrastDarkTheme() => ThemeData.dark();
  
  @override
  Future<void> setThemeMode(ThemeMode mode) async {
    _currentMode = mode;
  }
  
  @override
  Future<void> toggleTheme() async {
    _currentMode = _currentMode == ThemeMode.light ? ThemeMode.dark : ThemeMode.light;
  }
  
  @override
  Future<void> setSystemThemeEnabled(bool enabled) async {
    _isSystemThemeEnabled = enabled;
  }
  
  @override
  Future<void> setHighContrastEnabled(bool enabled) async {
    _isHighContrast = enabled;
  }
  
  @override
  Future<void> resetTheme() async {
    _currentMode = ThemeMode.system;
    _isHighContrast = false;
    _isSystemThemeEnabled = false;
  }
  
  void setHighContrast(bool enabled) {
    _isHighContrast = enabled;
  }
  
  void setCurrentThemeMode(ThemeMode mode) {
    _currentMode = mode;
  }
}

class MockSettingsBloc extends SettingsBloc {
  MockSettingsBloc() : super(repository: MockSettingsRepository());
}

class MockSettingsRepository extends SettingsRepository {
  MockSettingsRepository() : super(localStorage: MockLocalStorage());
}

class MockLocalStorage extends LocalStorage {
  @override
  Future<Map<String, dynamic>?> loadState(String key) async => null;
  
  @override
  Future<void> saveState(String key, Map<String, dynamic> data) async {}
}

void main() {
  group('AicoThemeExtensions', () {
    late Widget testWidget;
    late BuildContext testContext;

    setUpAll(() async {
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
      // Reset ServiceLocator and set up test configuration
      await ServiceLocator.reset();
      
      // Set up test configuration for AICOPaths to avoid null check errors
      final tempDir = await Directory.systemTemp.createTemp('aico_test');
      AICOPaths.setTestConfig(
        baseDataDir: tempDir.path,
        config: {
          'system': {
            'paths': {
              'frontend_subdirectory': 'frontend',
              'cache_subdirectory': 'cache',
              'logs_subdirectory': 'logs',
            }
          }
        },
      );
      
      await ServiceLocator.initialize();
      
      // Override ThemeManager with mock for testing
      GetIt.instance.unregister<ThemeManager>();
      GetIt.instance.registerLazySingleton<ThemeManager>(() => MockThemeManager());
      
      // Set up test widget after ServiceLocator is ready
      testWidget = MaterialApp(
        theme: AicoThemeDataFactory.generateLightTheme(),
        darkTheme: AicoThemeDataFactory.generateDarkTheme(),
        home: Builder(
          builder: (context) {
            testContext = context;
            return const Scaffold(body: Text('Test'));
          },
        ),
      );
    });

    group('theme access extensions', () {
      testWidgets('should provide access to theme data', (tester) async {
        await tester.pumpWidget(testWidget);

        expect(testContext.theme, isA<ThemeData>());
        expect(testContext.colorScheme, isA<ColorScheme>());
        expect(testContext.textTheme, isA<TextTheme>());
      });

      testWidgets('should detect theme brightness correctly', (tester) async {
        // Test light theme
        final lightTheme = AicoThemeDataFactory.generateLightTheme();
        await tester.pumpWidget(MaterialApp(
          theme: lightTheme,
          home: Builder(
            builder: (context) {
              expect(context.theme.brightness, Brightness.light);
              expect(context.isLightTheme, true);
              expect(context.isDarkTheme, false);
              return const SizedBox();
            },
          ),
        ));

        // Test dark theme - verify the theme data directly
        final darkTheme = AicoThemeDataFactory.generateDarkTheme();
        
        // Direct theme data verification
        expect(darkTheme.brightness, Brightness.dark);
        expect(darkTheme.colorScheme.brightness, Brightness.dark);
        
        // Test with Theme widget to override MaterialApp theme
        await tester.pumpWidget(MaterialApp(
          home: Theme(
            data: darkTheme,
            child: Builder(
              builder: (context) {
                expect(context.theme.brightness, Brightness.dark);
                expect(context.isDarkTheme, true);
                expect(context.isLightTheme, false);
                return const SizedBox();
              },
            ),
          ),
        ));
      });

      testWidgets('should detect high contrast themes', (tester) async {
        final mockThemeManager = GetIt.instance<ThemeManager>() as MockThemeManager;
        
        // Test normal theme
        mockThemeManager.setHighContrast(false);
        await tester.pumpWidget(MaterialApp(
          theme: AicoThemeDataFactory.generateLightTheme(),
          home: Builder(
            builder: (context) {
              expect(context.isHighContrast, false);
              return const SizedBox();
            },
          ),
        ));

        // Test high contrast theme
        mockThemeManager.setHighContrast(true);
        await tester.pumpWidget(MaterialApp(
          theme: AicoThemeDataFactory.generateHighContrastLightTheme(),
          home: Builder(
            builder: (context) {
              expect(context.isHighContrast, true);
              return const SizedBox();
            },
          ),
        ));
      });
    });

    group('semantic colors', () {
      testWidgets('should provide semantic color access', (tester) async {
        await tester.pumpWidget(testWidget);

        final semanticColors = testContext.semanticColors;
        
        expect(semanticColors.primary, isA<Color>());
        expect(semanticColors.secondary, isA<Color>());
        expect(semanticColors.accent, isA<Color>());
        expect(semanticColors.success, isA<Color>());
        expect(semanticColors.warning, isA<Color>());
        expect(semanticColors.error, isA<Color>());
        expect(semanticColors.info, isA<Color>());
      });

      testWidgets('should adapt semantic colors to theme brightness', (tester) async {
        // Test that semantic colors are accessible in both themes
        await tester.pumpWidget(MaterialApp(
          theme: AicoThemeDataFactory.generateLightTheme(),
          home: Builder(
            builder: (context) {
              final colors = context.semanticColors;
              expect(colors.primary, isNotNull);
              expect(colors.success, isNotNull);
              expect(colors.warning, isNotNull);
              expect(colors.error, isNotNull);
              return const SizedBox();
            },
          ),
        ));
      });

      testWidgets('should provide consistent semantic colors', (tester) async {
        await tester.pumpWidget(testWidget);

        final semanticColors = testContext.semanticColors;
        
        // Success should be green-ish
        expect(semanticColors.success.green, greaterThan(semanticColors.success.red));
        expect(semanticColors.success.green, greaterThan(semanticColors.success.blue));
        
        // Error should be red-ish
        expect(semanticColors.error.red, greaterThan(semanticColors.error.green));
        expect(semanticColors.error.red, greaterThan(semanticColors.error.blue));
        
        // Warning should be yellow/orange-ish
        expect(semanticColors.warning.red + semanticColors.warning.green, 
               greaterThan(semanticColors.warning.blue * 2));
      });
    });

    group('spacing extensions', () {
      testWidgets('should provide spacing values', (tester) async {
        await tester.pumpWidget(testWidget);

        final spacing = testContext.spacing;
        
        expect(spacing.xs, AicoDesignTokens.spaceXs);
        expect(spacing.sm, AicoDesignTokens.spaceSm);
        expect(spacing.md, AicoDesignTokens.spaceMd);
        expect(spacing.lg, AicoDesignTokens.spaceLg);
        expect(spacing.xl, AicoDesignTokens.spaceXl);
        expect(spacing.xxl, AicoDesignTokens.spaceXxl);
      });

      testWidgets('should provide padding EdgeInsets', (tester) async {
        await tester.pumpWidget(testWidget);

        final spacing = testContext.spacing;
        
        expect(spacing.paddingXs, const EdgeInsets.all(AicoDesignTokens.spaceXs));
        expect(spacing.paddingSm, const EdgeInsets.all(AicoDesignTokens.spaceSm));
        expect(spacing.paddingMd, const EdgeInsets.all(AicoDesignTokens.spaceMd));
        expect(spacing.paddingLg, const EdgeInsets.all(AicoDesignTokens.spaceLg));
        expect(spacing.paddingXl, const EdgeInsets.all(AicoDesignTokens.spaceXl));
        expect(spacing.paddingXxl, const EdgeInsets.all(AicoDesignTokens.spaceXxl));
      });

      testWidgets('should provide margin EdgeInsets', (tester) async {
        await tester.pumpWidget(testWidget);

        final spacing = testContext.spacing;
        
        expect(spacing.marginXs, isA<EdgeInsets>());
        expect(spacing.marginSm, isA<EdgeInsets>());
        expect(spacing.marginMd, isA<EdgeInsets>());
        expect(spacing.marginLg, isA<EdgeInsets>());
        expect(spacing.marginXl, isA<EdgeInsets>());
        expect(spacing.marginXxl, isA<EdgeInsets>());
      });
    });

    group('animation extensions', () {
      testWidgets('should provide animation durations', (tester) async {
        await tester.pumpWidget(testWidget);

        final animations = testContext.animations;
        
        expect(animations.fast, AicoDesignTokens.durationFast);
        expect(animations.medium, AicoDesignTokens.durationMedium);
        expect(animations.slow, AicoDesignTokens.durationSlow);
      });

      testWidgets('should provide animation curves', (tester) async {
        await tester.pumpWidget(testWidget);

        final animations = testContext.animations;
        
        expect(animations.easeIn, AicoDesignTokens.curveEaseIn);
        expect(animations.easeOut, AicoDesignTokens.curveEaseOut);
        expect(animations.easeInOut, AicoDesignTokens.curveEaseInOut);
      });
    });

    group('elevation extensions', () {
      testWidgets('should provide elevation levels', (tester) async {
        await tester.pumpWidget(testWidget);

        final elevation = testContext.elevation;
        
        expect(elevation.level0, AicoDesignTokens.elevationLevel0);
        expect(elevation.level1, AicoDesignTokens.elevationLevel1);
        expect(elevation.level2, AicoDesignTokens.elevationLevel2);
        expect(elevation.level3, AicoDesignTokens.elevationLevel3);
        expect(elevation.level4, AicoDesignTokens.elevationLevel4);
        expect(elevation.level5, AicoDesignTokens.elevationLevel5);
      });
    });

    group('breakpoint extensions', () {
      testWidgets('should detect current breakpoint correctly', (tester) async {
        // Test default screen size (800x600)
        await tester.pumpWidget(testWidget);

        final breakpoints = testContext.breakpoints;
        
        // 800px width should be tablet (>= 600px mobile, < 1200px desktop)
        expect(breakpoints.isMobile, false);
        expect(breakpoints.isTablet, true);
        expect(breakpoints.isDesktop, false);
        expect(breakpoints.desktop, AicoDesignTokens.breakpointDesktop);
        expect(breakpoints.largeDesktop, AicoDesignTokens.breakpointLargeDesktop);
      });

      testWidgets('should detect different breakpoints correctly', (tester) async {
        // Test mobile breakpoint (400px < 600px mobile breakpoint)
        tester.view.physicalSize = const Size(400, 800);
        tester.view.devicePixelRatio = 1.0;
        
        await tester.pumpWidget(testWidget);
        
        expect(testContext.breakpoints.isMobile, true);
        expect(testContext.breakpoints.isTablet, false);
        expect(testContext.breakpoints.isDesktop, false);

        // Test desktop breakpoint (1300px >= 1200px desktop breakpoint)
        tester.view.physicalSize = const Size(1300, 800);
        
        await tester.pumpWidget(testWidget);
        
        expect(testContext.breakpoints.isMobile, false);
        expect(testContext.breakpoints.isTablet, false);
        expect(testContext.breakpoints.isDesktop, true);
      });
    });

    group('accessibility extensions', () {
      testWidgets('should provide accessibility helpers', (tester) async {
        await tester.pumpWidget(testWidget);

        final accessibility = testContext.accessibility;
        
        expect(accessibility.isLargeText, isA<bool>());
        expect(accessibility.isReduceMotionEnabled, isA<bool>());
        expect(accessibility.isHighContrastEnabled, isA<bool>());
      });

      testWidgets('should detect high contrast correctly', (tester) async {
        final mockThemeManager = GetIt.instance<ThemeManager>() as MockThemeManager;
        
        // Test normal theme - update mock state
        mockThemeManager.setHighContrast(false);
        await tester.pumpWidget(MaterialApp(
          theme: AicoThemeDataFactory.generateLightTheme(),
          home: Builder(
            builder: (context) {
              expect(context.accessibility.isHighContrastEnabled, false);
              return const SizedBox();
            },
          ),
        ));

        // Test high contrast theme - update mock state
        mockThemeManager.setHighContrast(true);
        await tester.pumpWidget(MaterialApp(
          theme: AicoThemeDataFactory.generateHighContrastLightTheme(),
          home: Builder(
            builder: (context) {
              expect(context.accessibility.isHighContrastEnabled, true);
              return const SizedBox();
            },
          ),
        ));
      });

      testWidgets('should provide minimum touch target size', (tester) async {
        await tester.pumpWidget(testWidget);

        final accessibility = testContext.accessibility;
        
        expect(accessibility.minTouchTargetSize, AicoDesignTokens.minTouchTarget);
      });
    });

    group('integration with different themes', () {
      testWidgets('should work with all theme variants', (tester) async {
        final themes = [
          AicoThemeDataFactory.generateLightTheme(),
          AicoThemeDataFactory.generateDarkTheme(),
          AicoThemeDataFactory.generateHighContrastLightTheme(),
          AicoThemeDataFactory.generateHighContrastDarkTheme(),
        ];

        for (final theme in themes) {
          await tester.pumpWidget(MaterialApp(
            theme: theme,
            home: Builder(
              builder: (context) {
                // All extensions should work without errors
                expect(() => context.theme, returnsNormally);
                expect(() => context.colorScheme, returnsNormally);
                expect(() => context.textTheme, returnsNormally);
                expect(() => context.semanticColors, returnsNormally);
                expect(() => context.spacing, returnsNormally);
                expect(() => context.animations, returnsNormally);
                expect(() => context.elevation, returnsNormally);
                expect(() => context.breakpoints, returnsNormally);
                expect(() => context.accessibility, returnsNormally);
                
                return const SizedBox();
              },
            ),
          ));
        }
      });
    });

    group('error handling', () {
      testWidgets('should handle missing theme gracefully', (tester) async {
        await tester.pumpWidget(Builder(
          builder: (context) {
            // Extensions should not crash even without proper theme setup
            expect(() => context.spacing, returnsNormally);
            expect(() => context.animations, returnsNormally);
            expect(() => context.elevation, returnsNormally);
            expect(() => context.breakpoints, returnsNormally);
            
            return const SizedBox();
          },
        ));
      });
    });
  });
}
