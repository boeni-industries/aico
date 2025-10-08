import 'dart:io';

import 'package:aico_frontend/core/services/encryption_service.dart';
import 'package:aico_frontend/networking/clients/unified_api_client.dart';
import 'package:aico_frontend/networking/clients/websocket_client.dart';
import 'package:aico_frontend/networking/services/connection_manager.dart';
import 'package:aico_frontend/networking/services/token_manager.dart';
import 'package:flutter/foundation.dart';

/// Test script to verify Flutter logging integration with encryption
/// This simulates the logs that would be sent by the Flutter app
void main() async {
  debugPrint('🧪 Testing Flutter logging integration...');
  
  // Initialize encryption service
  final encryptionService = EncryptionService();
  await encryptionService.initialize();
  
  // Create token manager and connection manager
  final tokenManager = TokenManager();
  final webSocketClient = WebSocketClient(
    encryptionService: encryptionService,
    tokenManager: tokenManager,
  );
  final connectionManager = ConnectionManager(webSocketClient, encryptionService);
  
  // Create API client with proper dependencies
  final apiClient = UnifiedApiClient(
    encryptionService: encryptionService,
    tokenManager: tokenManager,
    connectionManager: connectionManager,
  );
  
  try {
    // Initialize API client
    debugPrint('🔐 Initializing API client...');
    await apiClient.initialize();
    debugPrint('✅ Encryption session established');
  } catch (e) {
    debugPrint('❌ Failed to establish encryption: $e');
    return;
  }
  
  // Test 1: App startup log
  await testLog(apiClient, {
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
  await testLog(apiClient, {
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
  await testLog(apiClient, {
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
  await testLog(apiClient, {
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
  await testLog(apiClient, {
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
  await testLog(apiClient, {
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
  
  debugPrint('\n✅ All Flutter logging tests completed!');
  debugPrint('📋 Check logs with: aico logs tail');
  debugPrint('🔍 Filter frontend logs with: aico logs tail --subsystem frontend');
  
  // Clean up
  apiClient.dispose();
  encryptionService.dispose();
}

Future<void> testLog(UnifiedApiClient apiClient, Map<String, dynamic> logData, String testName) async {
  try {
    debugPrint('\n🧪 Testing: $testName');
    
    final response = await apiClient.post('/logs/batch', data: logData);
    
    debugPrint('✅ $testName: SUCCESS');
    if (response?.containsKey('success') == true && response!['success'] == true) {
      debugPrint('✅ Batch: ${response!['message']}');
    }
  } catch (e) {
    debugPrint('❌ $testName: ERROR - $e');
  }
  
  // Small delay between tests
  await Future.delayed(Duration(milliseconds: 100));
}
