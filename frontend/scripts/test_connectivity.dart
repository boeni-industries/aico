import 'package:aico_frontend/core/services/unified_api_client.dart';
import 'package:aico_frontend/core/services/encryption_service.dart';
import 'package:dio/dio.dart';
import 'package:http/http.dart' as http;

Future<void> main() async {
  final dio = Dio(BaseOptions(baseUrl: 'http://localhost:8771/api/v1/'));

  // Test UnifiedApiClient: /health and /echo
  final encryptionService = EncryptionService();
  final unifiedClient = UnifiedApiClient(
    dio: dio,
    httpClient: http.Client(),
    encryptionService: encryptionService,
    baseUrl: 'http://localhost:8771/api/v1/',
  );

  try {
    final health = await unifiedClient.get('/health', fromJson: (json) => json['status']);
    print('UNIFIED /health: SUCCESS: $health');
  } catch (e) {
    print('UNIFIED /health: ERROR: $e');
  }

  try {
    await unifiedClient.initializeEncryption();
    final echo = await unifiedClient.post('/echo', {'message': 'hello'}, fromJson: (json) => json['message']);
    print('UNIFIED /echo: SUCCESS: $echo');
  } catch (e) {
    print('UNIFIED /echo: ERROR: $e');
  }
}
