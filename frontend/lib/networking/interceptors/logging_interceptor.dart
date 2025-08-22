import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

class LoggingInterceptor extends Interceptor {
  final bool logRequests;
  final bool logResponses;
  final bool logErrors;
  final bool logHeaders;
  final bool logBody;

  LoggingInterceptor({
    this.logRequests = true,
    this.logResponses = true,
    this.logErrors = true,
    this.logHeaders = false,
    this.logBody = kDebugMode,
  });

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    if (logRequests) {
      debugPrint('🚀 ${options.method} ${options.uri}');
      
      if (logHeaders && options.headers.isNotEmpty) {
        debugPrint('📋 Headers: ${options.headers}');
      }
      
      if (logBody && options.data != null) {
        debugPrint('📦 Body: ${options.data}');
      }
    }
    
    handler.next(options);
  }

  @override
  void onResponse(Response response, ResponseInterceptorHandler handler) {
    if (logResponses) {
      debugPrint('✅ ${response.statusCode} ${response.requestOptions.method} ${response.requestOptions.uri}');
      
      if (logHeaders && response.headers.map.isNotEmpty) {
        debugPrint('📋 Response Headers: ${response.headers.map}');
      }
      
      if (logBody && response.data != null) {
        debugPrint('📦 Response Body: ${response.data}');
      }
    }
    
    handler.next(response);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    if (logErrors) {
      debugPrint('❌ ${err.response?.statusCode ?? 'NO_STATUS'} ${err.requestOptions.method} ${err.requestOptions.uri}');
      debugPrint('🔥 Error: ${err.message}');
      
      if (err.response?.data != null) {
        debugPrint('📦 Error Body: ${err.response?.data}');
      }
    }
    
    handler.next(err);
  }
}
