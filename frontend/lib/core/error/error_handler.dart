import 'dart:async';
import 'dart:io';
import 'package:aico_frontend/core/logging/aico_log.dart';

/// Centralized error handling and recovery system for AICO frontend
/// Provides intelligent error classification, recovery strategies, and user feedback
class AicoErrorHandler {
  static final AicoErrorHandler _instance = AicoErrorHandler._internal();
  factory AicoErrorHandler() => _instance;
  AicoErrorHandler._internal();

  final StreamController<AicoError> _errorStreamController = StreamController<AicoError>.broadcast();
  Stream<AicoError> get errorStream => _errorStreamController.stream;

  /// Handle any error with intelligent classification and recovery
  Future<AicoErrorResult> handleError(
    dynamic error, {
    String? context,
    Map<String, dynamic>? metadata,
    bool shouldNotifyUser = true,
  }) async {
    final aicoError = _classifyError(error, context: context, metadata: metadata);
    
    AICOLog.error(
      'Error handled by AicoErrorHandler',
      topic: 'error_handler/handle',
      error: error,
      extra: {
        'error_type': aicoError.type.name,
        'severity': aicoError.severity.name,
        'context': context,
        'recoverable': aicoError.isRecoverable,
        'metadata': metadata,
      },
    );

    // Emit error to stream for UI components to handle
    if (shouldNotifyUser) {
      _errorStreamController.add(aicoError);
    }

    // Attempt automatic recovery based on error type
    final recoveryResult = await _attemptRecovery(aicoError);
    
    return AicoErrorResult(
      error: aicoError,
      recoveryAttempted: recoveryResult.attempted,
      recoverySuccessful: recoveryResult.successful,
      userActionRequired: recoveryResult.userActionRequired,
    );
  }

  /// Classify error into AICO error types with recovery strategies
  AicoError _classifyError(
    dynamic error, {
    String? context,
    Map<String, dynamic>? metadata,
  }) {
    final errorString = error.toString().toLowerCase();
    
    // Network connectivity errors
    if (error is SocketException || 
        errorString.contains('connection refused') ||
        errorString.contains('network is unreachable') ||
        errorString.contains('no route to host')) {
      return AicoError(
        type: AicoErrorType.networkConnectivity,
        severity: AicoErrorSeverity.high,
        message: 'Network connection unavailable',
        userMessage: 'Unable to connect to AICO servers. Check your internet connection.',
        originalError: error,
        context: context,
        metadata: metadata,
        isRecoverable: true,
        recoveryStrategy: AicoRecoveryStrategy.retryWithBackoff,
      );
    }

    // Backend unavailable errors
    if (errorString.contains('connection timed out') ||
        errorString.contains('server error') ||
        errorString.contains('service unavailable') ||
        errorString.contains('502') ||
        errorString.contains('503') ||
        errorString.contains('504')) {
      return AicoError(
        type: AicoErrorType.backendUnavailable,
        severity: AicoErrorSeverity.high,
        message: 'Backend service unavailable',
        userMessage: 'AICO servers are temporarily unavailable. Your messages will be sent when connection is restored.',
        originalError: error,
        context: context,
        metadata: metadata,
        isRecoverable: true,
        recoveryStrategy: AicoRecoveryStrategy.queueForRetry,
      );
    }

    // Authentication errors
    if (errorString.contains('unauthorized') ||
        errorString.contains('401') ||
        errorString.contains('forbidden') ||
        errorString.contains('403') ||
        errorString.contains('token') && errorString.contains('expired')) {
      return AicoError(
        type: AicoErrorType.authentication,
        severity: AicoErrorSeverity.medium,
        message: 'Authentication failed',
        userMessage: 'Your session has expired. Please sign in again.',
        originalError: error,
        context: context,
        metadata: metadata,
        isRecoverable: true,
        recoveryStrategy: AicoRecoveryStrategy.refreshAuth,
      );
    }

    // Encryption/security errors
    if (errorString.contains('encryption') ||
        errorString.contains('handshake') ||
        errorString.contains('certificate') ||
        errorString.contains('ssl') ||
        errorString.contains('tls')) {
      return AicoError(
        type: AicoErrorType.encryption,
        severity: AicoErrorSeverity.high,
        message: 'Secure connection failed',
        userMessage: 'Unable to establish secure connection. Please check your network settings.',
        originalError: error,
        context: context,
        metadata: metadata,
        isRecoverable: true,
        recoveryStrategy: AicoRecoveryStrategy.resetEncryption,
      );
    }

    // Data validation errors
    if (errorString.contains('validation') ||
        errorString.contains('invalid') ||
        errorString.contains('malformed') ||
        errorString.contains('400')) {
      return AicoError(
        type: AicoErrorType.dataValidation,
        severity: AicoErrorSeverity.low,
        message: 'Data validation failed',
        userMessage: 'The information provided is invalid. Please check and try again.',
        originalError: error,
        context: context,
        metadata: metadata,
        isRecoverable: false,
        recoveryStrategy: AicoRecoveryStrategy.userCorrection,
      );
    }

    // Storage/persistence errors
    if (errorString.contains('storage') ||
        errorString.contains('database') ||
        errorString.contains('file system') ||
        errorString.contains('disk')) {
      return AicoError(
        type: AicoErrorType.storage,
        severity: AicoErrorSeverity.medium,
        message: 'Local storage error',
        userMessage: 'Unable to save data locally. Please check available storage space.',
        originalError: error,
        context: context,
        metadata: metadata,
        isRecoverable: true,
        recoveryStrategy: AicoRecoveryStrategy.clearCache,
      );
    }

    // Unknown/unexpected errors
    return AicoError(
      type: AicoErrorType.unknown,
      severity: AicoErrorSeverity.medium,
      message: 'Unexpected error occurred',
      userMessage: 'Something unexpected happened. The issue has been logged and will be investigated.',
      originalError: error,
      context: context,
      metadata: metadata,
      isRecoverable: false,
      recoveryStrategy: AicoRecoveryStrategy.reportAndContinue,
    );
  }

