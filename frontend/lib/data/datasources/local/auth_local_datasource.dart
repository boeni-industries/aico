import 'package:aico_frontend/networking/services/jwt_decoder.dart';
import 'package:aico_frontend/networking/services/token_manager.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';

abstract class AuthLocalDataSource {
  Future<void> storeCredentials(String userUuid, String pin, String token);
  Future<Map<String, String>?> getStoredCredentials();
  Future<void> clearStoredCredentials();
  Future<bool> hasStoredCredentials();
  Future<void> storeToken(String token);
  Future<String?> getToken();
  Future<void> clearToken();
}

class AuthLocalDataSourceImpl implements AuthLocalDataSource {
  final FlutterSecureStorage _secureStorage;
  final SharedPreferences _sharedPreferences;

  static const String _keyUserUuid = 'user_uuid';
  static const String _keyPin = 'user_pin';
  static const String _keyToken = 'auth_token';
  static const String _keyHasCredentials = 'has_stored_credentials';

  AuthLocalDataSourceImpl(this._secureStorage, this._sharedPreferences);

  @override
  Future<void> storeCredentials(String userUuid, String pin, String token) async {
    debugPrint('AuthLocalDataSource: Storing credentials - userUuid: $userUuid, pin: ${pin.isNotEmpty ? "PROVIDED" : "EMPTY"}, token: ${token.isNotEmpty ? "PROVIDED" : "EMPTY"}');
    
    // Clear any existing stale credentials first
    debugPrint('AuthLocalDataSource: Clearing any existing stale credentials...');
    await Future.wait([
      _secureStorage.delete(key: _keyUserUuid),
      _secureStorage.delete(key: _keyPin),
      _secureStorage.delete(key: _keyToken),
    ]);
    
    // Store each credential individually to debug which ones fail
    try {
      await _secureStorage.write(key: _keyUserUuid, value: userUuid);
      debugPrint('AuthLocalDataSource: UserUuid stored successfully');
    } catch (e) {
      debugPrint('AuthLocalDataSource: Failed to store userUuid: $e');
    }
    
    try {
      await _secureStorage.write(key: _keyPin, value: pin);
      debugPrint('AuthLocalDataSource: PIN stored successfully');
    } catch (e) {
      debugPrint('AuthLocalDataSource: Failed to store PIN: $e');
    }
    
    try {
      await _secureStorage.write(key: _keyToken, value: token);
      debugPrint('AuthLocalDataSource: Token stored successfully');
    } catch (e) {
      debugPrint('AuthLocalDataSource: Failed to store token: $e');
    }
    
    try {
      await _sharedPreferences.setBool(_keyHasCredentials, true);
      debugPrint('AuthLocalDataSource: HasCredentials flag set successfully');
    } catch (e) {
      debugPrint('AuthLocalDataSource: Failed to set hasCredentials flag: $e');
    }
    
    debugPrint('AuthLocalDataSource: Credential storage process completed');
  }

  @override
  Future<Map<String, String>?> getStoredCredentials() async {
    debugPrint('AuthLocalDataSource: Getting stored credentials...');
    
    final results = await Future.wait([
      _secureStorage.read(key: _keyUserUuid),
      _secureStorage.read(key: _keyPin),
      _secureStorage.read(key: _keyToken),
    ]);
    
    final userUuid = results[0];
    final pin = results[1];
    final token = results[2];
    
    debugPrint('AuthLocalDataSource: Retrieved - userUuid: ${userUuid != null ? "EXISTS" : "NULL"}, pin: ${pin != null ? "EXISTS" : "NULL"}, token: ${token != null ? "EXISTS" : "NULL"}');
    
    if (userUuid != null && pin != null && token != null) {
      debugPrint('AuthLocalDataSource: All credentials found, returning credential map');
      return {
        'userUuid': userUuid,
        'pin': pin,
        'token': token,
      };
    }
    
    debugPrint('AuthLocalDataSource: Missing credentials, returning null');
    return null;
  }

  @override
  Future<void> clearStoredCredentials() async {
    await Future.wait([
      _secureStorage.delete(key: _keyUserUuid),
      _secureStorage.delete(key: _keyPin),
      _secureStorage.delete(key: _keyToken),
      _secureStorage.delete(key: 'aico_access_token'),
      _secureStorage.delete(key: 'aico_token_expiry'),
      _sharedPreferences.setBool(_keyHasCredentials, false),
    ]);
  }

  @override
  Future<bool> hasStoredCredentials() async {
    final hasCredentials = _sharedPreferences.getBool(_keyHasCredentials) ?? false;
    debugPrint('AuthLocalDataSource: Has stored credentials check: $hasCredentials');
    return hasCredentials;
  }

  @override
  Future<void> storeToken(String token) async {
    debugPrint('AuthLocalDataSource: Storing token with key: $_keyToken, token: ${token.substring(0, 20)}...');
    await _secureStorage.write(key: _keyToken, value: token);
    
    // Store token in TokenManager format for compatibility
    try {
      await _secureStorage.write(key: 'aico_access_token', value: token);
      debugPrint('AuthLocalDataSource: Stored token in TokenManager format');
      
      final expiryTime = JWTDecoder.getExpiryTime(token);
      if (expiryTime != null) {
        await _secureStorage.write(key: 'aico_token_expiry', value: expiryTime.toIso8601String());
        debugPrint('AuthLocalDataSource: Stored token expiry: ${expiryTime.toIso8601String()}');
      }
    } catch (e) {
      debugPrint('AuthLocalDataSource: Failed to extract/store token expiry: $e');
    }
    
    // Start background token refresh monitoring after storing new token
    TokenManager().startBackgroundRefresh();
    debugPrint('AuthLocalDataSource: Started background token refresh monitoring');
  }

  @override
  Future<String?> getToken() async {
    return await _secureStorage.read(key: _keyToken);
  }

  @override
  Future<void> clearToken() async {
    await Future.wait([
      _secureStorage.delete(key: _keyToken),
      _secureStorage.delete(key: 'aico_access_token'),
      _secureStorage.delete(key: 'aico_token_expiry'),
    ]);
  }
}
