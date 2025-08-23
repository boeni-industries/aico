import 'package:aico_frontend/core/services/local_storage.dart';
import 'package:aico_frontend/core/theme/aico_theme_manager.dart';
import 'package:aico_frontend/core/theme/theme_manager.dart';
import 'package:aico_frontend/core/utils/aico_paths.dart';
import 'package:aico_frontend/networking/clients/api_client.dart';
import 'package:aico_frontend/networking/repositories/user_repository.dart';
import 'package:aico_frontend/networking/services/offline_queue.dart';
import 'package:aico_frontend/networking/services/token_manager.dart';
import 'package:aico_frontend/presentation/blocs/auth/auth_bloc.dart';
import 'package:aico_frontend/presentation/blocs/connection/connection_bloc.dart';
import 'package:aico_frontend/presentation/blocs/navigation/navigation_bloc.dart';
import 'package:aico_frontend/presentation/blocs/settings/settings_bloc.dart';
import 'package:dio/dio.dart';
import 'package:get_it/get_it.dart';
import 'package:hydrated_bloc/hydrated_bloc.dart';

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

      // Register core services
      await _registerCoreServices();

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
    _getIt.registerLazySingleton<Dio>(() => Dio());

    // API client
    _getIt.registerLazySingleton<AicoApiClient>(
      () => AicoApiClient(
        _getIt<Dio>(),
        baseUrl: 'http://localhost:8771/api/v1', // TODO: Make configurable
      ),
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
        apiClient: _getIt<AicoApiClient>(),
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

  /// Reset all services (for testing)
  static Future<void> reset() async {
    await _getIt.reset();
    _isInitialized = false;
  }

  /// Dispose all services
  static Future<void> dispose() async {
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
