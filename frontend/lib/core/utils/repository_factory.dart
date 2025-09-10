import 'package:aico_frontend/core/di/service_locator.dart';
import 'package:aico_frontend/core/services/encryption_service.dart';
import 'package:aico_frontend/core/services/local_storage.dart';
import 'package:aico_frontend/networking/clients/unified_api_client.dart';
import 'package:aico_frontend/networking/services/token_manager.dart';
import 'package:get_it/get_it.dart';

/// Factory for creating repositories with unified error handling and dependency injection
/// Provides consistent patterns for data layer instantiation
class RepositoryFactory {
  static final GetIt _getIt = GetIt.instance;

  /// Create repository with API client and local storage dependencies
  static T create<T extends Object>({
    required T Function(UnifiedApiClient apiClient, LocalStorage localStorage) factory,
    UnifiedApiClient? apiClient,
    LocalStorage? localStorage,
    bool registerSingleton = true,
  }) {
    try {
      // Get or create dependencies
      final client = apiClient ?? _getOrCreateUnifiedApiClient();
      final storage = localStorage ?? _getOrCreateLocalStorage();
      
      // Create repository instance
      final repository = factory(client, storage);
      
      // Register with service locator
      if (registerSingleton && !_getIt.isRegistered<T>()) {
        _getIt.registerSingleton<T>(repository);
      }
      
      return repository;
    } catch (e) {
      throw RepositoryCreationException('Failed to create repository<$T>: $e');
    }
  }

  /// Create repository with only API client dependency
  static T createApiOnly<T extends Object>({
    required T Function(UnifiedApiClient apiClient) factory,
    UnifiedApiClient? apiClient,
    bool registerSingleton = true,
  }) {
    try {
      final client = apiClient ?? _getOrCreateUnifiedApiClient();
      final repository = factory(client);
      
      if (registerSingleton && !_getIt.isRegistered<T>()) {
        _getIt.registerSingleton<T>(repository);
      }
      
      return repository;
    } catch (e) {
      throw RepositoryCreationException('Failed to create API repository<$T>: $e');
    }
  }

  /// Create repository with only local storage dependency
  static T createLocalOnly<T extends Object>({
    required T Function(LocalStorage localStorage) factory,
    LocalStorage? localStorage,
    bool registerSingleton = true,
  }) {
    try {
      final storage = localStorage ?? _getOrCreateLocalStorage();
      final repository = factory(storage);
      
      if (registerSingleton && !_getIt.isRegistered<T>()) {
        _getIt.registerSingleton<T>(repository);
      }
      
      return repository;
    } catch (e) {
      throw RepositoryCreationException('Failed to create local repository<$T>: $e');
    }
  }

  /// Get existing repository from service locator
  static T getRepository<T extends Object>() {
    try {
      return _getIt.get<T>();
    } catch (e) {
      throw RepositoryRetrievalException('Failed to retrieve repository<$T>: $e');
    }
  }

  /// Check if repository is registered
  static bool isRegistered<T extends Object>() {
    return _getIt.isRegistered<T>();
  }

  /// Get or create API client
  static UnifiedApiClient _getOrCreateUnifiedApiClient() {
    if (_getIt.isRegistered<UnifiedApiClient>()) {
      return _getIt.get<UnifiedApiClient>();
    }
    final client = UnifiedApiClient(
      encryptionService: ServiceLocator.get<EncryptionService>(),
      tokenManager: ServiceLocator.get<TokenManager>(),
      baseUrl: 'http://localhost:8771/api/v1',
    );
    _getIt.registerSingleton<UnifiedApiClient>(client);
    return client;
  }

  /// Get or create local storage
  static LocalStorage _getOrCreateLocalStorage() {
    if (_getIt.isRegistered<LocalStorage>()) {
      return _getIt.get<LocalStorage>();
    }
    
    final storage = LocalStorage();
    _getIt.registerSingleton<LocalStorage>(storage);
    return storage;
  }

  /// Dispose repository and its dependencies
  static Future<void> disposeRepository<T extends Object>() async {
    if (_getIt.isRegistered<T>()) {
      final repository = _getIt.get<T>();
      
      // If repository has dispose method, call it
      if (repository is Disposable) {
        await (repository as Disposable).dispose();
      }
      
      await _getIt.unregister<T>();
    }
  }

  /// Clear all registered repositories
  static Future<void> clearAll() async {
    await _getIt.reset();
  }
}

/// Interface for disposable repositories
abstract class Disposable {
  Future<void> dispose();
}

/// Exception for repository creation errors
class RepositoryCreationException implements Exception {
  final String message;
  const RepositoryCreationException(this.message);

  @override
  String toString() => 'RepositoryCreationException: $message';
}

/// Exception for repository retrieval errors
class RepositoryRetrievalException implements Exception {
  final String message;
  const RepositoryRetrievalException(this.message);

  @override
  String toString() => 'RepositoryRetrievalException: $message';
}
