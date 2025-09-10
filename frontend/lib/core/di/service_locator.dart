import 'package:aico_frontend/core/di/modules/core_module.dart';
import 'package:aico_frontend/core/di/modules/di_module.dart';
import 'package:aico_frontend/core/di/modules/domain_module.dart';
import 'package:aico_frontend/core/di/modules/networking_module.dart';
import 'package:aico_frontend/core/di/modules/presentation_module.dart';
import 'package:get_it/get_it.dart';

/// Environment configuration for dependency injection
enum Environment { development, staging, production }

/// Centralized dependency injection setup for the AICO app
/// Configures all services, repositories, and BLoCs with proper lifecycle management
class ServiceLocator {
  static final GetIt _getIt = GetIt.instance;
  static bool _isInitialized = false;
  static final List<DIModule> _modules = [];

  static Future<void> initialize({Environment environment = Environment.development}) async {
    if (_isInitialized) return;

    // Initialize modules in dependency order
    _modules.addAll([
      CoreModule(),
      NetworkingModule(),
      DomainModule(),
      PresentationModule(),
    ]);

    // Register all modules
    for (final module in _modules) {
      await module.register(_getIt);
    }

    _isInitialized = true;
  }

  /// Dispose all services and reset the service locator
  static Future<void> dispose() async {
    if (!_isInitialized) return;

    // Dispose modules in reverse order
    for (final module in _modules.reversed) {
      await module.dispose(_getIt);
    }

    await _getIt.reset();
    _modules.clear();
    _isInitialized = false;
  }

  /// Get service instance with type safety
  static T get<T extends Object>() => _getIt.getService<T>();

  /// Check if service is registered
  static bool isRegistered<T extends Object>() => _getIt.hasService<T>();

  /// Waits until all registered async singletons are ready
  static Future<void> allReady() => _getIt.allReady();

  /// Reset all services (for testing)
  static Future<void> reset() async {
    await dispose();
  }
}

/// Exception for service locator errors
class ServiceLocatorException implements Exception {
  final String message;
  const ServiceLocatorException(this.message);

  @override
  String toString() => 'ServiceLocatorException: $message';
}
