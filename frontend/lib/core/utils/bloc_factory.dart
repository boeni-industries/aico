import 'package:hydrated_bloc/hydrated_bloc.dart';
import 'package:get_it/get_it.dart';

/// Factory for creating BLoCs with consistent setup and error handling
/// Provides DRY patterns for BLoC instantiation across the app
class BlocFactory {
  static final GetIt _getIt = GetIt.instance;

  /// Create a HydratedBloc with automatic persistence
  static T createHydratedBloc<T extends HydratedBloc>({
    required T Function() create,
    String? storageKey,
  }) {
    try {
      final bloc = create();
      
      // Register with service locator for dependency injection
      if (!_getIt.isRegistered<T>()) {
        _getIt.registerSingleton<T>(bloc);
      }
      
      return bloc;
    } catch (e) {
      throw BlocCreationException('Failed to create HydratedBloc<$T>: $e');
    }
  }

  /// Create a regular Bloc
  static T createBloc<T extends Bloc>({
    required T Function() create,
    bool registerSingleton = false,
  }) {
    try {
      final bloc = create();
      
      // Optionally register with service locator
      if (registerSingleton && !_getIt.isRegistered<T>()) {
        _getIt.registerSingleton<T>(bloc);
      }
      
      return bloc;
    } catch (e) {
      throw BlocCreationException('Failed to create Bloc<$T>: $e');
    }
  }

  /// Create a Cubit for simple state management
  static T createCubit<T extends Cubit>({
    required T Function() create,
    bool registerSingleton = false,
  }) {
    try {
      final cubit = create();
      
      // Optionally register with service locator
      if (registerSingleton && !_getIt.isRegistered<T>()) {
        _getIt.registerSingleton<T>(cubit);
      }
      
      return cubit;
    } catch (e) {
      throw BlocCreationException('Failed to create Cubit<$T>: $e');
    }
  }

  /// Get existing BLoC from service locator
  static T getBloc<T extends BlocBase>() {
    try {
      return _getIt.get<T>();
    } catch (e) {
      throw BlocRetrievalException('Failed to retrieve BLoC<$T>: $e');
    }
  }

  /// Check if BLoC is registered
  static bool isRegistered<T extends BlocBase>() {
    return _getIt.isRegistered<T>();
  }

  /// Dispose and unregister BLoC
  static Future<void> disposeBloc<T extends BlocBase>() async {
    if (_getIt.isRegistered<T>()) {
      final bloc = _getIt.get<T>();
      await bloc.close();
      await _getIt.unregister<T>();
    }
  }

  /// Clear all registered BLoCs (for testing or app reset)
  static Future<void> clearAll() async {
    await _getIt.reset();
  }
}

/// Exception for BLoC creation errors
class BlocCreationException implements Exception {
  final String message;
  const BlocCreationException(this.message);

  @override
  String toString() => 'BlocCreationException: $message';
}

/// Exception for BLoC retrieval errors
class BlocRetrievalException implements Exception {
  final String message;
  const BlocRetrievalException(this.message);

  @override
  String toString() => 'BlocRetrievalException: $message';
}
