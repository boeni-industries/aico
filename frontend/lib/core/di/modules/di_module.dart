import 'package:get_it/get_it.dart';

/// Base interface for dependency injection modules
abstract class DIModule {
  /// Register dependencies for this module
  Future<void> register(GetIt getIt);
  
  /// Dispose resources for this module
  Future<void> dispose(GetIt getIt);
  
  /// Module name for debugging
  String get name;
}

/// Exception thrown when a service is not registered
class ServiceNotRegisteredException implements Exception {
  final String message;
  
  const ServiceNotRegisteredException(this.message);
  
  @override
  String toString() => 'ServiceNotRegisteredException: $message';
}

/// Extension for type-safe service access
extension ServiceLocatorExtensions on GetIt {
  /// Get service with type safety and better error messages
  T getService<T extends Object>() {
    if (!isRegistered<T>()) {
      throw ServiceNotRegisteredException('Service ${T.toString()} not registered');
    }
    return get<T>();
  }
  
  /// Check if service is registered
  bool hasService<T extends Object>() => isRegistered<T>();
}
