import 'package:aico_frontend/core/services/encryption_service.dart';
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

Future<void> main() async {
  final dio = Dio(BaseOptions(baseUrl: 'http://localhost:8771/api/v1/'));
  String? jwtToken;

  debugPrint('🚀 AICO Flutter Connectivity Test');
  debugPrint('==================================================');

  // Test basic health endpoint
  try {
    final healthResponse = await dio.get('/health');
    debugPrint('✅ Backend health check: ${healthResponse.data['status']}');
  } catch (e) {
    debugPrint('❌ Backend health check failed: $e');
    return;
  }

  // Initialize encryption service
  final encryptionService = EncryptionService();
  await encryptionService.initialize();
  
  try {
    debugPrint('\n🤝 Starting encrypted handshake...');
    
    // Perform handshake
    final handshakeData = await encryptionService.createHandshakeRequest();
    final handshakeResponse = await dio.post('/handshake', data: {
      'handshake_request': handshakeData['handshake_request']
    });
    
    await encryptionService.processHandshakeResponse(handshakeResponse.data);
    debugPrint('✅ Encryption session established');
    
    // Authenticate with test user credentials
    debugPrint('\n🔐 Authenticating with backend...');
    
    final authPayload = {
      'user_uuid': '4837b1ac-f59a-400a-a875-6a4ea994c936',
      'pin': '1234'
    };
    
    final encryptedAuthPayload = encryptionService.encryptPayload(authPayload);
    final authRequest = {
      'encrypted': true,
      'payload': encryptedAuthPayload,
      'client_id': encryptionService.clientId,
    };
    
    final authResponse = await dio.post('/users/authenticate', data: authRequest);
    
    if (authResponse.data['success'] == true) {
      jwtToken = authResponse.data['jwt_token'];
      debugPrint('✅ Authentication successful - JWT token received');
    } else {
      debugPrint('❌ Authentication failed: ${authResponse.data['error']}');
      return;
    }
    
    // Test encrypted echo with JWT authentication
    debugPrint('\n📡 Testing encrypted echo with authentication...');
    final echoPayload = {'message': 'hello from Flutter!', 'test_data': {'key': 'value'}};
    final encryptedPayload = encryptionService.encryptPayload(echoPayload);
    
    final encryptedRequest = {
      'encrypted': true,
      'payload': encryptedPayload,
      'client_id': encryptionService.clientId,
    };
    
    final echoResponse = await dio.post(
      '/echo',
      data: encryptedRequest,
      options: Options(headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $jwtToken',
      }),
    );
    
    debugPrint('✅ Encrypted echo with auth successful');
    debugPrint('Echo response: ${echoResponse.data}');
    
    debugPrint('\n==================================================');
    debugPrint('🎉 Flutter Connectivity Test COMPLETED SUCCESSFULLY!');
    debugPrint('\n✅ All tests passed:');
    debugPrint('  • Backend connectivity');
    debugPrint('  • Encrypted handshake protocol');
    debugPrint('  • JWT authentication flow');
    debugPrint('  • End-to-end encrypted communication with auth');
    debugPrint('\n🔐 Flutter-backend encryption with JWT auth is working correctly!');
    
  } catch (e) {
    debugPrint('❌ Test failed: $e');
  }
}
