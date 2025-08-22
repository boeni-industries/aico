import 'package:get_it/get_it.dart';
import 'package:hydrated_bloc/hydrated_bloc.dart';
import 'package:path_provider/path_provider.dart';
import '../services/api_client.dart';
import '../services/local_storage.dart';
import '../utils/aico_paths.dart';
import '../../features/connection/bloc/connection_bloc.dart';
import '../../features/settings/bloc/settings_bloc.dart';
import '../../features/connection/repositories/connection_repository.dart';
import '../../features/settings/repositories/settings_repository.dart';
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
    // HTTP client
    _getIt.registerLazySingleton<http.Client>(() => http.Client());

    // API client
    _getIt.registerLazySingleton<ApiClient>(
      () => ApiClient(
        httpClient: _getIt<http.Client>(),
        baseUrl: 'http://localhost:8000', // TODO: Make configurable
      ),
    );

    // Local storage
    _getIt.registerLazySingleton<LocalStorage>(() => LocalStorage());
  }

  /// Register repositories
  static Future<void> _registerRepositories() async {
    // Connection repository
    _getIt.registerLazySingleton<ConnectionRepository>(
      () => ConnectionRepository(
        apiClient: _getIt<ApiClient>(),
        localStorage: _getIt<LocalStorage>(),
      ),
    );

    // Settings repository
    _getIt.registerLazySingleton<SettingsRepository>(
      () => SettingsRepository(
        localStorage: _getIt<LocalStorage>(),
      ),
    );
  }

  /// Register BLoCs
  static Future<void> _registerBlocs() async {
    // Connection BLoC (HydratedBloc for persistence)
    _getIt.registerLazySingleton<ConnectionBloc>(
      () => ConnectionBloc(
        repository: _getIt<ConnectionRepository>(),
      ),
    );

    // Settings BLoC (HydratedBloc for persistence)
    _getIt.registerLazySingleton<SettingsBloc>(
      () => SettingsBloc(
        repository: _getIt<SettingsRepository>(),
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
    // Close HTTP client
    if (_getIt.isRegistered<http.Client>()) {
      _getIt<http.Client>().close();
    }

    // Close API client
    if (_getIt.isRegistered<ApiClient>()) {
      _getIt<ApiClient>().dispose();
    }

    // Close BLoCs
    if (_getIt.isRegistered<ConnectionBloc>()) {
      await _getIt<ConnectionBloc>().close();
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
