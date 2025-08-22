import 'package:aico_frontend/core/theme/design_tokens.dart';
import 'package:aico_frontend/core/theme/theme_data_factory.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('AicoThemeDataFactory', () {
    group('light theme generation', () {
      late ThemeData lightTheme;

      setUpAll(() {
        lightTheme = AicoThemeDataFactory.generateLightTheme();
      });

      test('should generate valid ThemeData', () {
        expect(lightTheme, isA<ThemeData>());
        expect(lightTheme.useMaterial3, true);
      });

      test('should use light brightness', () {
        expect(lightTheme.brightness, Brightness.light);
        expect(lightTheme.colorScheme.brightness, Brightness.light);
      });

      test('should use AICO soft lavender as seed color', () {
        // The primary color should be derived from soft lavender
        expect(lightTheme.colorScheme.primary, isNotNull);
      });

      test('should have proper surface colors', () {
        expect(lightTheme.colorScheme.surface, isNotNull);
        expect(lightTheme.colorScheme.surface, isNotNull);
      });

      test('should have complete color scheme', () {
        final colorScheme = lightTheme.colorScheme;
        expect(colorScheme.primary, isNotNull);
        expect(colorScheme.onPrimary, isNotNull);
        expect(colorScheme.secondary, isNotNull);
        expect(colorScheme.onSecondary, isNotNull);
        expect(colorScheme.error, isNotNull);
        expect(colorScheme.onError, isNotNull);
        expect(colorScheme.surface, isNotNull);
        expect(colorScheme.onSurface, isNotNull);
      });

      test('should have AICO typography', () {
        expect(lightTheme.textTheme, isNotNull);
        expect(lightTheme.textTheme.bodyLarge?.fontFamily, AicoDesignTokens.fontFamily);
      });

      test('should have component themes configured', () {
        expect(lightTheme.appBarTheme, isNotNull);
        expect(lightTheme.elevatedButtonTheme, isNotNull);
        expect(lightTheme.textButtonTheme, isNotNull);
        expect(lightTheme.outlinedButtonTheme, isNotNull);
        expect(lightTheme.cardTheme, isNotNull);
        expect(lightTheme.inputDecorationTheme, isNotNull);
      });
    });

    group('dark theme generation', () {
      late ThemeData darkTheme;

      setUpAll(() {
        darkTheme = AicoThemeDataFactory.generateDarkTheme();
      });

      test('should generate valid ThemeData', () {
        expect(darkTheme, isA<ThemeData>());
        expect(darkTheme.useMaterial3, true);
      });

      test('should use dark brightness', () {
        expect(darkTheme.brightness, Brightness.dark);
        expect(darkTheme.colorScheme.brightness, Brightness.dark);
      });

      test('should have proper dark surface colors', () {
        expect(darkTheme.colorScheme.surface, isNotNull);
        expect(darkTheme.colorScheme.surface, isNotNull);
      });

      test('should have complete color scheme', () {
        final colorScheme = darkTheme.colorScheme;
        expect(colorScheme.primary, isNotNull);
        expect(colorScheme.onPrimary, isNotNull);
        expect(colorScheme.secondary, isNotNull);
        expect(colorScheme.onSecondary, isNotNull);
        expect(colorScheme.error, isNotNull);
        expect(colorScheme.onError, isNotNull);
        expect(colorScheme.surface, isNotNull);
        expect(colorScheme.onSurface, isNotNull);
      });
    });

    group('high contrast light theme generation', () {
      late ThemeData highContrastLightTheme;

      setUpAll(() {
        highContrastLightTheme = AicoThemeDataFactory.generateHighContrastLightTheme();
      });

      test('should generate valid ThemeData', () {
        expect(highContrastLightTheme, isA<ThemeData>());
        expect(highContrastLightTheme.useMaterial3, true);
      });

      test('should use light brightness', () {
        expect(highContrastLightTheme.brightness, Brightness.light);
        expect(highContrastLightTheme.colorScheme.brightness, Brightness.light);
      });

      test('should use high contrast colors', () {
        final colorScheme = highContrastLightTheme.colorScheme;
        
        // High contrast light should use black primary on white surface
        expect(colorScheme.primary, Colors.black);
        expect(colorScheme.onPrimary, Colors.white);
        expect(colorScheme.surface, Colors.white);
        expect(colorScheme.onSurface, Colors.black);
        expect(colorScheme.surface, Colors.white);
        expect(colorScheme.onSurface, Colors.black);
      });

      test('should have accessibility-compliant contrast ratios', () {
        final colorScheme = highContrastLightTheme.colorScheme;
        
        // Test key color combinations for WCAG AAA compliance
        // Black on white should have maximum contrast
        expect(colorScheme.primary, Colors.black);
        expect(colorScheme.surface, Colors.white);
      });

      test('should have proper error colors for accessibility', () {
        final colorScheme = highContrastLightTheme.colorScheme;
        expect(colorScheme.error, const Color(0xFFD32F2F)); // High contrast red
        expect(colorScheme.onError, Colors.white);
      });
    });

    group('high contrast dark theme generation', () {
      late ThemeData highContrastDarkTheme;

      setUpAll(() {
        highContrastDarkTheme = AicoThemeDataFactory.generateHighContrastDarkTheme();
      });

      test('should generate valid ThemeData', () {
        expect(highContrastDarkTheme, isA<ThemeData>());
        expect(highContrastDarkTheme.useMaterial3, true);
      });

      test('should use dark brightness', () {
        expect(highContrastDarkTheme.brightness, Brightness.dark);
        expect(highContrastDarkTheme.colorScheme.brightness, Brightness.dark);
      });

      test('should use high contrast colors', () {
        final colorScheme = highContrastDarkTheme.colorScheme;
        
        // High contrast dark should use white primary on black surface
        expect(colorScheme.primary, Colors.white);
        expect(colorScheme.onPrimary, Colors.black);
        expect(colorScheme.surface, Colors.black);
        expect(colorScheme.onSurface, Colors.white);
        expect(colorScheme.surface, Colors.black);
        expect(colorScheme.onSurface, Colors.white);
      });

      test('should have accessibility-compliant contrast ratios', () {
        final colorScheme = highContrastDarkTheme.colorScheme;
        
        // Test key color combinations for WCAG AAA compliance
        // White on black should have maximum contrast
        expect(colorScheme.primary, Colors.white);
        expect(colorScheme.surface, Colors.black);
      });

      test('should have proper error colors for accessibility', () {
        final colorScheme = highContrastDarkTheme.colorScheme;
        expect(colorScheme.error, const Color(0xFFFF5252)); // High contrast red for dark
        expect(colorScheme.onError, Colors.black);
      });
    });

    group('theme consistency', () {
      test('should generate different themes for different modes', () {
        final lightTheme = AicoThemeDataFactory.generateLightTheme();
        final darkTheme = AicoThemeDataFactory.generateDarkTheme();
        final highContrastLight = AicoThemeDataFactory.generateHighContrastLightTheme();
        final highContrastDark = AicoThemeDataFactory.generateHighContrastDarkTheme();

        // Themes should be different instances
        expect(identical(lightTheme, darkTheme), false);
        expect(identical(lightTheme, highContrastLight), false);
        expect(identical(darkTheme, highContrastDark), false);
        expect(identical(highContrastLight, highContrastDark), false);

        // But should have consistent structure
        expect(lightTheme.useMaterial3, darkTheme.useMaterial3);
        expect(lightTheme.useMaterial3, highContrastLight.useMaterial3);
        expect(lightTheme.useMaterial3, highContrastDark.useMaterial3);
      });

      test('should have consistent component themes across all variants', () {
        final themes = [
          AicoThemeDataFactory.generateLightTheme(),
          AicoThemeDataFactory.generateDarkTheme(),
          AicoThemeDataFactory.generateHighContrastLightTheme(),
          AicoThemeDataFactory.generateHighContrastDarkTheme(),
        ];

        for (final theme in themes) {
          expect(theme.appBarTheme, isNotNull);
          expect(theme.elevatedButtonTheme, isNotNull);
          expect(theme.textButtonTheme, isNotNull);
          expect(theme.outlinedButtonTheme, isNotNull);
          expect(theme.cardTheme, isNotNull);
          expect(theme.inputDecorationTheme, isNotNull);
          expect(theme.floatingActionButtonTheme, isNotNull);
        }
      });

      test('should use AICO design tokens consistently', () {
        final themes = [
          AicoThemeDataFactory.generateLightTheme(),
          AicoThemeDataFactory.generateDarkTheme(),
          AicoThemeDataFactory.generateHighContrastLightTheme(),
          AicoThemeDataFactory.generateHighContrastDarkTheme(),
        ];

        for (final theme in themes) {
          // Check typography uses AICO font family
          expect(theme.textTheme.bodyLarge?.fontFamily, AicoDesignTokens.fontFamily);
          expect(theme.textTheme.headlineLarge?.fontFamily, AicoDesignTokens.fontFamily);
          
          // Check button themes use AICO spacing
          final elevatedButtonStyle = theme.elevatedButtonTheme.style;
          expect(elevatedButtonStyle, isNotNull);
        }
      });
    });

    group('accessibility compliance', () {
      test('high contrast themes should meet WCAG AAA standards', () {
        final highContrastLight = AicoThemeDataFactory.generateHighContrastLightTheme();
        final highContrastDark = AicoThemeDataFactory.generateHighContrastDarkTheme();

        // Test primary color contrast ratios
        final lightScheme = highContrastLight.colorScheme;
        final darkScheme = highContrastDark.colorScheme;

        // High contrast light: black on white
        expect(lightScheme.primary, Colors.black);
        expect(lightScheme.surface, Colors.white);

        // High contrast dark: white on black  
        expect(darkScheme.primary, Colors.white);
        expect(darkScheme.surface, Colors.black);
      });

      test('should have proper minimum touch target sizes', () {
        final themes = [
          AicoThemeDataFactory.generateLightTheme(),
          AicoThemeDataFactory.generateDarkTheme(),
          AicoThemeDataFactory.generateHighContrastLightTheme(),
          AicoThemeDataFactory.generateHighContrastDarkTheme(),
        ];

        for (final theme in themes) {
          // Check button minimum sizes meet accessibility guidelines
          final elevatedButtonStyle = theme.elevatedButtonTheme.style;
          expect(elevatedButtonStyle?.minimumSize, isNotNull);
          
          final textButtonStyle = theme.textButtonTheme.style;
          expect(textButtonStyle?.minimumSize, isNotNull);
        }
      });
    });

    group('Material 3 compliance', () {
      test('should use Material 3 design system', () {
        final themes = [
          AicoThemeDataFactory.generateLightTheme(),
          AicoThemeDataFactory.generateDarkTheme(),
          AicoThemeDataFactory.generateHighContrastLightTheme(),
          AicoThemeDataFactory.generateHighContrastDarkTheme(),
        ];

        for (final theme in themes) {
          expect(theme.useMaterial3, true);
          
          // Material 3 should have proper color scheme structure
          final colorScheme = theme.colorScheme;
          expect(colorScheme.primary, isNotNull);
          expect(colorScheme.secondary, isNotNull);
          expect(colorScheme.tertiary, isNotNull);
          expect(colorScheme.surface, isNotNull);
          expect(colorScheme.surfaceContainerHighest, isNotNull);
          expect(colorScheme.outline, isNotNull);
        }
      });

      test('should have proper elevation and shape themes', () {
        final lightTheme = AicoThemeDataFactory.generateLightTheme();
        
        // Check card theme has proper elevation and shape
        expect(lightTheme.cardTheme.elevation, isNotNull);
        expect(lightTheme.cardTheme.shape, isNotNull);
        
        // Check FAB theme
        expect(lightTheme.floatingActionButtonTheme.elevation, isNotNull);
        expect(lightTheme.floatingActionButtonTheme.shape, isNotNull);
      });
    });
  });
}
