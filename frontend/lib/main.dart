import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'core/di/service_locator.dart';
import 'core/theme/theme_manager.dart';
import 'core/theme/theme_animated_switcher.dart';
import 'core/theme/theme_extensions.dart';
import 'features/settings/bloc/settings_bloc.dart';
import 'features/settings/models/settings_event.dart';
import 'features/connection/bloc/connection_bloc.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Initialize dependency injection
  await ServiceLocator.initialize();
  
  runApp(const AicoApp());
}

class AicoApp extends StatelessWidget {
  const AicoApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiBlocProvider(
      providers: [
        BlocProvider<SettingsBloc>(
          create: (context) => ServiceLocator.get<SettingsBloc>()..add(const SettingsLoad()),
        ),
        BlocProvider<ConnectionBloc>(
          create: (context) => ServiceLocator.get<ConnectionBloc>(),
        ),
      ],
      child: StreamBuilder<ThemeMode>(
        stream: ServiceLocator.get<ThemeManager>().themeChanges,
        builder: (context, snapshot) {
          final themeManager = ServiceLocator.get<ThemeManager>();
          
          return ThemeAnimatedSwitcher(
            child: MaterialApp(
              title: 'AICO',
              debugShowCheckedModeBanner: false,
              theme: themeManager.isHighContrastEnabled 
                  ? themeManager.generateHighContrastLightTheme()
                  : themeManager.generateLightTheme(),
              darkTheme: themeManager.isHighContrastEnabled
                  ? themeManager.generateHighContrastDarkTheme()
                  : themeManager.generateDarkTheme(),
              themeMode: themeManager.currentThemeMode,
              home: const AicoHomePage(),
            ),
          );
        },
      ),
    );
  }
}

/// AICO Home Page - demonstrates theming system
class AicoHomePage extends StatelessWidget {
  const AicoHomePage({super.key});

  @override
  Widget build(BuildContext context) {
    final themeManager = ServiceLocator.get<ThemeManager>();
    
    return Scaffold(
      appBar: AppBar(
        title: const Text('AICO'),
        actions: [
          IconButton(
            icon: Icon(
              context.isDarkTheme ? Icons.light_mode : Icons.dark_mode,
            ),
            onPressed: () => themeManager.toggleTheme(),
            tooltip: 'Toggle theme',
          ),
          IconButton(
            icon: const Icon(Icons.contrast),
            onPressed: () => themeManager.setHighContrastEnabled(
              !themeManager.isHighContrastEnabled,
            ),
            tooltip: 'Toggle high contrast',
          ),
        ],
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Card(
              margin: context.spacing.paddingLg,
              child: Padding(
                padding: context.spacing.paddingLg,
                child: Column(
                  children: [
                    Text(
                      'AICO Theme System',
                      style: context.textTheme.headlineLarge,
                    ),
                    SizedBox(height: context.spacing.md),
                    Text(
                      'Material 3 theming with AICO branding',
                      style: context.textTheme.bodyLarge,
                    ),
                    SizedBox(height: context.spacing.lg),
                    Wrap(
                      spacing: context.spacing.sm,
                      children: [
                        Chip(
                          label: Text('Theme: ${_getThemeName(themeManager.currentThemeMode)}'),
                          backgroundColor: context.semanticColors.accent.withOpacity(0.2),
                        ),
                        Chip(
                          label: Text('High Contrast: ${themeManager.isHighContrastEnabled ? 'On' : 'Off'}'),
                          backgroundColor: context.semanticColors.info.withOpacity(0.2),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
            SizedBox(height: context.spacing.xl),
            ElevatedButton(
              onPressed: () => themeManager.toggleTheme(),
              child: const Text('Toggle Theme'),
            ),
            SizedBox(height: context.spacing.md),
            OutlinedButton(
              onPressed: () => themeManager.setHighContrastEnabled(
                !themeManager.isHighContrastEnabled,
              ),
              child: const Text('Toggle High Contrast'),
            ),
            SizedBox(height: context.spacing.md),
            TextButton(
              onPressed: () => themeManager.resetTheme(),
              child: const Text('Reset to System Theme'),
            ),
          ],
        ),
      ),
    );
  }

  String _getThemeName(ThemeMode mode) {
    switch (mode) {
      case ThemeMode.light:
        return 'Light';
      case ThemeMode.dark:
        return 'Dark';
      case ThemeMode.system:
        return 'System';
    }
  }
}
