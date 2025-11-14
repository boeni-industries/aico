import 'dart:async';
import 'package:aico_frontend/core/error/error_handler.dart';
import 'package:aico_frontend/core/error/retry_manager.dart';
import 'package:aico_frontend/core/logging/aico_log.dart';

/// Wrapper for resilient operations that combines error handling, retries, and circuit breaking
class ResilientOperation<T> {
  final String name;
  final Future<T> Function() operation;
  final RetryManager? retryManager;
  final AicoErrorHandler errorHandler;
  final Map<String, dynamic>? metadata;
  final bool shouldNotifyUser;
  final T? fallbackValue;
  final Future<T> Function()? fallbackOperation;

  ResilientOperation({
    required this.name,
    required this.operation,
    this.retryManager,
    AicoErrorHandler? errorHandler,
    this.metadata,
    this.shouldNotifyUser = true,
    this.fallbackValue,
    this.fallbackOperation,
  }) : errorHandler = errorHandler ?? AicoErrorHandler();

  /// Execute the operation with full resilience features
  Future<ResilientResult<T>> execute() async {
    final startTime = DateTime.now();
    
    try {
      AICOLog.debug('Starting resilient operation: $name',
        topic: 'resilient_operation/start',
        extra: {
          'operation': name,
          'has_retry_manager': retryManager != null,
          'has_fallback_value': fallbackValue != null,
          'has_fallback_operation': fallbackOperation != null,
          'metadata': metadata,
        });

      final T result;
      final int attemptsCount;
      final Duration totalRetryDelay;
      
      if (retryManager != null) {
        // Execute with retry logic
        final retryResult = await retryManager!.execute(
          operation,
          operationName: name,
          metadata: metadata,
        );
        result = retryResult.value;
        attemptsCount = retryResult.attempts;
        totalRetryDelay = retryResult.totalRetryDelay;
        
        // Log retry information if retries occurred
        if (retryResult.hadRetries) {
          AICOLog.info('Resilient operation succeeded after retries: $name',
            topic: 'resilient_operation/success_with_retries',
            extra: {
              'operation': name,
              'total_attempts': attemptsCount,
              'retry_delay_ms': totalRetryDelay.inMilliseconds,
              'errors_encountered': retryResult.errors.length,
              'metadata': metadata,
            });
        }
      } else {
        // Execute directly without retry
        result = await operation();
        attemptsCount = 1;
        totalRetryDelay = Duration.zero;
      }

      final duration = DateTime.now().difference(startTime);
      
      AICOLog.info('Resilient operation succeeded: $name',
        topic: 'resilient_operation/success',
        extra: {
          'operation': name,
          'duration_ms': duration.inMilliseconds,
          'attempts': attemptsCount,
          'had_retries': attemptsCount > 1,
          'retry_delay_ms': totalRetryDelay.inMilliseconds,
          'metadata': metadata,
        });

      return ResilientResult.success(
        value: result,
        duration: duration,
        attemptsCount: attemptsCount,
      );

    } catch (error) {
      final duration = DateTime.now().difference(startTime);
      
      // Handle error through error handler
      final errorResult = await errorHandler.handleError(
        error,
        context: 'resilient_operation:$name',
        metadata: metadata,
        shouldNotifyUser: shouldNotifyUser,
      );

      AICOLog.warn('Resilient operation failed: $name',
        topic: 'resilient_operation/failed',
        error: error,
        extra: {
          'operation': name,
          'duration_ms': duration.inMilliseconds,
          'error_type': errorResult.error.type.name,
          'recovery_attempted': errorResult.recoveryAttempted,
          'recovery_successful': errorResult.recoverySuccessful,
          'metadata': metadata,
        });

      // Try fallback if available
      if (fallbackOperation != null || fallbackValue != null) {
        try {
          final T fallbackResult;
          if (fallbackOperation != null) {
            fallbackResult = await fallbackOperation!();
            AICOLog.info('Fallback operation succeeded for: $name',
              topic: 'resilient_operation/fallback_success');
          } else {
            fallbackResult = fallbackValue as T;
            AICOLog.info('Using fallback value for: $name',
              topic: 'resilient_operation/fallback_value');
          }

          return ResilientResult.fallback(
            value: fallbackResult,
            originalError: errorResult.error,
            duration: DateTime.now().difference(startTime),
          );
        } catch (fallbackError) {
          AICOLog.error('Fallback also failed for: $name',
            topic: 'resilient_operation/fallback_failed',
            error: fallbackError);
        }
      }

      return ResilientResult.failure(
        error: errorResult.error,
        duration: duration,
        recoveryAttempted: errorResult.recoveryAttempted,
        userActionRequired: errorResult.userActionRequired,
      );
    }
  }
}

/// Result of a resilient operation
class ResilientResult<T> {
  final T? value;
  final AicoError? error;
  final Duration duration;
  final ResilientResultType type;
  final bool recoveryAttempted;
  final bool userActionRequired;
  final int attemptsCount;

