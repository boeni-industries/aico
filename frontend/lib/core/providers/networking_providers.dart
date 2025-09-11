import 'package:aico_frontend/core/providers/offline_queue_provider.dart';
import 'package:aico_frontend/core/services/api_service.dart';
import 'package:aico_frontend/core/services/encryption_service.dart';
import 'package:aico_frontend/networking/clients/unified_api_client.dart';
import 'package:aico_frontend/networking/clients/websocket_client.dart';
import 'package:aico_frontend/networking/services/connection_manager.dart';
import 'package:aico_frontend/networking/services/token_manager.dart';
import 'package:aico_frontend/networking/services/user_service.dart';
import 'package:aico_frontend/networking/services/websocket_manager.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:aico_frontend/networking/services/resilient_api_service.dart';

/// Encryption service provider for networking - singleton
final networkingEncryptionServiceProvider = Provider<EncryptionService>((ref) {
  return EncryptionService();
});

/// Token manager provider for networking - singleton
final tokenManagerProvider = Provider<TokenManager>((ref) {
  return TokenManager();
});

/// WebSocket client provider
final webSocketClientProvider = Provider<WebSocketClient>((ref) {
  final encryptionService = ref.watch(networkingEncryptionServiceProvider);
  final tokenManager = ref.watch(tokenManagerProvider);
  
  return WebSocketClient(
    encryptionService: encryptionService,
    tokenManager: tokenManager,
  );
});

/// Connection manager provider
final connectionManagerProvider = Provider<ConnectionManager>((ref) {
  final webSocketClient = ref.watch(webSocketClientProvider);
  
  final connectionManager = ConnectionManager(webSocketClient);
  
  // Dispose when provider is disposed
  ref.onDispose(() {
    connectionManager.dispose();
  });
  
  return connectionManager;
});

/// Unified API client provider - singleton to ensure single encryption session
final unifiedApiClientProvider = Provider<UnifiedApiClient>((ref) {
  final encryptionService = ref.watch(networkingEncryptionServiceProvider);
  final tokenManager = ref.watch(tokenManagerProvider);
  final connectionManager = ref.watch(connectionManagerProvider);
  final offlineQueue = ref.watch(offlineQueueProvider);
  
  final client = UnifiedApiClient(
    encryptionService: encryptionService,
    tokenManager: tokenManager,
    connectionManager: connectionManager,
    offlineQueue: offlineQueue,
  );
  
  // Wire up TokenManager to use UnifiedApiClient for encrypted refresh requests
  tokenManager.setApiClient(client);
  
  // Ensure the client is disposed when the provider is disposed
  ref.onDispose(() {
    client.dispose();
  });
  
  return client;
});

/// WebSocket manager provider
final webSocketManagerProvider = Provider<WebSocketManager>((ref) {
  return WebSocketManager();
});

/// API service provider
final apiServiceProvider = Provider<ApiService>((ref) {
  final unifiedApiClient = ref.watch(unifiedApiClientProvider);
  return ApiService(unifiedApiClient);
});

/// Resilient API service provider
final resilientApiServiceProvider = Provider<ResilientApiService>((ref) {
  final unifiedApiClient = ref.watch(unifiedApiClientProvider);
  final connectionManager = ref.watch(connectionManagerProvider);
  return ResilientApiService(unifiedApiClient, connectionManager);
});

/// User service provider
final userServiceProvider = Provider<ApiUserService>((ref) {
  final tokenManager = ref.watch(tokenManagerProvider);
  final apiService = ref.watch(apiServiceProvider);
  return ApiUserService(
    apiService: apiService,
    tokenManager: tokenManager,
  );
});

