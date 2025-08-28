import 'package:aico_frontend/core/logging/logging.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:get_it/get_it.dart';


/// Example of how to integrate logging into main.dart
void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Setup dependency injection
  await setupDependencies();
  
  // Setup user context if available
  Log.setEnvironment('production'); // or 'dev', 'staging'
  
  // Log app startup
  Log.i('frontend.app', 'app.lifecycle.startup', 'AICO app starting');
  
  runApp(MyApp());
}

Future<void> setupDependencies() async {
  final getIt = GetIt.instance;
  
  // Register Dio first (required by logging module)
  getIt.registerLazySingleton<Dio>(() {
    final dio = Dio(BaseOptions(
      baseUrl: 'http://localhost:8771', // AICO backend URL
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 10),
      sendTimeout: const Duration(seconds: 10),
    ));
    
    // Add interceptors for authentication, etc.
    // dio.interceptors.add(AuthInterceptor());
    
    return dio;
  });
  
  // Register logging module
  await LoggingModule.register(getIt);
  
  // Log successful setup
  Log.i('frontend.app', 'app.setup.complete', 'Dependency injection setup complete');
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AICO',
      theme: ThemeData(
        primarySwatch: Colors.blue,
      ),
      home: MyHomePage(),
      // Add navigation observer for route logging
      navigatorObservers: [LoggingNavigatorObserver()],
    );
  }
}

class MyHomePage extends StatefulWidget {
  const MyHomePage({super.key});

  @override
  State<MyHomePage> createState() => _MyHomePageState();
}

class _MyHomePageState extends State<MyHomePage> with WidgetsBindingObserver {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    Log.i('frontend.home', 'widget.lifecycle.init', 'Home page initialized');
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    Log.i('frontend.home', 'widget.lifecycle.dispose', 'Home page disposed');
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    super.didChangeAppLifecycleState(state);
    
    Log.i('frontend.app', 'app.lifecycle.state_change', 'App lifecycle state changed', extra: {
      'state': state.toString(),
    });
    
    if (state == AppLifecycleState.paused) {
      // Flush logs when app goes to background
      Log.flush();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('AICO'),
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: <Widget>[
            Text('Welcome to AICO'),
            ElevatedButton(
              onPressed: () {
                Log.i('frontend.home', 'ui.button.click', 'Welcome button clicked');
                // Navigate or perform action
              },
              child: Text('Get Started'),
            ),
          ],
        ),
      ),
    );
  }
}

/// Navigation observer that logs route changes
class LoggingNavigatorObserver extends NavigatorObserver {
  @override
  void didPush(Route<dynamic> route, Route<dynamic>? previousRoute) {
    super.didPush(route, previousRoute);
    
    Log.d('frontend.navigation', 'navigation.push', 'Route pushed', extra: {
      'route_name': route.settings.name ?? 'unnamed',
      'previous_route': previousRoute?.settings.name ?? 'none',
    });
  }

  @override
  void didPop(Route<dynamic> route, Route<dynamic>? previousRoute) {
    super.didPop(route, previousRoute);
    
    Log.d('frontend.navigation', 'navigation.pop', 'Route popped', extra: {
      'route_name': route.settings.name ?? 'unnamed',
      'previous_route': previousRoute?.settings.name ?? 'none',
    });
  }

  @override
  void didReplace({Route<dynamic>? newRoute, Route<dynamic>? oldRoute}) {
    super.didReplace(newRoute: newRoute, oldRoute: oldRoute);
    
    Log.d('frontend.navigation', 'navigation.replace', 'Route replaced', extra: {
      'new_route': newRoute?.settings.name ?? 'unnamed',
      'old_route': oldRoute?.settings.name ?? 'unnamed',
    });
  }
}
