import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Manages secure storage of user credentials for automatic re-authentication
class SecureCredentialManager {
  static const String _userUuidKey = 'aico_user_uuid';
  static const String _pinKey = 'aico_user_pin';
  
  static const FlutterSecureStorage _secureStorage = FlutterSecureStorage(
    aOptions: AndroidOptions(
      encryptedSharedPreferences: true,
    ),
    iOptions: IOSOptions(
      accessibility: KeychainAccessibility.first_unlock_this_device,
    ),
  );
  
  /// Store user credentials securely for automatic re-authentication
  Future<void> storeCredentials(String userUuid, String pin) async {
    await _secureStorage.write(key: _userUuidKey, value: userUuid);
    await _secureStorage.write(key: _pinKey, value: pin);
  }
  
  /// Retrieve stored user credentials
  /// Returns null if no credentials are stored
  Future<Map<String, String>?> getStoredCredentials() async {
    final userUuid = await _secureStorage.read(key: _userUuidKey);
    final pin = await _secureStorage.read(key: _pinKey);
    
    if (userUuid != null && pin != null) {
      return {'userUuid': userUuid, 'pin': pin};
    }
    return null;
  }
  
  /// Clear all stored credentials
  Future<void> clearCredentials() async {
    await _secureStorage.delete(key: _userUuidKey);
    await _secureStorage.delete(key: _pinKey);
  }
  
  /// Check if credentials are stored
  Future<bool> hasStoredCredentials() async {
    final credentials = await getStoredCredentials();
    return credentials != null;
  }
}
