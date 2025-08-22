import 'package:dio/dio.dart';
import '../models/error_models.dart';
import '../services/token_manager.dart';

class AuthInterceptor extends Interceptor {
  final TokenManager _tokenManager;

  AuthInterceptor(this._tokenManager);

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) async {
    try {
      final token = await _tokenManager.getValidToken();
      if (token != null) {
        options.headers['Authorization'] = 'Bearer $token';
      }
      handler.next(options);
    } catch (e) {
      handler.reject(
        DioException(
          requestOptions: options,
          error: AuthException('Failed to attach authentication token: $e'),
        ),
      );
    }
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) async {
    if (err.response?.statusCode == 401) {
      try {
        // Token expired, attempt refresh
        if (await _tokenManager.refreshToken()) {
          // Retry original request with new token
          final newToken = await _tokenManager.getValidToken();
          if (newToken != null) {
            err.requestOptions.headers['Authorization'] = 'Bearer $newToken';
            
            final dio = Dio();
            final response = await dio.fetch(err.requestOptions);
            handler.resolve(response);
            return;
          }
        }
        
        // Refresh failed, clear tokens and propagate auth error
        await _tokenManager.clearTokens();
        handler.reject(
          DioException(
            requestOptions: err.requestOptions,
            response: err.response,
            error: const AuthException('Authentication failed - please log in again'),
          ),
        );
      } catch (e) {
        handler.reject(
          DioException(
            requestOptions: err.requestOptions,
            response: err.response,
            error: AuthException('Token refresh failed: $e'),
          ),
        );
      }
    } else {
      handler.next(err);
    }
  }
}
