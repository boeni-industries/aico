import 'package:aico_frontend/networking/services/jwt_decoder.dart';
import 'package:aico_frontend/networking/services/token_manager.dart';
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
  Future<void> storeRefreshToken(String refreshToken);
  Future<String?> getRefreshToken();
  Future<void> clearRefreshToken();
}

class AuthLocalDataSourceImpl implements AuthLocalDataSource {
  final FlutterSecureStorage _secureStorage;
  final SharedPreferences _sharedPreferences;

  static const String _keyUserUuid = 'user_uuid';
  static const String _keyPin = 'user_pin';
  static const String _keyToken = 'auth_token';
  static const String _keyRefreshToken = 'refresh_token';
  static const String _keyHasCredentials = 'has_stored_credentials';

  AuthLocalDataSourceImpl(this._secureStorage, this._sharedPreferences);

  @override
  Future<void> storeCredentials(String userUuid, String pin, String token) async {
    // Clear any existing stale credentials first
    await Future.wait([
      _secureStorage.delete(key: _keyUserUuid),
      _secureStorage.delete(key: _keyPin),
      _secureStorage.delete(key: _keyToken),
    ]);
    
    // Store credentials
    await _secureStorage.write(key: _keyUserUuid, value: userUuid);
    await _secureStorage.write(key: _keyPin, value: pin);
    await _secureStorage.write(key: _keyToken, value: token);
    await _sharedPreferences.setBool(_keyHasCredentials, true);
  }

  @override
  Future<Map<String, String>?> getStoredCredentials() async {
    final results = await Future.wait([
      _secureStorage.read(key: _keyUserUuid),
      _secureStorage.read(key: _keyPin),
      _secureStorage.read(key: _keyToken),
    ]);
    
    final userUuid = results[0];
    final pin = results[1];
    final token = results[2];
    
    // Check if we have essential credentials (userUuid and pin)
    if (userUuid != null && pin != null) {
      final credentials = {
        'userUuid': userUuid,
        'pin': pin,
      };
      
      // Add token if available and valid
      if (token != null) {
        try {
          final expiryTime = JWTDecoder.getExpiryTime(token);
          final now = DateTime.now();
          
          if (expiryTime != null && expiryTime.isAfter(now.add(const Duration(minutes: 5)))) {
            // Token is valid for at least 5 more minutes
            credentials['token'] = token;
          }
        } catch (e) {
          // Token parsing failed - will need re-authentication
        }
      }
      
      return credentials;
    }
    
    return null;
  }

  @override
  Future<void> clearStoredCredentials() async {
    await Future.wait([
      _secureStorage.delete(key: _keyUserUuid),
      _secureStorage.delete(key: _keyPin),
      _secureStorage.delete(key: _keyToken),
      _secureStorage.delete(key: _keyRefreshToken),
      _secureStorage.delete(key: 'aico_access_token'),
      _secureStorage.delete(key: 'aico_refresh_token'),
      _secureStorage.delete(key: 'aico_token_expiry'),
      _sharedPreferences.setBool(_keyHasCredentials, false),
    ]);
  }

  @override
  Future<bool> hasStoredCredentials() async {
    return _sharedPreferences.getBool(_keyHasCredentials) ?? false;
  }

  @override
  Future<void> storeToken(String token) async {
    await _secureStorage.write(key: _keyToken, value: token);
    
    // Store token in TokenManager format for compatibility
    try {
      await _secureStorage.write(key: 'aico_access_token', value: token);
      
      final expiryTime = JWTDecoder.getExpiryTime(token);
      if (expiryTime != null) {
        await _secureStorage.write(key: 'aico_token_expiry', value: expiryTime.toIso8601String());
      }
    } catch (e) {
      // Token expiry extraction failed - not critical
    }
    
    // Start background token refresh monitoring after storing new token
    TokenManager().startBackgroundRefresh();
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

  @override
  Future<void> storeRefreshToken(String refreshToken) async {
    await _secureStorage.write(key: _keyRefreshToken, value: refreshToken);
    await _secureStorage.write(key: 'aico_refresh_token', value: refreshToken);
  }

  @override
  Future<String?> getRefreshToken() async {
    return await _secureStorage.read(key: _keyRefreshToken);
  }

  @override
  Future<void> clearRefreshToken() async {
    await Future.wait([
      _secureStorage.delete(key: _keyRefreshToken),
      _secureStorage.delete(key: 'aico_refresh_token'),
    ]);
  }
}
