import 'dart:async';

import 'package:aico_frontend/core/logging/aico_log.dart';
import 'package:aico_frontend/core/error/resilient_operation.dart';
import 'package:aico_frontend/core/error/retry_manager.dart';
import 'package:aico_frontend/core/error/error_handler.dart';
import 'package:aico_frontend/networking/clients/unified_api_client.dart';
import 'package:aico_frontend/networking/services/connection_manager.dart';

/// Resilient API service that gracefully handles backend failures
/// and provides immediate UI feedback without throwing exceptions
class ResilientApiService {
  final UnifiedApiClient _apiClient;
  final ConnectionManager _connectionManager;
  final RetryManagerRegistry _retryRegistry = RetryManagerRegistry();

  ResilientApiService(this._apiClient, this._connectionManager);
  
  // Expose API client for direct access when needed
  UnifiedApiClient get apiClient => _apiClient;

  /// Execute API operation with full resilience features
  /// Returns null on failure and updates connection status immediately
  Future<T?> executeOperation<T>(
    Future<T> Function() operation, {
    String operationName = 'API Operation',
    Map<String, dynamic>? metadata,
  }) async {
    // Ensure connection manager is initialized
    if (!_connectionManager.isInitialized) {
      await _connectionManager.initialize();
    }

    final resilientOp = ResilientOperationPresets.apiCall(
      operationName,
      operation,
    ).withMetadata(metadata ?? {}).build();

    final result = await resilientOp.execute();

    if (result.isSuccess || result.isFallback) {
      // Success - ensure connection status is updated
      if (_connectionManager.health.status != InternalConnectionStatus.connected) {
        AICOLog.info('$operationName succeeded - backend is back online',
          topic: 'network/resilient_api/recovery');
      }
      return result.value;
    } else {
      // Update connection status based on error type
      final error = result.error!;
      switch (error.type) {
        case AicoErrorType.networkConnectivity:
        case AicoErrorType.backendUnavailable:
          _connectionManager.updateHealth(
            InternalConnectionStatus.disconnected,
            error.message,
          );
          break;
        case AicoErrorType.authentication:
          _connectionManager.updateHealth(
            InternalConnectionStatus.error,
            'Authentication required',
          );
          break;
        default:
          _connectionManager.updateHealth(
            InternalConnectionStatus.error,
            error.message,
          );
      }
      
      return null;
    }
  }

  /// Execute operation with enhanced retry logic for critical operations
  Future<T?> executeWithRetry<T>(
    Future<T> Function() operation, {
    String operationName = 'API Operation',
    int maxRetries = 3,
    T? fallbackValue,
    Map<String, dynamic>? metadata,
  }) async {
    final builder = ResilientOperationPresets.criticalOperation(
      operationName,
      operation,
      fallbackValue,
    ).withMetadata(metadata ?? {});

    // Override retry manager with custom settings if needed
    final customRetryManager = RetryManager(
      name: '${operationName}_custom',
      maxRetries: maxRetries,
      baseDelay: const Duration(seconds: 1),
      maxDelay: const Duration(seconds: 30),
    );

    final resilientOp = builder.withRetryManager(customRetryManager).build();
    final result = await resilientOp.execute();

    if (result.isSuccess || result.isFallback) {
      return result.value;
    }

    return null;
  }

  /// Check if backend is available without throwing exceptions
  Future<bool> isBackendAvailable() async {
    final resilientOp = ResilientOperationBuilder<dynamic>()
        .named('health_check')
        .operation(() => _apiClient.get('/health'))
        .withRetryManager(_retryRegistry.getManager(
          'health_check',
          maxRetries: 1, // Quick health check, don't retry much
          baseDelay: const Duration(milliseconds: 500),
        ))
        .silentErrors() // Don't notify user for health checks
        .build();

    final result = await resilientOp.execute();
    return result.isSuccess;
  }

  /// Get current connection status
  InternalConnectionStatus get connectionStatus => _connectionManager.health.status;
  
  /// Stream of connection health updates
  Stream<ConnectionHealth> get healthStream => _connectionManager.healthStream;
}
