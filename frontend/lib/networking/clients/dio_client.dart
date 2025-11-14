import 'package:aico_frontend/networking/interceptors/token_refresh_interceptor.dart';
import 'package:aico_frontend/networking/services/token_manager.dart';
import 'package:aico_frontend/networking/services/user_service.dart';
import 'package:dio/dio.dart';

/// Factory class for creating configured Dio instances
class DioClient {
  static Dio createDio({
    required String baseUrl,
    TokenManager? tokenManager,
    ApiUserService? userService,
  }) {
    final dio = Dio(BaseOptions(
      baseUrl: baseUrl,
      connectTimeout: const Duration(seconds: 30),
      receiveTimeout: const Duration(seconds: 30),
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    ));

    // Add logging interceptor in debug mode
    dio.interceptors.add(LogInterceptor(
      requestBody: true,
      responseBody: true,
      requestHeader: true,
      responseHeader: false,
      error: true,
    ));

    // Add token refresh interceptor if dependencies are provided
    if (tokenManager != null && userService != null) {
      dio.interceptors.add(TokenRefreshInterceptor(
        tokenManager: tokenManager,
        userService: userService,
        dio: dio,
      ));
    }

    return dio;
  }
}
