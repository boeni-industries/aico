import 'dart:async';
import 'dart:math';

import 'package:aico_frontend/core/error/circuit_breaker.dart';
import 'package:aico_frontend/core/logging/aico_log.dart';

/// Result of a retry operation containing the value and metadata
class RetryResult<T> {
  /// The successful result value
  final T value;
  
  /// Total number of attempts made (including the successful one)
  final int attempts;
  
  /// Total time spent in retry delays (not including operation execution time)
  final Duration totalRetryDelay;
  
  /// List of errors encountered during failed attempts (excluding the successful attempt)
  final List<dynamic> errors;

  RetryResult({
    required this.value,
    required this.attempts,
    this.totalRetryDelay = Duration.zero,
    this.errors = const [],
  });
  
  /// Whether this operation required retries
  bool get hadRetries => attempts > 1;
  
  /// Whether this operation succeeded on first attempt
  bool get succeededImmediately => attempts == 1;
}

/// Advanced retry manager with exponential backoff, jitter, and circuit breaker integration
class RetryManager {
  final String name;
  final int maxRetries;
  final Duration baseDelay;
  final Duration maxDelay;
  final double backoffMultiplier;
  final double jitterFactor;
  final CircuitBreaker? circuitBreaker;
  final bool Function(dynamic error)? retryCondition;

  RetryManager({
    required this.name,
    this.maxRetries = 3,
    this.baseDelay = const Duration(seconds: 1),
    this.maxDelay = const Duration(seconds: 30),
    this.backoffMultiplier = 2.0,
    this.jitterFactor = 0.1,
    this.circuitBreaker,
    this.retryCondition,
  });

  /// Execute operation with retry logic
  /// Returns a [RetryResult] containing the value and retry metadata
  Future<RetryResult<T>> execute<T>(
    Future<T> Function() operation, {
    String? operationName,
    Map<String, dynamic>? metadata,
  }) async {
    final opName = operationName ?? 'operation';
    var attempt = 0;
    var totalRetryDelay = Duration.zero;
    final errors = <dynamic>[];
    dynamic lastError;

    while (attempt <= maxRetries) {
      try {
        AICOLog.debug('Executing $opName (attempt ${attempt + 1}/${maxRetries + 1})',
          topic: 'retry_manager/attempt',
          extra: {
            'manager': name,
            'attempt': attempt + 1,
            'max_attempts': maxRetries + 1,
            'operation': opName,
            'metadata': metadata,
          });

        // Execute through circuit breaker if available
        final T result;
        if (circuitBreaker != null) {
          result = await circuitBreaker!.execute(operation);
        } else {
          result = await operation();
        }

        // Success - log and return with metadata
        final totalAttempts = attempt + 1;
        
        if (attempt > 0) {
          AICOLog.info('$opName succeeded after $totalAttempts attempts',
            topic: 'retry_manager/success_after_retry',
            extra: {
              'manager': name,
              'total_attempts': totalAttempts,
              'total_retry_delay_ms': totalRetryDelay.inMilliseconds,
              'operation': opName,
              'errors_encountered': errors.length,
            });
        } else {
          AICOLog.debug('$opName succeeded on first attempt',
            topic: 'retry_manager/immediate_success',
            extra: {
              'manager': name,
              'operation': opName,
            });
        }

        return RetryResult(
          value: result,
          attempts: totalAttempts,
          totalRetryDelay: totalRetryDelay,
          errors: List.unmodifiable(errors),
        );
      } catch (e) {
        lastError = e;
        errors.add(e);
        attempt++;

        // Check if we should retry this error
        if (!_shouldRetry(e) || attempt > maxRetries) {
          AICOLog.error('$opName failed after $attempt attempts',
            topic: 'retry_manager/final_failure',
            error: e,
            extra: {
              'manager': name,
              'total_attempts': attempt,
              'operation': opName,
              'should_retry': _shouldRetry(e),
              'exceeded_max_retries': attempt > maxRetries,
            });
          rethrow;
        }

        // Calculate delay for next attempt
        final delay = _calculateDelay(attempt - 1);
        totalRetryDelay += delay;
        
        AICOLog.warn('$opName failed, retrying in ${delay.inMilliseconds}ms',
          topic: 'retry_manager/retry_scheduled',
          error: e,
          extra: {
            'manager': name,
            'attempt': attempt,
            'next_attempt': attempt + 1,
            'delay_ms': delay.inMilliseconds,
            'total_retry_delay_ms': totalRetryDelay.inMilliseconds,
            'operation': opName,
            'error_type': e.runtimeType.toString(),
          });

        await Future.delayed(delay);
      }
    }

    // This should never be reached due to rethrow above, but for safety
    throw lastError ?? Exception('Retry manager failed without error');
  }

