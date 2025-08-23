import 'package:aico_frontend/core/services/api_client.dart';
import 'package:aico_frontend/networking/models/error_models.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;

// Mock HTTP client for testing
class MockHttpClient extends http.BaseClient {
  final bool shouldThrow;
  final int statusCode;
  final String responseBody;
  
  MockHttpClient({
    this.shouldThrow = false,
    this.statusCode = 200,
    this.responseBody = '{"status": "ok"}',
  });
  
  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    if (shouldThrow) {
      throw Exception('Network error');
    }
    
    return http.StreamedResponse(
      Stream.value(responseBody.codeUnits),
      statusCode,
      headers: {'content-type': 'application/json'},
    );
  }
}

void main() {
  group('ApiClient', () {
    late ApiClient apiClient;
    late MockHttpClient mockHttpClient;

    setUp(() {
      mockHttpClient = MockHttpClient();
      apiClient = ApiClient(
        httpClient: mockHttpClient,
        baseUrl: 'https://api.test.com',
      );
    });

    test('makes successful GET request', () async {
      mockHttpClient = MockHttpClient(
        responseBody: '{"message": "success"}',
      );
      apiClient = ApiClient(
        httpClient: mockHttpClient,
        baseUrl: 'https://api.test.com',
      );

      final response = await apiClient.get('/test');
      
      expect(response.isSuccess, isTrue);
      expect(response.statusCode, 200);
      expect(response.rawData, {'message': 'success'});
    });

    test('handles API errors correctly', () async {
      mockHttpClient = MockHttpClient(
        statusCode: 404,
        responseBody: '{"error": "Not found"}',
      );
      apiClient = ApiClient(
        httpClient: mockHttpClient,
        baseUrl: 'https://api.test.com',
      );

      await expectLater(
        () => apiClient.get('/nonexistent'),
        throwsA(isA<ApiException>()),
      );
    });

    test('handles network errors', () async {
      mockHttpClient = MockHttpClient(shouldThrow: true);
      apiClient = ApiClient(
        httpClient: mockHttpClient,
        baseUrl: 'https://api.test.com',
      );

      await expectLater(
        () => apiClient.get('/test'),
        throwsA(isA<ApiException>()),
      );
    });

    test('disposes without error', () {
      expect(() => apiClient.dispose(), returnsNormally);
    });
  });

  group('NetworkException hierarchy', () {
    test('ConnectionException is a NetworkException', () {
      const exception = ConnectionException('Connection failed');
      expect(exception, isA<NetworkException>());
      expect(exception.message, 'Connection failed');
    });

    test('ConnectionException toString works correctly', () {
      const exception = ConnectionException('Test connection error');
      expect(exception.toString(), contains('Test connection error'));
    });
  });

  group('ApiException', () {
    test('creates exception with message only', () {
      const exception = ApiException('Test error');
      expect(exception.message, 'Test error');
      expect(exception.statusCode, isNull);
      expect(exception.toString(), 'ApiException: Test error');
    });

    test('creates exception with status code', () {
      const exception = ApiException('Server error', statusCode: 500);
      expect(exception.message, 'Server error');
      expect(exception.statusCode, 500);
      expect(exception.toString(), 'ApiException(500): Server error');
    });

    test('correctly identifies error types', () {
      const networkError = ApiException('Network error');
      const clientError = ApiException('Client error', statusCode: 404);
      const serverError = ApiException('Server error', statusCode: 500);

      expect(networkError.isNetworkError, isTrue);
      expect(networkError.isClientError, isFalse);
      expect(networkError.isServerError, isFalse);

      expect(clientError.isNetworkError, isFalse);
      expect(clientError.isClientError, isTrue);
      expect(clientError.isServerError, isFalse);

      expect(serverError.isNetworkError, isFalse);
      expect(serverError.isClientError, isFalse);
      expect(serverError.isServerError, isTrue);
    });
  });

  group('ApiResponse', () {
    test('creates successful response', () {
      const response = ApiResponse<String>(
        data: 'test data',
        statusCode: 200,
        isSuccess: true,
        rawData: {'result': 'test data'},
      );
      
      expect(response.data, 'test data');
      expect(response.statusCode, 200);
      expect(response.isSuccess, isTrue);
      expect(response.rawData, {'result': 'test data'});
    });
  });
}
