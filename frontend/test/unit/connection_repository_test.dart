import 'package:aico_frontend/networking/clients/unified_api_client.dart';
import 'package:aico_frontend/networking/models/error_models.dart';
import 'package:aico_frontend/networking/services/token_manager.dart';
import 'package:flutter_test/flutter_test.dart';

// Dummy encryption service for testing
class DummyEncryptionService {
  Map<String, dynamic> createEncryptedRequest(Map<String, dynamic> data) => data;
  Map<String, dynamic> decryptPayload(String payload) => {};
  Future<void> initialize() async {}
  bool get isSessionActive => true;
  String? get clientId => 'dummy-client-id';
  Future<void> dispose() async {}
  String encryptPayload(Map<String, dynamic> payload) => '';
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

    setUp(() {
      apiClient = UnifiedApiClient(
        encryptionService: DummyEncryptionService() as dynamic,
        tokenManager: TokenManager(),
        baseUrl: 'https://api.test.com',
      );
    });

    test('makes successful GET request', () async {
      final response = await apiClient.get('/test');
      
      expect(response, isNotNull);
    });

    test('handles API errors correctly', () async {
      await expectLater(
        () => apiClient.get('/nonexistent'),
        throwsA(isA<Exception>()),
      );
    });

    test('handles network errors', () async {
      await expectLater(
        () => apiClient.get('/test'),
        throwsA(isA<Exception>()),
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
