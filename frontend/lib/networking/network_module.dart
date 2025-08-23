import 'package:aico_frontend/networking/clients/api_client.dart';
import 'package:aico_frontend/networking/clients/dio_client.dart';
import 'package:aico_frontend/networking/clients/websocket_client.dart';
import 'package:aico_frontend/networking/interceptors/token_refresh_interceptor.dart';
import 'package:aico_frontend/networking/repositories/admin_repository.dart';
import 'package:aico_frontend/networking/repositories/health_repository.dart';
import 'package:aico_frontend/networking/repositories/user_repository.dart';
import 'package:aico_frontend/networking/services/connection_manager.dart';
import 'package:aico_frontend/networking/services/offline_queue.dart';
import 'package:aico_frontend/networking/services/token_manager.dart';
import 'package:dio/dio.dart';
import 'package:get_it/get_it.dart';

class NetworkModule {
  static void registerDependencies() {
    final getIt = GetIt.instance;

    // Core networking services
    getIt.registerLazySingleton<TokenManager>(() => TokenManager());
    getIt.registerLazySingleton<OfflineQueue>(() => OfflineQueue());
    
    // Basic HTTP client without token refresh (to avoid circular dependency)
    getIt.registerLazySingleton<Dio>(() {
      return DioClient.createDio(
        baseUrl: "http://localhost:8771/api/v1",
      );
    });

    // API clients
    getIt.registerLazySingleton<AicoApiClient>(
      () => AicoApiClient(getIt<Dio>()),
    );
    
    getIt.registerLazySingleton<WebSocketClient>(() => WebSocketClient());
    
    getIt.registerLazySingleton<ConnectionManager>(
      () => ConnectionManager(
        getIt<WebSocketClient>(),
      ),
    );

    // Repositories
    getIt.registerLazySingleton<UserRepository>(
      () => ApiUserRepository(
        apiClient: getIt<AicoApiClient>(),
        tokenManager: getIt<TokenManager>(),
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
    
    // Add token refresh interceptor after all dependencies are available
    _configureTokenRefreshInterceptor();
  }

  static void _configureTokenRefreshInterceptor() {
    final getIt = GetIt.instance;
    final dio = getIt<Dio>();
    final tokenManager = getIt<TokenManager>();
    final userRepository = getIt<UserRepository>() as ApiUserRepository;
    
    // Add token refresh interceptor
    dio.interceptors.add(TokenRefreshInterceptor(
      tokenManager: tokenManager,
      userRepository: userRepository,
      dio: dio,
    ));
  }

  static void dispose() {
    final getIt = GetIt.instance;
    
    // Dispose resources
    getIt<OfflineQueue>().dispose();
    getIt<ConnectionManager>().dispose();
  }
}
