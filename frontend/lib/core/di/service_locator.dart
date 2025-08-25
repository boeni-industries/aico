import 'package:aico_frontend/core/logging/logging_module.dart';
import 'package:aico_frontend/core/services/local_storage.dart';
import 'package:aico_frontend/core/theme/aico_theme_manager.dart';
import 'package:aico_frontend/core/theme/theme_manager.dart';
import 'package:aico_frontend/core/utils/aico_paths.dart';
import 'package:aico_frontend/networking/repositories/user_repository.dart';
import 'package:aico_frontend/networking/services/offline_queue.dart';
import 'package:aico_frontend/networking/services/token_manager.dart';
import 'package:aico_frontend/presentation/blocs/auth/auth_bloc.dart';
import 'package:aico_frontend/presentation/blocs/connection/connection_bloc.dart';
import 'package:aico_frontend/presentation/blocs/navigation/navigation_bloc.dart';
import 'package:aico_frontend/presentation/blocs/settings/settings_bloc.dart';
import 'package:dio/dio.dart';
import 'package:aico_frontend/core/services/api_service.dart';
import 'package:aico_frontend/core/services/encryption_service.dart';
import 'package:aico_frontend/core/services/unified_api_client.dart';
import 'package:get_it/get_it.dart';
import 'package:hydrated_bloc/hydrated_bloc.dart';
import 'package:http/http.dart' as http;

/// Centralized dependency injection setup for the AICO app
/// Configures all services, repositories, and BLoCs with proper lifecycle management
class ServiceLocator {
  static final GetIt _getIt = GetIt.instance;
  static bool _isInitialized = false;

  /// Initialize all dependencies
  static Future<void> initialize() async {
    if (_isInitialized) return;

    try {
      // Initialize HydratedBloc storage
      await _initializeHydratedStorage();

      // Initialize AICO paths
      await AICOPaths.initialize();

      // Register encryption services first (required by core services)
      await _registerEncryptionServices();
      
      // Wait for async encryption service to be ready
      await _getIt.allReady();

      // Register core services
      await _registerCoreServices();
      
      // Wait for async UnifiedApiClient to be ready
      await _getIt.allReady();

      // Register logging module
      await LoggingModule.register(_getIt);

      // Register repositories
      await _registerRepositories();

      // Register BLoCs
      await _registerBlocs();

      _isInitialized = true;
    } catch (e) {
      throw ServiceLocatorException('Failed to initialize dependencies: $e');
    }
  }

  /// Initialize HydratedBloc storage
  static Future<void> _initializeHydratedStorage() async {
    final storageDirectory = await AICOPaths.getStatePath();
    await AICOPaths.ensureDirectory(storageDirectory);
    
    HydratedBloc.storage = await HydratedStorage.build(
      storageDirectory: HydratedStorageDirectory(storageDirectory),
    );
  }

  /// Register core services
  static Future<void> _registerCoreServices() async {
    // Dio client
    _getIt.registerLazySingleton<Dio>(() {
      final dio = Dio(BaseOptions(
        baseUrl: 'http://localhost:8771/api/v1/', // TODO: Make configurable
        connectTimeout: const Duration(seconds: 15),
        receiveTimeout: const Duration(seconds: 15),
        followRedirects: true, // Allow Dio to follow redirects
        validateStatus: (status) {
          // Allow all status codes < 500, including redirects (3xx)
          return status != null && status < 500;
        },
      ));
      return dio;
    });

    // Smart API client and ApiService (unified API layer)
    _getIt.registerSingletonAsync<UnifiedApiClient>(() async {
      final client = UnifiedApiClient(
        dio: _getIt<Dio>(),
        httpClient: http.Client(),
        encryptionService: _getIt<EncryptionService>(),
        baseUrl: 'http://localhost:8771/api/v1',
      );
      try {
        await client.initializeEncryption();
        print('✅ UnifiedApiClient: Encryption initialized successfully');
      } catch (e) {
        print('❌ UnifiedApiClient: Encryption initialization failed: $e');
        // Don't throw here - let the client work in unencrypted mode for health checks
        // but log the error for debugging
      }
      return client;
    });

    // Register ApiService using the initialized UnifiedApiClient
    _getIt.registerLazySingleton<ApiService>(
      () => ApiService(_getIt<UnifiedApiClient>()),
    );

    // Offline queue
    _getIt.registerLazySingleton<OfflineQueue>(() => OfflineQueue());

    // Local storage
    _getIt.registerLazySingleton<LocalStorage>(() => LocalStorage());
  }

