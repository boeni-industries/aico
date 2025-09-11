import 'package:aico_frontend/core/providers/token_manager.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Flutter Secure Storage provider
final flutterSecureStorageProvider = Provider<FlutterSecureStorage>((ref) {
  return const FlutterSecureStorage();
});

/// SharedPreferences provider
final sharedPreferencesProvider = FutureProvider<SharedPreferences>((ref) async {
  return await SharedPreferences.getInstance();
});

/// Encryption service provider
final encryptionServiceProvider = Provider<EncryptionService>((ref) {
  final secureStorage = ref.watch(flutterSecureStorageProvider);
  return EncryptionService(secureStorage);
});

/// Token manager provider  
final tokenManagerProvider = Provider<TokenManager>((ref) {
  final secureStorage = ref.watch(flutterSecureStorageProvider);
  return TokenManager(secureStorage);
});

/// Storage service provider
final storageServiceProvider = FutureProvider<StorageService>((ref) async {
  final secureStorage = ref.watch(flutterSecureStorageProvider);
  final sharedPrefs = await ref.watch(sharedPreferencesProvider.future);
  return StorageService(secureStorage, sharedPrefs);
});

/// Simple encryption service implementation
class EncryptionService {
  final FlutterSecureStorage _secureStorage;
  
  EncryptionService(this._secureStorage);
  
  // TODO: Implement proper encryption when needed
  String encrypt(String data) => data;
  String decrypt(String data) => data;
  
  Future<String?> getSecureString(String key) async {
    return await _secureStorage.read(key: key);
  }
  
  Future<void> setSecureString(String key, String value) async {
    await _secureStorage.write(key: key, value: value);
  }
  
  Future<void> deleteSecureString(String key) async {
    await _secureStorage.delete(key: key);
  }
  
  Future<String?> getToken() async {
    return await _secureStorage.read(key: 'auth_token');
  }
  
  Future<void> setToken(String token) async {
    await _secureStorage.write(key: 'auth_token', value: token);
  }
  
  Future<void> clearToken() async {
    await _secureStorage.delete(key: 'auth_token');
  }
}

/// Storage service for managing local data
class StorageService {
  final FlutterSecureStorage _secureStorage;
  final SharedPreferences _sharedPreferences;
  
  StorageService(this._secureStorage, this._sharedPreferences);
  
  // Secure storage methods
  Future<String?> getSecureValue(String key) async {
    return await _secureStorage.read(key: key);
  }
  
  Future<void> setSecureValue(String key, String value) async {
    await _secureStorage.write(key: key, value: value);
  }
  
  Future<void> deleteSecureValue(String key) async {
    await _secureStorage.delete(key: key);
  }
  
  // Shared preferences methods
  String? getStringValue(String key) {
    return _sharedPreferences.getString(key);
  }
  
  Future<bool> setStringValue(String key, String value) async {
    return await _sharedPreferences.setString(key, value);
  }
  
  Future<bool> setBoolValue(String key, bool value) async {
    return await _sharedPreferences.setBool(key, value);
  }
  
  bool? getBoolValue(String key) {
    return _sharedPreferences.getBool(key);
  }
  
  int? getIntValue(String key) {
    return _sharedPreferences.getInt(key);
  }
  
  Future<bool> setIntValue(String key, int value) async {
    return await _sharedPreferences.setInt(key, value);
  }
  
  Future<bool> removeValue(String key) async {
    return await _sharedPreferences.remove(key);
  }
  
  Future<void> setJson(String key, Map<String, dynamic> value) async {
    final jsonString = value.toString();
    await setStringValue(key, jsonString);
  }
}
