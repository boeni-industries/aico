import 'package:aico_frontend/core/di/modules/di_module.dart';
import 'package:aico_frontend/core/services/api_service.dart';
import 'package:aico_frontend/core/services/encryption_service.dart';
import 'package:aico_frontend/data/datasources/remote_user_datasource.dart';
import 'package:aico_frontend/networking/clients/unified_api_client.dart';
import 'package:aico_frontend/networking/clients/websocket_client.dart';
import 'package:aico_frontend/networking/repositories/user_repository.dart';
import 'package:aico_frontend/networking/services/connection_manager.dart';
import 'package:aico_frontend/networking/services/offline_queue.dart';
import 'package:aico_frontend/networking/services/token_manager.dart';
import 'package:get_it/get_it.dart';

/// Networking module for API clients and network-related services
class NetworkingModule implements DIModule {
  @override
  String get name => 'NetworkingModule';

  @override
  Future<void> register(GetIt getIt) async {
    // Core networking services
    getIt.registerLazySingleton<TokenManager>(() => TokenManager());
    getIt.registerLazySingleton<OfflineQueue>(() => OfflineQueue());
    
    // Connection manager
    getIt.registerLazySingleton<ConnectionManager>(
      () => ConnectionManager(
        getIt<WebSocketClient>(),
      ),
    );

    // Unified API client with encryption
    getIt.registerLazySingletonAsync<UnifiedApiClient>(
      () async {
        final encryptionService = getIt<EncryptionService>();
        final tokenManager = getIt<TokenManager>();
        
        final client = UnifiedApiClient(
          encryptionService: encryptionService,
          tokenManager: tokenManager,
        );
        
        await client.initialize();
        return client;
      },
    );

    // WebSocket client
    getIt.registerLazySingletonAsync<WebSocketClient>(
      () async {
        final encryptionService = getIt<EncryptionService>();
        final tokenManager = getIt<TokenManager>();
        
        final client = WebSocketClient(
          encryptionService: encryptionService,
          tokenManager: tokenManager,
        );
        
        return client;
      },
    );

    // Initialize async services
    await _initializeAsyncServices(getIt);

    // API Service layer
    getIt.registerLazySingleton<ApiService>(
      () => ApiService(getIt<UnifiedApiClient>()),
    );

    // Data sources
    getIt.registerLazySingleton<RemoteUserDataSource>(
      () => RemoteUserDataSource(getIt<UnifiedApiClient>()),
    );

    // Register ApiUserService (networking layer service)
    getIt.registerLazySingleton<ApiUserService>(
      () => ApiUserService(
        apiService: getIt<ApiService>(),
        tokenManager: getIt<TokenManager>(),
      ),
    );
  }

  /// Initialize services that require async setup
  Future<void> _initializeAsyncServices(GetIt getIt) async {
    // Wait for UnifiedApiClient to be ready
    await getIt.isReady<UnifiedApiClient>();
    
    // Initialize UnifiedApiClient
    final apiClient = getIt<UnifiedApiClient>();
    await apiClient.initialize();
    
    // Wait for WebSocket client to be ready
    await getIt.isReady<WebSocketClient>();
  }

  @override
  Future<void> dispose(GetIt getIt) async {
    // Dispose services in reverse order
    if (getIt.isRegistered<WebSocketClient>()) {
      await getIt<WebSocketClient>().dispose();
    }
    
    if (getIt.isRegistered<UnifiedApiClient>()) {
      await getIt<UnifiedApiClient>().dispose();
    }
    
    // TokenManager doesn't have dispose method
    // if (getIt.isRegistered<TokenManager>()) {
    //   await getIt<TokenManager>().dispose();
    // }
  }
}
