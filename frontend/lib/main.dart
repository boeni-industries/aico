import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'core/di/service_locator.dart';
import 'core/theme/theme_manager.dart';
import 'core/theme/theme_animated_switcher.dart';
import 'core/navigation/app_router.dart';
import 'features/settings/bloc/settings_bloc.dart';
import 'features/settings/models/settings_event.dart';
import 'features/connection/bloc/connection_bloc.dart';
import 'presentation/blocs/navigation/navigation_bloc.dart';

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
        BlocProvider<NavigationBloc>(
          create: (context) => NavigationBloc(),
        ),
      ],
      child: StreamBuilder<ThemeMode>(
        stream: ServiceLocator.get<ThemeManager>().themeChanges,
        builder: (context, snapshot) {
          final themeManager = ServiceLocator.get<ThemeManager>();
          
          return ThemeAnimatedSwitcher(
            child: MaterialApp.router(
              title: 'AICO',
              debugShowCheckedModeBanner: false,
              theme: themeManager.isHighContrastEnabled 
                  ? themeManager.generateHighContrastLightTheme()
                  : themeManager.generateLightTheme(),
              darkTheme: themeManager.isHighContrastEnabled
                  ? themeManager.generateHighContrastDarkTheme()
                  : themeManager.generateDarkTheme(),
              themeMode: themeManager.currentThemeMode,
              routerConfig: AppRouter.router,
            ),
          );
        },
      ),
    );
  }
}

