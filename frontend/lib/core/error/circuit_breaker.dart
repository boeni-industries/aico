import 'dart:async';
import 'package:aico_frontend/core/logging/aico_log.dart';

/// Circuit breaker pattern implementation for AICO frontend
/// Prevents cascading failures by temporarily stopping requests to failing services
class CircuitBreaker {
  final String name;
  final int failureThreshold;
  final Duration timeout;
  final Duration resetTimeout;
  
  CircuitBreakerState _state = CircuitBreakerState.closed;
  int _failureCount = 0;
  DateTime? _nextAttemptTime;

  CircuitBreaker({
    required this.name,
    this.failureThreshold = 5,
    this.timeout = const Duration(seconds: 30),
    this.resetTimeout = const Duration(minutes: 1),
  });

  /// Execute operation through circuit breaker
  Future<T> execute<T>(Future<T> Function() operation) async {
    if (_state == CircuitBreakerState.open) {
      if (_shouldAttemptReset()) {
        _state = CircuitBreakerState.halfOpen;
        AICOLog.info('Circuit breaker transitioning to half-open',
          topic: 'circuit_breaker/half_open',
          extra: {'name': name});
      } else {
        throw CircuitBreakerOpenException(
          'Circuit breaker is open for $name. Next attempt at $_nextAttemptTime'
        );
      }
    }

    try {
      final result = await operation().timeout(timeout);
      _onSuccess();
      return result;
    } catch (e) {
      _onFailure();
      rethrow;
    }
  }

  /// Check if operation is allowed
  bool get isCallAllowed => _state != CircuitBreakerState.open || _shouldAttemptReset();

  /// Get current state
  CircuitBreakerState get state => _state;

  /// Get failure count
  int get failureCount => _failureCount;

  /// Get next attempt time (when circuit is open)
  DateTime? get nextAttemptTime => _nextAttemptTime;

  void _onSuccess() {
    _failureCount = 0;
    _nextAttemptTime = null;
    
    if (_state == CircuitBreakerState.halfOpen) {
      _state = CircuitBreakerState.closed;
      AICOLog.info('Circuit breaker reset to closed',
        topic: 'circuit_breaker/closed',
        extra: {'name': name});
    }
  }

  void _onFailure() {
    _failureCount++;

    if (_failureCount >= failureThreshold) {
      _state = CircuitBreakerState.open;
      _nextAttemptTime = DateTime.now().add(resetTimeout);
      
      AICOLog.warn('Circuit breaker opened due to failures',
        topic: 'circuit_breaker/opened',
        extra: {
          'name': name,
          'failure_count': _failureCount,
          'next_attempt': _nextAttemptTime?.toIso8601String(),
        });
    }
  }

  bool _shouldAttemptReset() {
    return _nextAttemptTime != null && DateTime.now().isAfter(_nextAttemptTime!);
  }

  /// Reset circuit breaker manually
  void reset() {
    _state = CircuitBreakerState.closed;
    _failureCount = 0;
    _nextAttemptTime = null;
    
    AICOLog.info('Circuit breaker manually reset',
      topic: 'circuit_breaker/manual_reset',
      extra: {'name': name});
  }
}

/// Circuit breaker states
enum CircuitBreakerState {
  closed,   // Normal operation
  open,     // Blocking requests due to failures
  halfOpen, // Testing if service has recovered
}

/// Exception thrown when circuit breaker is open
class CircuitBreakerOpenException implements Exception {
  final String message;
  CircuitBreakerOpenException(this.message);
  
  @override
  String toString() => 'CircuitBreakerOpenException: $message';
}

/// Circuit breaker registry for managing multiple breakers
class CircuitBreakerRegistry {
  static final CircuitBreakerRegistry _instance = CircuitBreakerRegistry._internal();
  factory CircuitBreakerRegistry() => _instance;
  CircuitBreakerRegistry._internal();

  final Map<String, CircuitBreaker> _breakers = {};

  /// Get or create circuit breaker
  CircuitBreaker getBreaker(
    String name, {
    int failureThreshold = 5,
    Duration timeout = const Duration(seconds: 30),
    Duration resetTimeout = const Duration(minutes: 1),
  }) {
    return _breakers.putIfAbsent(
      name,
      () => CircuitBreaker(
        name: name,
        failureThreshold: failureThreshold,
        timeout: timeout,
        resetTimeout: resetTimeout,
      ),
    );
  }

  /// Get all breakers
  Map<String, CircuitBreaker> get breakers => Map.unmodifiable(_breakers);

  /// Reset all breakers
  void resetAll() {
    for (final breaker in _breakers.values) {
      breaker.reset();
    }
    AICOLog.info('All circuit breakers reset',
      topic: 'circuit_breaker_registry/reset_all');
  }

  /// Get breakers by state
  List<CircuitBreaker> getBreakersByState(CircuitBreakerState state) {
    return _breakers.values.where((breaker) => breaker.state == state).toList();
  }
}
