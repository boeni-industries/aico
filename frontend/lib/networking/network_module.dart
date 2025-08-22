import 'package:dio/dio.dart';
import 'package:get_it/get_it.dart';
import 'clients/api_client.dart';
import 'clients/websocket_client.dart';
import 'interceptors/auth_interceptor.dart';
import 'interceptors/retry_interceptor.dart';
import 'interceptors/logging_interceptor.dart';
import 'services/token_manager.dart';
import 'services/connection_manager.dart';
import 'services/offline_queue.dart';
import 'repositories/user_repository.dart';
import 'repositories/admin_repository.dart';
import 'repositories/health_repository.dart';

class NetworkModule {
  static void registerDependencies() {
    final getIt = GetIt.instance;

    // Core networking services
    getIt.registerLazySingleton<TokenManager>(() => TokenManager());
    getIt.registerLazySingleton<OfflineQueue>(() => OfflineQueue());
    
    // HTTP client with interceptors
    getIt.registerLazySingleton<Dio>(() {
      final dio = Dio();
      
      // Add interceptors in order
      dio.interceptors.add(LoggingInterceptor());
      dio.interceptors.add(AuthInterceptor(getIt<TokenManager>()));
      dio.interceptors.add(RetryInterceptor());
      
      // Configure default options
      dio.options.connectTimeout = const Duration(seconds: 10);
      dio.options.receiveTimeout = const Duration(seconds: 30);
      dio.options.sendTimeout = const Duration(seconds: 30);
      
      return dio;
    });

    // API clients
    getIt.registerLazySingleton<AicoApiClient>(
      () => AicoApiClient(getIt<Dio>()),
    );
    
    getIt.registerLazySingleton<WebSocketClient>(() => WebSocketClient());
    
    getIt.registerLazySingleton<ConnectionManager>(
      () => ConnectionManager(
        getIt<AicoApiClient>(),
        getIt<WebSocketClient>(),
      ),
    );

    // Repositories
    getIt.registerLazySingleton<UserRepository>(
      () => ApiUserRepository(
        getIt<AicoApiClient>(),
        getIt<OfflineQueue>(),
      ),
    );
    
    getIt.registerLazySingleton<AdminRepository>(
      () => ApiAdminRepository(getIt<AicoApiClient>()),
    );
    
    getIt.registerLazySingleton<HealthRepository>(
      () => ApiHealthRepository(getIt<AicoApiClient>()),
    );
  }

  static Future<void> initialize() async {
    final getIt = GetIt.instance;
    
    // Initialize offline queue
    await getIt<OfflineQueue>().initialize();
    
    // Initialize connection manager
    await getIt<ConnectionManager>().initialize();
  }

  static void dispose() {
    final getIt = GetIt.instance;
    
    // Dispose resources
    getIt<OfflineQueue>().dispose();
    getIt<ConnectionManager>().dispose();
  }
}
