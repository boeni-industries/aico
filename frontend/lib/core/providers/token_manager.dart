import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Token manager for handling authentication tokens
class TokenManager {
  final FlutterSecureStorage _secureStorage;
  
  TokenManager(this._secureStorage);
  
  static const String _tokenKey = 'auth_token';
  static const String _refreshTokenKey = 'refresh_token';
  
  Future<String?> getToken() async {
    return await _secureStorage.read(key: _tokenKey);
  }
  
  Future<void> setToken(String token) async {
    await _secureStorage.write(key: _tokenKey, value: token);
  }
  
  Future<String?> getRefreshToken() async {
    return await _secureStorage.read(key: _refreshTokenKey);
  }
  
  Future<void> setRefreshToken(String refreshToken) async {
    await _secureStorage.write(key: _refreshTokenKey, value: refreshToken);
  }
  
  Future<void> clearTokens() async {
    await Future.wait([
      _secureStorage.delete(key: _tokenKey),
      _secureStorage.delete(key: _refreshTokenKey),
    ]);
  }
  
  Future<bool> hasValidToken() async {
    final token = await getToken();
    return token != null && token.isNotEmpty;
  }
}
