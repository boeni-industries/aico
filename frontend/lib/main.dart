import 'dart:io';

import 'package:aico_frontend/core/logging/aico_log.dart';
import 'package:aico_frontend/core/logging/providers/logging_providers.dart';
import 'package:aico_frontend/core/providers.dart';
import 'package:aico_frontend/core/services/window_state_service.dart';
import 'package:aico_frontend/core/topics/aico_topics.dart';
import 'package:aico_frontend/presentation/providers/auth_provider.dart';
import 'package:aico_frontend/presentation/providers/theme_provider.dart';
import 'package:aico_frontend/presentation/widgets/auth/auth_gate.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_inappwebview/flutter_inappwebview.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:window_manager/window_manager.dart';
import 'package:package_info_plus/package_info_plus.dart';

// Avatar localhost server
final InAppLocalhostServer avatarServer = InAppLocalhostServer(
  documentRoot: 'assets/avatar',
  port: 8779,
);

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Start avatar localhost server for WebView
  if (!kIsWeb) {
    try {
      await avatarServer.start();
      debugPrint('[AICO] Avatar localhost server started on port 8779');
      AICOLog.info('Avatar localhost server started', 
        topic: 'app/startup/avatar_server', 
        extra: {'port': 8779});
    } catch (e) {
      debugPrint('[AICO] Failed to start avatar server: $e');
      AICOLog.error('Failed to start avatar localhost server', 
        topic: 'app/startup/avatar_server', 
        error: e);
    }
  }
  
  // Enable WebView debugging in debug mode
  if (!kIsWeb && kDebugMode) {
    if (Platform.isAndroid) {
      await InAppWebViewController.setWebContentsDebuggingEnabled(true);
    }
  }
  
  // Initialize SharedPreferences for Riverpod
  final sharedPreferences = await SharedPreferences.getInstance();
  
  // Initialize window state service for desktop platforms
  // This handles window manager initialization, state restoration, and version title
  final windowStateService = WindowStateService(sharedPreferences);
  await windowStateService.initialize();
  
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
  String _appTitle = 'AICO';
  
  @override
  void initState() {
    super.initState();
    _loadVersion();
    
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
  
  Future<void> _loadVersion() async {
    try {
      final packageInfo = await PackageInfo.fromPlatform();
      setState(() {
        _appTitle = 'AICO v${packageInfo.version}';
      });
    } catch (e) {
      debugPrint('Failed to load version: $e');
      AICOLog.warn('Failed to load package version', 
        topic: 'app/lifecycle/version', 
        error: e);
    }
  }

  @override
  Widget build(BuildContext context) {
    final themeState = ref.watch(themeControllerProvider);
    final themeManager = ref.watch(themeManagerProvider);
    
    // Get dark theme based on high contrast setting (light mode disabled)
    final darkTheme = themeState.isHighContrast 
        ? themeManager.generateHighContrastDarkTheme()
        : themeManager.generateDarkTheme();
    
    return MaterialApp(
      title: _appTitle,
      debugShowCheckedModeBanner: false,
      theme: darkTheme,  // Force dark mode
      darkTheme: darkTheme,
      themeMode: ThemeMode.dark,  // Always dark
      home: const AuthGate(),
    );
  }
}

