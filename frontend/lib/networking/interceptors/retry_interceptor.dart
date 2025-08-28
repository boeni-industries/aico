import 'package:aico_frontend/networking/models/error_models.dart';
import 'package:dio/dio.dart';

class RetryInterceptor extends Interceptor {
  final int maxRetries;
  final Duration baseDelay;
  final List<int> retryStatusCodes;

  RetryInterceptor({
    this.maxRetries = 3,
    this.baseDelay = const Duration(seconds: 1),
    this.retryStatusCodes = const [408, 429, 500, 502, 503, 504],
  });

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) async {
    final extra = err.requestOptions.extra;
    final retryCount = extra['retry_count'] ?? 0;

    if (_shouldRetry(err, retryCount)) {
      final delay = _calculateDelay(retryCount);
      await Future.delayed(delay);

      // Update retry count
      err.requestOptions.extra['retry_count'] = retryCount + 1;

      try {
        final dio = Dio();
        final response = await dio.fetch(err.requestOptions);
        handler.resolve(response);
        return;
      } catch (e) {
        // If retry fails, continue with original error handling
      }
    }

    // Convert to appropriate exception type
    final networkException = _convertToNetworkException(err);
    handler.reject(
      DioException(
        requestOptions: err.requestOptions,
        response: err.response,
        error: networkException,
      ),
    );
  }

  bool _shouldRetry(DioException err, int retryCount) {
    if (retryCount >= maxRetries) return false;

    // Retry on network errors
    if (err.type == DioExceptionType.connectionTimeout ||
        err.type == DioExceptionType.receiveTimeout ||
        err.type == DioExceptionType.sendTimeout ||
        err.type == DioExceptionType.connectionError) {
      return true;
    }

    // Retry on specific HTTP status codes
    if (err.response?.statusCode != null) {
      return retryStatusCodes.contains(err.response!.statusCode);
    }

    return false;
  }

  Duration _calculateDelay(int retryCount) {
    // Exponential backoff with jitter
    final exponentialDelay = baseDelay * (2 << retryCount);
    final jitter = Duration(
      milliseconds: (exponentialDelay.inMilliseconds * 0.1).round(),
    );
    return exponentialDelay + jitter;
  }

  NetworkException _convertToNetworkException(DioException err) {
    switch (err.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.receiveTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.connectionError:
        return ConnectionException(
          'Network connection failed: ${err.message}',
          originalError: err,
        );

      case DioExceptionType.badResponse:
        final statusCode = err.response?.statusCode ?? 0;
        if (statusCode >= 400 && statusCode < 500) {
          if (statusCode == 401 || statusCode == 403) {
            return AuthException(
              'Authentication failed',
              statusCode: statusCode,
              originalError: err,
            );
          }
          return HttpException(
            'Client error: ${err.message}',
            statusCode,
            originalError: err,
          );
        } else if (statusCode >= 500) {
          return ServerException(
            'Server error: ${err.message}',
            statusCode: statusCode,
            originalError: err,
          );
        }
        return HttpException(
          'HTTP error: ${err.message}',
          statusCode,
          originalError: err,
        );

      case DioExceptionType.cancel:
        return ConnectionException(
          'Request was cancelled'
        ); 
      case DioExceptionType.unknown:
      default:
        return ConnectionException(
          'Unknown network error: ${err.message}',
          originalError: err,
        );
    }
  }
}
