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
    await Future.wait([
      _secureStorage.write(key: _keyUserUuid, value: userUuid),
      _secureStorage.write(key: _keyPin, value: pin),
      _secureStorage.write(key: _keyToken, value: token),
      _sharedPreferences.setBool(_keyHasCredentials, true),
    ]);
  }

  @override
  Future<Map<String, String>?> getStoredCredentials() async {
    final hasCredentials = _sharedPreferences.getBool(_keyHasCredentials) ?? false;
    if (!hasCredentials) return null;

    final results = await Future.wait([
      _secureStorage.read(key: _keyUserUuid),
      _secureStorage.read(key: _keyPin),
      _secureStorage.read(key: _keyToken),
    ]);

    final userUuid = results[0];
    final pin = results[1];
    final token = results[2];

    if (userUuid != null && pin != null && token != null) {
      return {
        'userUuid': userUuid,
        'pin': pin,
        'token': token,
      };
    }

    return null;
  }

  @override
  Future<void> clearStoredCredentials() async {
    await Future.wait([
      _secureStorage.delete(key: _keyUserUuid),
      _secureStorage.delete(key: _keyPin),
      _secureStorage.delete(key: _keyToken),
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
  }

  @override
  Future<String?> getToken() async {
    return await _secureStorage.read(key: _keyToken);
  }

  @override
  Future<void> clearToken() async {
    await _secureStorage.delete(key: _keyToken);
  }
}
