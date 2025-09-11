import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:aico_frontend/core/logging/aico_log.dart';
import 'package:aico_frontend/networking/services/jwt_decoder.dart';

class TokenManager {
  // Singleton implementation
  static TokenManager? _instance;
  static TokenManager get instance => _instance ??= TokenManager._internal();
  
  factory TokenManager() => instance;
  
  TokenManager._internal();

  static const FlutterSecureStorage _storage = FlutterSecureStorage(
    aOptions: AndroidOptions(
      encryptedSharedPreferences: true,
    ),
    iOptions: IOSOptions(
      accessibility: KeychainAccessibility.first_unlock_this_device,
    ),
    lOptions: LinuxOptions(),
    mOptions: MacOsOptions(),
    wOptions: WindowsOptions(
      useBackwardCompatibility: false,
    ),
    webOptions: WebOptions(
      dbName: 'aico_secure_storage',
      publicKey: 'aico_public_key',
    ),
  );
  

  // Storage keys - aligned with AuthLocalDataSource
  static const String _keyAccessToken = 'auth_token';
  static const String _keyRefreshToken = 'aico_refresh_token';
  static const String _keyTokenExpiry = 'aico_token_expiry';

  String? _cachedToken;
  String? _cachedRefreshToken;
  DateTime? _tokenExpiry;
  Timer? _refreshTimer;
  
  // UnifiedApiClient for encrypted refresh requests
  dynamic _apiClient;

  /// Get access token (alias for getValidToken for compatibility)
  Future<String?> getAccessToken() async {
    return await getValidToken();
  }

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

    debugPrint('TokenManager: No valid token available');
    return null;
  }


  /// Set the API client for encrypted refresh requests
  void setApiClient(dynamic apiClient) {
    _apiClient = apiClient;
  }

  /// Refresh the access token using refresh token
  Future<bool> refreshToken() async {
    AICOLog.debug('Token refresh initiated', topic: 'network/token/refresh/debug');
    
    if (_cachedToken == null) {
      AICOLog.warn('No current token available for refresh', topic: 'network/token/refresh/no_token');
      return false;
    }

    try {
      if (_apiClient == null) {
        AICOLog.error('No API client available for token refresh', topic: 'network/token/refresh/no_client');
        return false;
      }
      
      AICOLog.info('Attempting token refresh via API client', topic: 'network/token/refresh/encrypted');
      
      // Use UnifiedApiClient with special refresh method that skips token freshness check
      final response = await _apiClient.postForTokenRefresh('/users/refresh');
      
      if (response != null && response['success'] == true && response['jwt_token'] != null) {
        final newToken = response['jwt_token'] as String;
        final newExpiry = JWTDecoder.getExpiryTime(newToken);
        
        _cachedToken = newToken;
        _tokenExpiry = newExpiry;
        await _storeTokensInStorage();
        
        AICOLog.info('Token refresh successful via encrypted client', 
          topic: 'network/token/refresh/success',
          extra: {'new_expiry': newExpiry?.toIso8601String()});
        
        return true;
      }
      
      AICOLog.error('Token refresh failed - invalid response from encrypted client', 
        topic: 'network/token/refresh/invalid_response');
      return false;
      
    } catch (e) {
      AICOLog.error('Token refresh failed', 
        topic: 'network/token/refresh/error',
        extra: {'error': e.toString()});
      return false;
    }
  }


  /// Check if current token is valid (not expired)
  bool _isTokenValid() {
    // If no expiry is stored, assume token is valid (for backward compatibility)
    if (_tokenExpiry == null) {
      return true;
    }
    
    return DateTime.now().isBefore(_tokenExpiry!.subtract(const Duration(minutes: 2)));
  }

  /// Check if token needs refresh (expires within 5 minutes)
  bool _shouldRefreshToken() {
    if (_tokenExpiry == null || _cachedToken == null) {
      return false;
    }
    
    // Refresh if token expires within 2 minutes
    return DateTime.now().isAfter(_tokenExpiry!.subtract(const Duration(minutes: 2)));
  }

  /// Proactively refresh token if it's close to expiring
  Future<void> ensureTokenFreshness() async {
    if (_shouldRefreshToken()) {
      AICOLog.info('Proactively refreshing token before expiry', topic: 'network/token/proactive_refresh');
      await refreshToken();
    }
  }


  /// Load tokens from secure storage
  Future<void> _loadTokensFromStorage() async {
    try {
      final accessToken = await _storage.read(key: _keyAccessToken);
      final refreshToken = await _storage.read(key: _keyRefreshToken);
      final expiryString = await _storage.read(key: _keyTokenExpiry);

      // Load tokens silently

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
        await _storage.write(key: _keyAccessToken, value: _cachedToken!);
      }
      
      if (_cachedRefreshToken != null && _cachedRefreshToken!.isNotEmpty) {
        await _storage.write(key: _keyRefreshToken, value: _cachedRefreshToken!);
      }
      
      if (_tokenExpiry != null) {
        await _storage.write(key: _keyTokenExpiry, value: _tokenExpiry!.toIso8601String());
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

  /// Start background token refresh monitoring
  void startBackgroundRefresh() {
    // Cancel existing timer if any
    _refreshTimer?.cancel();
    
    // Check and refresh token every 30 seconds for maximum reliability
    _refreshTimer = Timer.periodic(const Duration(seconds: 30), (timer) async {
      try {
        await ensureTokenFreshness();
      } catch (e) {
        AICOLog.error('Background token refresh failed', 
          topic: 'auth/token/background_refresh',
          extra: {'error': e.toString()});
      }
    });
    
    AICOLog.info('Background token refresh monitoring started', 
      topic: 'auth/token/background_refresh',
      extra: {'interval_seconds': 30});
  }

  /// Stop background token refresh monitoring
  void stopBackgroundRefresh() {
    _refreshTimer?.cancel();
    _refreshTimer = null;
    
    AICOLog.info('Background token refresh monitoring stopped', 
      topic: 'auth/token/background_refresh');
  }

  /// Clear all tokens from memory and secure storage
  Future<void> clearTokens() async {
    // Stop background refresh when clearing tokens
    stopBackgroundRefresh();
    
    _cachedToken = null;
    _cachedRefreshToken = null;
    _tokenExpiry = null;
    
    // Clear from secure storage
    try {
      await _storage.delete(key: _keyAccessToken);
      await _storage.delete(key: _keyRefreshToken);
      await _storage.delete(key: _keyTokenExpiry);
    } catch (e) {
      debugPrint('Failed to clear secure storage: $e');
    }
  }
  
}

