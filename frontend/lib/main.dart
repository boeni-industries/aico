import 'dart:io';

import 'package:aico_frontend/core/providers.dart';
import 'package:aico_frontend/core/topics/aico_topics.dart';
import 'package:aico_frontend/presentation/providers/auth_provider.dart';
import 'package:aico_frontend/presentation/providers/theme_provider.dart';
import 'package:aico_frontend/presentation/widgets/auth/auth_gate.dart';
import 'package:aico_frontend/core/logging/aico_log.dart';
import 'package:aico_frontend/core/logging/providers/logging_providers.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:window_manager/window_manager.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Initialize window manager only for desktop platforms
  // Use try-catch to handle platforms where window_manager might not be available
  try {
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
  } catch (e) {
    // Window manager not available on this platform, continue without it
    debugPrint('Window manager not available: $e');
    AICOLog.warn('Window manager not available on platform', 
      topic: 'app/startup/window_manager', 
      error: e,
      extra: {'platform': Platform.operatingSystem});
  }
  
  // Initialize SharedPreferences for Riverpod
  final sharedPreferences = await SharedPreferences.getInstance();
  
  debugPrint('[app:${AICOTopics.appStartup}] AICO Flutter application starting');
  AICOLog.info('AICO Flutter application starting', 
    topic: 'app/startup/init', 
    extra: {'startup_topic': AICOTopics.appStartup});
  
  runApp(
    ProviderScope(
      overrides: [
        sharedPreferencesProvider.overrideWithValue(sharedPreferences),
      ],
      child: const AicoApp(),
    ),
  );
}

class AicoApp extends ConsumerStatefulWidget {
  const AicoApp({super.key});

  @override
  ConsumerState<AicoApp> createState() => _AicoAppState();
}

class _AicoAppState extends ConsumerState<AicoApp> {
  @override
  void initState() {
    super.initState();
    
    // Initialize the logger provider to trigger initialization
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(aicoLoggerProvider);
    });
    
    debugPrint('[app:${AICOTopics.appInitialization}] App widget initialized with Riverpod');
    AICOLog.info('App widget initialized with Riverpod', 
      topic: 'app/lifecycle/init', 
      extra: {'initialization_topic': AICOTopics.appInitialization});
    
    // Initialize auth status check
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(authProvider.notifier).checkAuthStatus();
    });
  }

  @override
  Widget build(BuildContext context) {
    final themeState = ref.watch(themeControllerProvider);
    final themeManager = ref.watch(themeManagerProvider);
    
    // Get appropriate themes based on high contrast setting
    final lightTheme = themeState.isHighContrast 
        ? themeManager.generateHighContrastLightTheme()
        : themeManager.generateLightTheme();
    final darkTheme = themeState.isHighContrast 
        ? themeManager.generateHighContrastDarkTheme()
        : themeManager.generateDarkTheme();
    
    return MaterialApp(
      title: 'AICO',
      debugShowCheckedModeBanner: false,
      theme: lightTheme,
      darkTheme: darkTheme,
      themeMode: themeState.themeMode,
      home: const AuthGate(),
    );
  }
}