  /// Check if error should trigger a retry
  bool _shouldRetry(dynamic error) {
    // Use custom retry condition if provided
    if (retryCondition != null) {
      return retryCondition!(error);
    }

    // Default retry conditions
    final errorString = error.toString().toLowerCase();
    
    // Retry network connectivity issues
    if (errorString.contains('connection refused') ||
        errorString.contains('connection timed out') ||
        errorString.contains('network is unreachable') ||
        errorString.contains('temporary failure') ||
        errorString.contains('502') ||
        errorString.contains('503') ||
        errorString.contains('504')) {
      return true;
    }

    // Don't retry authentication or validation errors
    if (errorString.contains('401') ||
        errorString.contains('403') ||
        errorString.contains('400') ||
        errorString.contains('unauthorized') ||
        errorString.contains('forbidden') ||
        errorString.contains('validation')) {
      return false;
    }

    // Don't retry circuit breaker open exceptions
    if (error is CircuitBreakerOpenException) {
      return false;
    }

    // Default to retry for unknown errors (conservative approach)
    return true;
  }

  /// Calculate delay with exponential backoff and jitter
  Duration _calculateDelay(int attemptNumber) {
    // Exponential backoff: baseDelay * (backoffMultiplier ^ attemptNumber)
    final exponentialDelay = baseDelay.inMilliseconds * 
        pow(backoffMultiplier, attemptNumber);
    
    // Apply maximum delay cap
    final cappedDelay = min(exponentialDelay, maxDelay.inMilliseconds.toDouble());
    
    // Add jitter to prevent thundering herd
    final jitter = cappedDelay * jitterFactor * (Random().nextDouble() - 0.5);
    final finalDelay = cappedDelay + jitter;
    
    return Duration(milliseconds: max(0, finalDelay.round()));
  }
}

/// Retry manager registry for consistent retry policies across the app
class RetryManagerRegistry {
  static final RetryManagerRegistry _instance = RetryManagerRegistry._internal();
  factory RetryManagerRegistry() => _instance;
  RetryManagerRegistry._internal();

  final Map<String, RetryManager> _managers = {};

  /// Get or create retry manager with specific configuration
  RetryManager getManager(
    String name, {
    int maxRetries = 3,
    Duration baseDelay = const Duration(seconds: 1),
    Duration maxDelay = const Duration(seconds: 30),
    double backoffMultiplier = 2.0,
    double jitterFactor = 0.1,
    CircuitBreaker? circuitBreaker,
    bool Function(dynamic error)? retryCondition,
  }) {
    return _managers.putIfAbsent(
      name,
      () => RetryManager(
        name: name,
        maxRetries: maxRetries,
        baseDelay: baseDelay,
        maxDelay: maxDelay,
        backoffMultiplier: backoffMultiplier,
        jitterFactor: jitterFactor,
        circuitBreaker: circuitBreaker,
        retryCondition: retryCondition,
      ),
    );
  }

  /// Get predefined retry managers for common use cases
  RetryManager get apiRetryManager => getManager(
    'api_operations',
    maxRetries: 3,
    baseDelay: const Duration(seconds: 1),
    maxDelay: const Duration(seconds: 30),
    circuitBreaker: CircuitBreakerRegistry().getBreaker('api_circuit_breaker'),
  );

  RetryManager get authRetryManager => getManager(
    'auth_operations',
    maxRetries: 2,
    baseDelay: const Duration(seconds: 2),
    maxDelay: const Duration(seconds: 10),
    retryCondition: (error) {
      final errorString = error.toString().toLowerCase();
      // Only retry network issues, not auth failures
      return errorString.contains('connection') ||
             errorString.contains('timeout') ||
             errorString.contains('502') ||
             errorString.contains('503') ||
             errorString.contains('504');
    },
  );

  RetryManager get encryptionRetryManager => getManager(
    'encryption_operations',
    maxRetries: 2,
    baseDelay: const Duration(milliseconds: 500),
    maxDelay: const Duration(seconds: 5),
    retryCondition: (error) {
      final errorString = error.toString().toLowerCase();
      // Retry handshake failures but not certificate errors
      return errorString.contains('handshake') ||
             errorString.contains('connection');
    },
  );

  /// Get all managers
  Map<String, RetryManager> get managers => Map.unmodifiable(_managers);
}
