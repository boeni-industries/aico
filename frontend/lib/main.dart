import 'dart:io';

import 'package:aico_frontend/core/di/service_locator.dart';
import 'package:aico_frontend/core/theme/aico_theme.dart';
import 'package:aico_frontend/core/theme/theme_manager.dart';
import 'package:aico_frontend/presentation/blocs/auth/auth_bloc.dart';
import 'package:aico_frontend/presentation/widgets/auth/auth_gate.dart';
import 'package:aico_frontend/presentation/blocs/connection/connection_bloc.dart';
import 'package:aico_frontend/presentation/blocs/settings/settings_bloc.dart';
import 'package:aico_frontend/networking/repositories/user_repository.dart';
import 'package:aico_frontend/networking/services/token_manager.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:window_manager/window_manager.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Initialize window manager only for desktop platforms
  if (!kIsWeb && (Platform.isWindows || Platform.isLinux || Platform.isMacOS)) {
    await windowManager.ensureInitialized();
    
    WindowOptions windowOptions = const WindowOptions(
      size: Size(1200, 800),
      minimumSize: Size(800, 600),
      center: true,
      backgroundColor: Colors.transparent,
      skipTaskbar: false,
      titleBarStyle: TitleBarStyle.normal,
    );
    
    windowManager.waitUntilReadyToShow(windowOptions, () async {
      await windowManager.show();
      await windowManager.focus();
    });
  }
  
  // Initialize dependency injection
  await ServiceLocator.initialize();
  
  runApp(const AicoApp());
}

class AicoApp extends StatefulWidget {
  const AicoApp({super.key});

  @override
  State<AicoApp> createState() => _AicoAppState();
}

class _AicoAppState extends State<AicoApp> {
  late ThemeManager _themeManager;
  ThemeMode _currentThemeMode = ThemeMode.system;

  @override
  void initState() {
    super.initState();
    _themeManager = ServiceLocator.get<ThemeManager>();
    _currentThemeMode = _themeManager.currentThemeMode;
    
    // Listen to theme changes
    _themeManager.themeChanges.listen((themeMode) {
      if (mounted) {
        setState(() {
          _currentThemeMode = themeMode;
        });
      }
    });
  }

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
        BlocProvider<AuthBloc>(
          create: (context) => AuthBloc(
            userRepository: ServiceLocator.get<UserRepository>(),
            tokenManager: ServiceLocator.get<TokenManager>(),
          )..add(const AuthStatusChecked()),
        ),
      ],
      child: MaterialApp(
        title: 'AICO',
        debugShowCheckedModeBanner: false,
        theme: _themeManager.isHighContrastEnabled 
            ? _themeManager.generateHighContrastLightTheme()
            : AicoTheme.light(),
        darkTheme: _themeManager.isHighContrastEnabled 
            ? _themeManager.generateHighContrastDarkTheme()
            : AicoTheme.dark(),
        themeMode: _currentThemeMode,
        home: const AuthGate(),
      ),
    );
  }
}