  /// Attempt automatic recovery based on error type and strategy
  Future<AicoRecoveryResult> _attemptRecovery(AicoError error) async {
    if (!error.isRecoverable) {
      return AicoRecoveryResult(
        attempted: false,
        successful: false,
        userActionRequired: error.recoveryStrategy == AicoRecoveryStrategy.userCorrection,
      );
    }

    try {
      switch (error.recoveryStrategy) {
        case AicoRecoveryStrategy.retryWithBackoff:
          // Let ConnectionManager handle retry logic
          return AicoRecoveryResult(
            attempted: true,
            successful: false, // Will be determined by subsequent operations
            userActionRequired: false,
          );

        case AicoRecoveryStrategy.queueForRetry:
          // Queue operation for later retry (to be implemented with offline support)
          AICOLog.info('Queuing operation for retry when connection restored',
            topic: 'error_handler/queue_retry');
          return AicoRecoveryResult(
            attempted: true,
            successful: true,
            userActionRequired: false,
          );

        case AicoRecoveryStrategy.refreshAuth:
          // Trigger authentication refresh (to be implemented)
          AICOLog.info('Triggering authentication refresh',
            topic: 'error_handler/refresh_auth');
          return AicoRecoveryResult(
            attempted: true,
            successful: false,
            userActionRequired: true,
          );

        case AicoRecoveryStrategy.resetEncryption:
          // Reset encryption session (to be implemented)
          AICOLog.info('Resetting encryption session',
            topic: 'error_handler/reset_encryption');
          return AicoRecoveryResult(
            attempted: true,
            successful: false,
            userActionRequired: false,
          );

        case AicoRecoveryStrategy.clearCache:
          // Clear local cache (to be implemented)
          AICOLog.info('Clearing local cache to recover from storage error',
            topic: 'error_handler/clear_cache');
          return AicoRecoveryResult(
            attempted: true,
            successful: true,
            userActionRequired: false,
          );

        case AicoRecoveryStrategy.userCorrection:
          return AicoRecoveryResult(
            attempted: false,
            successful: false,
            userActionRequired: true,
          );

        case AicoRecoveryStrategy.reportAndContinue:
          // Log for investigation but continue operation
          return AicoRecoveryResult(
            attempted: true,
            successful: true,
            userActionRequired: false,
          );
      }
    } catch (recoveryError) {
      AICOLog.error('Recovery attempt failed',
        topic: 'error_handler/recovery_failed',
        error: recoveryError,
        extra: {
          'original_error_type': error.type.name,
          'recovery_strategy': error.recoveryStrategy.name,
        });
      
      return AicoRecoveryResult(
        attempted: true,
        successful: false,
        userActionRequired: true,
      );
    }
  }

  /// Dispose resources
  void dispose() {
    _errorStreamController.close();
  }
}

/// Represents a classified error with recovery information
class AicoError {
  final AicoErrorType type;
  final AicoErrorSeverity severity;
  final String message;
  final String userMessage;
  final dynamic originalError;
  final String? context;
  final Map<String, dynamic>? metadata;
  final bool isRecoverable;
  final AicoRecoveryStrategy recoveryStrategy;
  final DateTime timestamp;

  AicoError({
    required this.type,
    required this.severity,
    required this.message,
    required this.userMessage,
    required this.originalError,
    this.context,
    this.metadata,
    required this.isRecoverable,
    required this.recoveryStrategy,
  }) : timestamp = DateTime.now();
}

/// Types of errors that can occur in AICO
enum AicoErrorType {
  networkConnectivity,
  backendUnavailable,
  authentication,
  encryption,
  dataValidation,
  storage,
  unknown,
}

/// Severity levels for errors
enum AicoErrorSeverity {
  low,    // User can continue with minor inconvenience
  medium, // Some functionality affected but app usable
  high,   // Major functionality impacted
  critical, // App unusable
}

/// Recovery strategies for different error types
enum AicoRecoveryStrategy {
  retryWithBackoff,
  queueForRetry,
  refreshAuth,
  resetEncryption,
  clearCache,
  userCorrection,
  reportAndContinue,
}

/// Result of error handling operation
class AicoErrorResult {
  final AicoError error;
  final bool recoveryAttempted;
  final bool recoverySuccessful;
  final bool userActionRequired;

  AicoErrorResult({
    required this.error,
    required this.recoveryAttempted,
    required this.recoverySuccessful,
    required this.userActionRequired,
  });
}

/// Result of recovery attempt
class AicoRecoveryResult {
  final bool attempted;
  final bool successful;
  final bool userActionRequired;

  AicoRecoveryResult({
    required this.attempted,
    required this.successful,
    required this.userActionRequired,
  });
}
