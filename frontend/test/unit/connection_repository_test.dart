import 'package:aico_frontend/core/services/unified_api_client.dart';
import 'package:aico_frontend/networking/models/error_models.dart';
import 'package:dio/dio.dart';
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

// Dummy encryption service for testing
class DummyEncryptionService {
  Future<void> initialize() async {}
  bool get isSessionActive => true;
  String? get clientId => 'dummy-client-id';
  Future<void> dispose() async {}
  String encryptPayload(Map<String, dynamic> payload) => '';
  Map<String, dynamic> createEncryptedRequest(Map<String, dynamic> payload) => {};
  Map<String, dynamic> decryptPayload(String encryptedPayload) => {};
  Future<Map<String, dynamic>> createHandshakeRequest() async => {};
  Future<void> processHandshakeResponse(Map<String, dynamic> response) async {}
  void resetSession() {}
  Future<void> clearAllKeys() async {}
  void disposeKeys() {}
  bool get isInitialized => true;
}

void main() {
  group('UnifiedApiClient', () {
    late UnifiedApiClient apiClient;
    late MockHttpClient mockHttpClient;
    late Dio dio;

    setUp(() {
      dio = Dio();
      mockHttpClient = MockHttpClient();
      apiClient = UnifiedApiClient(
        dio: dio,
        httpClient: mockHttpClient,
        encryptionService: DummyEncryptionService() as dynamic,
        baseUrl: 'https://api.test.com',
      );
    });

    test('makes successful GET request', () async {
      mockHttpClient = MockHttpClient(
        responseBody: '{"message": "success"}',
      );
      apiClient = UnifiedApiClient(
        dio: dio,
        httpClient: mockHttpClient,
        encryptionService: DummyEncryptionService() as dynamic,
        baseUrl: 'https://api.test.com',
      );

      final response = await apiClient.get('/test');
      
      expect(response.isSuccess, isTrue);
      expect(response.statusCode, 200);
    });

    test('handles API errors correctly', () async {
      mockHttpClient = MockHttpClient(
        statusCode: 404,
        responseBody: '{"error": "Not found"}',
      );
      apiClient = UnifiedApiClient(
        dio: dio,
        httpClient: mockHttpClient,
        encryptionService: DummyEncryptionService() as dynamic,
        baseUrl: 'https://api.test.com',
      );

      await expectLater(
        () => apiClient.get('/nonexistent'),
        throwsA(isA<NetworkException>()),
      );
    });

    test('handles network errors', () async {
      mockHttpClient = MockHttpClient(shouldThrow: true);
      apiClient = UnifiedApiClient(
        dio: dio,
        httpClient: mockHttpClient,
        encryptionService: DummyEncryptionService() as dynamic,
        baseUrl: 'https://api.test.com',
      );

      await expectLater(
        () => apiClient.get('/test'),
        throwsA(isA<NetworkException>()),
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
}