  /// Register repositories
  static Future<void> _registerRepositories() async {
    // User repository
    _getIt.registerLazySingleton<UserRepository>(
      () => ApiUserRepository(
        apiService: _getIt<ApiService>(),
        tokenManager: _getIt<TokenManager>(),
      ),
    );

    // Token manager
    _getIt.registerLazySingleton<TokenManager>(
      () => TokenManager(),
    );
  }

  /// Register BLoCs
  static Future<void> _registerBlocs() async {
    // Auth BLoC
    _getIt.registerLazySingleton<AuthBloc>(
      () => AuthBloc(
        userRepository: _getIt<UserRepository>(),
        tokenManager: _getIt<TokenManager>(),
      ),
    );

    // Connection BLoC (simplified constructor)
    _getIt.registerLazySingleton<ConnectionBloc>(
      () => ConnectionBloc(),
    );

    // Navigation BLoC (simplified constructor)
    _getIt.registerLazySingleton<NavigationBloc>(
      () => NavigationBloc(),
    );

    // Settings BLoC (simplified constructor)
    _getIt.registerLazySingleton<SettingsBloc>(
      () => SettingsBloc(),
    );

    // Theme Manager
    _getIt.registerLazySingleton<ThemeManager>(
      () => AicoThemeManager(
        settingsBloc: _getIt<SettingsBloc>(),
      ),
    );
  }

  /// Register encryption services
  static Future<void> _registerEncryptionServices() async {
    // Encryption Service (still registered for SmartApiClient internal use)
    _getIt.registerSingletonAsync<EncryptionService>(() async {
      final service = EncryptionService();
      await service.initialize();
      return service;
    });
    // No need to register EncryptedApiClient or EncryptedApiService globally
  }

  /// Get service instance
  static T get<T extends Object>() {
    if (!_isInitialized) {
      throw ServiceLocatorException('ServiceLocator not initialized. Call initialize() first.');
    }
    return _getIt.get<T>();
  }

  /// Check if service is registered
  static bool isRegistered<T extends Object>() {
    return _getIt.isRegistered<T>();
  }

  /// Waits until all registered async singletons are ready
  static Future<void> allReady() {
    return _getIt.allReady();
  }

  /// Reset all services (for testing)
  static Future<void> reset() async {
    await _getIt.reset();
    _isInitialized = false;
  }

  /// Dispose all services
  static Future<void> dispose() async {
    // Dispose logging module
    await LoggingModule.dispose(_getIt);

    // Dispose offline queue
    if (_getIt.isRegistered<OfflineQueue>()) {
      _getIt<OfflineQueue>().dispose();
    }

    // Close BLoCs
    if (_getIt.isRegistered<AuthBloc>()) {
      await _getIt<AuthBloc>().close();
    }
    if (_getIt.isRegistered<ConnectionBloc>()) {
      await _getIt<ConnectionBloc>().close();
    }
    if (_getIt.isRegistered<NavigationBloc>()) {
      await _getIt<NavigationBloc>().close();
    }
    if (_getIt.isRegistered<SettingsBloc>()) {
      await _getIt<SettingsBloc>().close();
    }

    await _getIt.reset();
    _isInitialized = false;
  }
}

/// Exception for service locator errors
class ServiceLocatorException implements Exception {
  final String message;
  const ServiceLocatorException(this.message);

  @override
  String toString() => 'ServiceLocatorException: $message';
}