  ResilientResult._({
    this.value,
    this.error,
    required this.duration,
    required this.type,
    this.recoveryAttempted = false,
    this.userActionRequired = false,
    this.attemptsCount = 1,
  });

  factory ResilientResult.success({
    required T value,
    required Duration duration,
    int attemptsCount = 1,
  }) {
    return ResilientResult._(
      value: value,
      duration: duration,
      type: ResilientResultType.success,
      attemptsCount: attemptsCount,
    );
  }

  factory ResilientResult.fallback({
    required T value,
    required AicoError originalError,
    required Duration duration,
  }) {
    return ResilientResult._(
      value: value,
      error: originalError,
      duration: duration,
      type: ResilientResultType.fallback,
    );
  }

  factory ResilientResult.failure({
    required AicoError error,
    required Duration duration,
    bool recoveryAttempted = false,
    bool userActionRequired = false,
  }) {
    return ResilientResult._(
      error: error,
      duration: duration,
      type: ResilientResultType.failure,
      recoveryAttempted: recoveryAttempted,
      userActionRequired: userActionRequired,
    );
  }

  bool get isSuccess => type == ResilientResultType.success;
  bool get isFallback => type == ResilientResultType.fallback;
  bool get isFailure => type == ResilientResultType.failure;
  bool get hasValue => value != null;
}

enum ResilientResultType {
  success,
  fallback,
  failure,
}

/// Builder for creating resilient operations with fluent API
class ResilientOperationBuilder<T> {
  String? _name;
  Future<T> Function()? _operation;
  RetryManager? _retryManager;
  AicoErrorHandler? _errorHandler;
  Map<String, dynamic>? _metadata;
  bool _shouldNotifyUser = true;
  T? _fallbackValue;
  Future<T> Function()? _fallbackOperation;

  ResilientOperationBuilder<T> named(String name) {
    _name = name;
    return this;
  }

  ResilientOperationBuilder<T> operation(Future<T> Function() op) {
    _operation = op;
    return this;
  }

  ResilientOperationBuilder<T> withRetryManager(RetryManager manager) {
    _retryManager = manager;
    return this;
  }

  ResilientOperationBuilder<T> withErrorHandler(AicoErrorHandler handler) {
    _errorHandler = handler;
    return this;
  }

  ResilientOperationBuilder<T> withMetadata(Map<String, dynamic> metadata) {
    _metadata = metadata;
    return this;
  }

  ResilientOperationBuilder<T> silentErrors() {
    _shouldNotifyUser = false;
    return this;
  }

  ResilientOperationBuilder<T> withFallbackValue(T value) {
    _fallbackValue = value;
    return this;
  }

  ResilientOperationBuilder<T> withFallbackOperation(Future<T> Function() fallback) {
    _fallbackOperation = fallback;
    return this;
  }

  ResilientOperation<T> build() {
    if (_name == null || _operation == null) {
      throw ArgumentError('Name and operation are required');
    }

    return ResilientOperation<T>(
      name: _name!,
      operation: _operation!,
      retryManager: _retryManager,
      errorHandler: _errorHandler,
      metadata: _metadata,
      shouldNotifyUser: _shouldNotifyUser,
      fallbackValue: _fallbackValue,
      fallbackOperation: _fallbackOperation,
    );
  }
}

/// Convenience methods for common resilient operations
extension ResilientOperations<T> on Future<T> Function() {
  /// Convert a function to a resilient operation
  ResilientOperationBuilder<T> resilient(String name) {
    return ResilientOperationBuilder<T>()
        .named(name)
        .operation(this);
  }
}

/// Predefined resilient operation configurations
class ResilientOperationPresets {
  static ResilientOperationBuilder<T> apiCall<T>(
    String name,
    Future<T> Function() operation,
  ) {
    return ResilientOperationBuilder<T>()
        .named('api_$name')
        .operation(operation)
        .withRetryManager(RetryManagerRegistry().apiRetryManager);
  }

  static ResilientOperationBuilder<T> authOperation<T>(
    String name,
    Future<T> Function() operation,
  ) {
    return ResilientOperationBuilder<T>()
        .named('auth_$name')
        .operation(operation)
        .withRetryManager(RetryManagerRegistry().authRetryManager);
  }

  static ResilientOperationBuilder<T> encryptionOperation<T>(
    String name,
    Future<T> Function() operation,
  ) {
    return ResilientOperationBuilder<T>()
        .named('encryption_$name')
        .operation(operation)
        .withRetryManager(RetryManagerRegistry().encryptionRetryManager);
  }

  static ResilientOperationBuilder<T> criticalOperation<T>(
    String name,
    Future<T> Function() operation,
    T fallbackValue,
  ) {
    return ResilientOperationBuilder<T>()
        .named('critical_$name')
        .operation(operation)
        .withRetryManager(RetryManagerRegistry().apiRetryManager)
        .withFallbackValue(fallbackValue);
  }
}
