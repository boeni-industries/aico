import 'package:aico_frontend/networking/repositories/user_repository.dart';
import 'package:aico_frontend/networking/services/token_manager.dart';
import 'package:dio/dio.dart';

/// Interceptor that automatically refreshes tokens when they expire
class TokenRefreshInterceptor extends Interceptor {
  final TokenManager _tokenManager;
  final ApiUserService _userService;
  final Dio _dio;

  TokenRefreshInterceptor({
    required TokenManager tokenManager,
    required ApiUserService userService,
    required Dio dio,
  })  : _tokenManager = tokenManager,
        _userService = userService,
        _dio = dio;

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) async {
    // Add valid token to request headers if available
    final token = await _tokenManager.getValidToken();
    if (token != null) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) async {
    // Check if error is due to token expiration (401 Unauthorized)
    if (err.response?.statusCode == 401) {
      try {
        // Attempt to refresh token using stored credentials
        final newToken = await _userService.refreshToken();
        
        if (newToken != null) {
          // Retry the original request with new token
          final requestOptions = err.requestOptions;
          requestOptions.headers['Authorization'] = 'Bearer $newToken';
          
          try {
            final response = await _dio.fetch(requestOptions);
            handler.resolve(response);
            return;
          } catch (e) {
            // If retry fails, clear credentials and let error propagate
            await _userService.clearStoredCredentials();
          }
        } else {
          // No stored credentials available, clear any existing data
          await _userService.clearStoredCredentials();
        }
      } catch (e) {
        // Token refresh failed, clear stored credentials
        await _userService.clearStoredCredentials();
      }
    }
    
    // Let the original error propagate
    handler.next(err);
  }
}
