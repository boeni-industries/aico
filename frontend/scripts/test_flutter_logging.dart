import 'dart:io';
import 'package:dio/dio.dart';



/// Simple test script to verify Flutter logging integration
/// This simulates the logs that would be sent by the Flutter app
void main() async {
  final dio = Dio();
  final baseUrl = 'http://localhost:8771/api/v1';
  
  print('🧪 Testing Flutter logging integration...');
  
  // Test 1: App startup log
  await testLog(dio, baseUrl, {
    'timestamp': DateTime.now().toIso8601String(),
    'level': 'INFO',
    'module': 'testmodule',
    'function': 'testfunction',
    'topic': 'startup',
    'message': 'AICO Flutter application starting',
    'environment': 'development',
    'origin': 'frontend',
    'extra': {
      'platform': Platform.operatingSystem,
      'version': Platform.operatingSystemVersion,
      'is_debug': true,
    }
  }, 'App Startup');
  
  // Test 2: App initialization log
  await testLog(dio, baseUrl, {
    'timestamp': DateTime.now().toIso8601String(),
    'level': 'INFO',
    'module': 'testmodule',
    'function': 'initState',
    'topic': 'initialization',
    'message': 'App widget initialized',
    'environment': 'development',
    'origin': 'frontend',
    'extra': {
      'theme_mode': 'ThemeMode.system',
    }
  }, 'App Initialization');
  
  // Test 3: Authentication attempt log
  await testLog(dio, baseUrl, {
    'timestamp': DateTime.now().toIso8601String(),
    'level': 'INFO',
    'module': 'mobile.auth',
    'function': '_onLoginRequested',
    'topic': 'login_attempt',
    'message': 'User login attempt started',
    'environment': 'development',
    'origin': 'frontend',
    'extra': {
      'user_uuid': 'test_user_123',
      'remember_me': true,
    }
  }, 'Authentication Attempt');
  
  // Test 4: Authentication success log
  await testLog(dio, baseUrl, {
    'timestamp': DateTime.now().toIso8601String(),
    'level': 'INFO',
    'module': 'mobile.auth',
    'function': '_onLoginRequested',
    'topic': 'login_success',
    'message': 'User authentication successful',
    'environment': 'development',
    'origin': 'frontend',
    'extra': {
      'user_uuid': 'test_user_123',
      'user_name': 'Test User',
      'nickname': 'tester',
      'remember_me': true,
      'token_expiry': DateTime.now().add(Duration(days: 30)).toIso8601String(),
    }
  }, 'Authentication Success');
  
  // Test 5: Auto-login attempt log
  await testLog(dio, baseUrl, {
    'timestamp': DateTime.now().toIso8601String(),
    'level': 'INFO',
    'module': 'mobile.auth',
    'function': '_onAutoLoginRequested',
    'topic': 'auto_login_attempt',
    'message': 'Attempting automatic login with stored credentials',
    'environment': 'development',
    'origin': 'frontend',
    'extra': {}
  }, 'Auto-login Attempt');
  
  // Test 6: Logout log
  await testLog(dio, baseUrl, {
    'timestamp': DateTime.now().toIso8601String(),
    'level': 'INFO',
    'module': 'mobile.auth',
    'function': '_onLogoutRequested',
    'topic': 'logout_attempt',
    'message': 'User logout requested',
    'environment': 'development',
    'origin': 'frontend',
    'extra': {}
  }, 'User Logout');
  
  print('\n✅ All Flutter logging tests completed!');
  print('📋 Check logs with: aico logs tail');
  print('🔍 Filter frontend logs with: aico logs tail --subsystem frontend');
}

Future<void> testLog(Dio dio, String baseUrl, Map<String, dynamic> logData, String testName) async {
  try {
    print('\n🧪 Testing: $testName');
    
    final response = await dio.post(
      '$baseUrl/logs/',
      data: logData,
      options: Options(
        headers: {'Content-Type': 'application/json'},
        followRedirects: true,
        validateStatus: (status) => status! < 400,
      ),
    );
    
    if (response.statusCode == 200) {
      print('✅ $testName: SUCCESS (${response.statusCode})');
    } else {
      print('❌ $testName: FAILED (${response.statusCode})');
    }
  } catch (e) {
    print('❌ $testName: ERROR - $e');
    if (e is DioException && e.response != null) {
      print('   Response body: ${e.response?.data}');
    }
  }
  
  // Small delay between tests
  await Future.delayed(Duration(milliseconds: 100));
}
