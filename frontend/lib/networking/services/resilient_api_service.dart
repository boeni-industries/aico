import 'dart:async';
import 'dart:io';

import 'package:aico_frontend/core/logging/aico_log.dart';
import 'package:aico_frontend/networking/clients/unified_api_client.dart';
import 'package:aico_frontend/networking/services/connection_manager.dart';

/// Resilient API service that gracefully handles backend failures
/// and provides immediate UI feedback without throwing exceptions
class ResilientApiService {
  final UnifiedApiClient _apiClient;
  final ConnectionManager _connectionManager;

  ResilientApiService(this._apiClient, this._connectionManager);
  
  // Expose API client for direct access when needed
  UnifiedApiClient get apiClient => _apiClient;

  /// Execute API operation with graceful error handling
  /// Returns null on failure and updates connection status immediately
  Future<T?> executeOperation<T>(
    Future<T> Function() operation, {
    String operationName = 'API Operation',
  }) async {
    try {
      // Ensure connection manager is initialized
      if (!_connectionManager.isInitialized) {
        await _connectionManager.initialize();
      }

      // Execute the operation
      final result = await operation();
      
      // Success - ensure connection status is updated
      if (_connectionManager.health.status != ConnectionStatus.connected) {
        AICOLog.info('$operationName succeeded - backend is back online',
          topic: 'network/resilient_api/recovery');
      }
      
      return result;
      
    } catch (e) {
      // Gracefully handle all exceptions without throwing
      AICOLog.warn('$operationName failed gracefully',
        topic: 'network/resilient_api/failure',
        extra: {
          'operation': operationName,
          'error': e.toString(),
          'error_type': e.runtimeType.toString(),
        });

      // Immediately update connection status based on error type
      if (e is SocketException || e.toString().contains('connection refused')) {
        // Backend is down - update status immediately
        _connectionManager.updateHealth(
          ConnectionStatus.disconnected, 
          'Backend unavailable: ${e.toString()}'
        );
        
        AICOLog.info('Backend detected as unavailable - UI should show disconnected state',
          topic: 'network/resilient_api/backend_down');
      } else {
        // Other error - mark as error state
        _connectionManager.updateHealth(
          ConnectionStatus.error,
          'API error: ${e.toString()}'
        );
      }

      // Return null instead of throwing - let UI handle gracefully
      return null;
    }
  }

  /// Execute operation with retry logic for critical operations
  Future<T?> executeWithRetry<T>(
    Future<T> Function() operation, {
    String operationName = 'API Operation',
    int maxRetries = 3,
    Duration retryDelay = const Duration(seconds: 2),
  }) async {
    for (int attempt = 0; attempt <= maxRetries; attempt++) {
      final result = await executeOperation<T>(
        operation,
        operationName: '$operationName (attempt ${attempt + 1})',
      );
      
      if (result != null) {
        return result;
      }
      
      // If not the last attempt, wait before retrying
      if (attempt < maxRetries) {
        AICOLog.debug('Retrying $operationName in ${retryDelay.inSeconds}s',
          topic: 'network/resilient_api/retry');
        await Future.delayed(retryDelay);
      }
    }
    
    AICOLog.error('$operationName failed after all retry attempts',
      topic: 'network/resilient_api/final_failure');
    return null;
  }

  /// Check if backend is available without throwing exceptions
  Future<bool> isBackendAvailable() async {
    final result = await executeOperation<dynamic>(
      () => _apiClient.get('/health'),
      operationName: 'Backend Health Check',
    );
    
    return result != null;
  }

  /// Get current connection status
  ConnectionStatus get connectionStatus => _connectionManager.health.status;
  
  /// Stream of connection health updates
  Stream<ConnectionHealth> get healthStream => _connectionManager.healthStream;
}
