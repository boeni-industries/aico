import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class TokenManager {
  static const FlutterSecureStorage _secureStorage = FlutterSecureStorage(
    aOptions: AndroidOptions(
      encryptedSharedPreferences: true,
    ),
    iOptions: IOSOptions(
      accessibility: KeychainAccessibility.first_unlock_this_device,
    ),
    lOptions: LinuxOptions(),
    wOptions: WindowsOptions(
      useBackwardCompatibility: false,
    ),
    webOptions: WebOptions(
      dbName: 'aico_secure_storage',
      publicKey: 'aico_public_key',
    ),
  );
  

  // Storage keys
  static const String _keyAccessToken = 'aico_access_token';
  static const String _keyRefreshToken = 'aico_refresh_token';
  static const String _keyTokenExpiry = 'aico_token_expiry';

  String? _cachedToken;
  String? _cachedRefreshToken;
  DateTime? _tokenExpiry;

  /// Get a valid token, refreshing if necessary
  Future<String?> getValidToken() async {
    // Return cached token if still valid
    if (_cachedToken != null && _isTokenValid()) {
      return _cachedToken;
    }

    // Try to load from secure storage
    await _loadTokensFromStorage();
    
    if (_cachedToken != null && _isTokenValid()) {
      return _cachedToken;
    }

    // Token expired or missing, try refresh
    if (_cachedRefreshToken != null) {
      if (await refreshToken()) {
        return _cachedToken;
      }
    }

    return null;
  }


  /// Refresh the access token using refresh token
  Future<bool> refreshToken() async {
    if (_cachedRefreshToken == null) {
      return false;
    }

    try {
      // TODO: Implement actual refresh API call
      // For now, simulate refresh logic
      await Future.delayed(const Duration(milliseconds: 100));
      
      // In real implementation, make API call to refresh endpoint
      // and update tokens based on response
      
      return false; // Placeholder - implement when refresh endpoint is available
    } catch (e) {
      debugPrint('Token refresh failed: $e');
      return false;
    }
  }


  /// Check if current token is valid (not expired)
  bool _isTokenValid() {
    if (_tokenExpiry == null) return false;
    return DateTime.now().isBefore(_tokenExpiry!.subtract(const Duration(minutes: 5)));
  }


  /// Load tokens from secure storage
  Future<void> _loadTokensFromStorage() async {
    try {
      final accessToken = await _secureStorage.read(key: _keyAccessToken);
      final refreshToken = await _secureStorage.read(key: _keyRefreshToken);
      final expiryString = await _secureStorage.read(key: _keyTokenExpiry);

      if (accessToken != null && accessToken.isNotEmpty) {
        _cachedToken = accessToken;
        _cachedRefreshToken = refreshToken;
        
        if (expiryString != null && expiryString.isNotEmpty) {
          try {
            _tokenExpiry = DateTime.parse(expiryString);
          } catch (e) {
            debugPrint('Invalid token expiry format: $expiryString');
            _tokenExpiry = null;
          }
        }
      }
    } catch (e) {
      debugPrint('Failed to load tokens from storage: $e');
      // Clear potentially corrupted tokens
      _cachedToken = null;
      _cachedRefreshToken = null;
      _tokenExpiry = null;
    }
  }

  /// Store tokens in secure storage
  Future<void> _storeTokensInStorage() async {
    try {
      if (_cachedToken != null && _cachedToken!.isNotEmpty) {
        await _secureStorage.write(key: _keyAccessToken, value: _cachedToken!);
      }
      
      if (_cachedRefreshToken != null && _cachedRefreshToken!.isNotEmpty) {
        await _secureStorage.write(key: _keyRefreshToken, value: _cachedRefreshToken!);
      }
      
      if (_tokenExpiry != null) {
        await _secureStorage.write(key: _keyTokenExpiry, value: _tokenExpiry!.toIso8601String());
      }
    } catch (e) {
      debugPrint('Failed to store tokens: $e');
      rethrow;
    }
  }


  /// Enhanced storeTokens method with secure storage
  Future<void> storeTokens({
    required String accessToken,
    String? refreshToken,
    required DateTime expiresAt,
  }) async {
    _cachedToken = accessToken;
    _cachedRefreshToken = refreshToken;
    _tokenExpiry = expiresAt;
    
    // Store in secure storage
    await _storeTokensInStorage();
  }

  /// Clear all tokens from memory and secure storage
  Future<void> clearTokens() async {
    _cachedToken = null;
    _cachedRefreshToken = null;
    _tokenExpiry = null;
    
    // Clear from secure storage
    try {
      await _secureStorage.delete(key: _keyAccessToken);
      await _secureStorage.delete(key: _keyRefreshToken);
      await _secureStorage.delete(key: _keyTokenExpiry);
    } catch (e) {
      debugPrint('Failed to clear secure storage: $e');
    }
  }
  
}

