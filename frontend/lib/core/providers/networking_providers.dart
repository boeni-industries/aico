import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:aico_frontend/core/services/api_service.dart';
import 'package:aico_frontend/core/services/encryption_service.dart';
import 'package:aico_frontend/networking/clients/unified_api_client.dart';
import 'package:aico_frontend/networking/services/offline_queue.dart';
import 'package:aico_frontend/networking/services/token_manager.dart';
import 'package:aico_frontend/networking/services/user_service.dart';
import 'package:aico_frontend/networking/services/websocket_manager.dart';

/// Encryption service provider for networking - singleton
final networkingEncryptionServiceProvider = Provider<EncryptionService>((ref) {
  return EncryptionService();
});

/// Token manager provider for networking - singleton  
final networkingTokenManagerProvider = Provider<TokenManager>((ref) {
  return TokenManager();
});

/// Unified API client provider - singleton to ensure single encryption session
final unifiedApiClientProvider = Provider<UnifiedApiClient>((ref) {
  final encryptionService = ref.watch(networkingEncryptionServiceProvider);
  final tokenManager = ref.watch(networkingTokenManagerProvider);
  
  final client = UnifiedApiClient(
    encryptionService: encryptionService,
    tokenManager: tokenManager,
  );
  
  // Wire up TokenManager to use this API client for encrypted refresh requests
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

/// User service provider
final userServiceProvider = Provider<ApiUserService>((ref) {
  final tokenManager = ref.watch(networkingTokenManagerProvider);
  final apiService = ref.watch(apiServiceProvider);
  return ApiUserService(
    apiService: apiService,
    tokenManager: tokenManager,
  );
});

/// Offline queue provider
final offlineQueueProvider = Provider<OfflineQueue>((ref) {
  return OfflineQueue(ref);
});
