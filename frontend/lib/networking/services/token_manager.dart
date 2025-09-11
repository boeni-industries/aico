import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:aico_frontend/core/logging/aico_log.dart';
import 'package:dio/dio.dart';
import 'package:aico_frontend/networking/services/jwt_decoder.dart';

class TokenManager {
  // Singleton implementation
  static TokenManager? _instance;
  static TokenManager get instance => _instance ??= TokenManager._internal();
  
  factory TokenManager() => instance;
  
  TokenManager._internal();

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
  

  // Storage keys - aligned with AuthLocalDataSource
  static const String _keyAccessToken = 'auth_token';
  static const String _keyRefreshToken = 'aico_refresh_token';
  static const String _keyTokenExpiry = 'aico_token_expiry';

  String? _cachedToken;
  String? _cachedRefreshToken;
  DateTime? _tokenExpiry;
  Timer? _refreshTimer;

  /// Get access token (alias for getValidToken for compatibility)
  Future<String?> getAccessToken() async {
    return await getValidToken();
  }

  /// Get a valid token, refreshing if necessary
  Future<String?> getValidToken() async {
    debugPrint('TokenManager: getValidToken() called - cachedToken: ${_cachedToken != null ? "EXISTS" : "NULL"}');
    
    // Return cached token if still valid
    if (_cachedToken != null && _isTokenValid()) {
      debugPrint('TokenManager: Returning cached token');
      return _cachedToken;
    }

    // Try to load from secure storage
    await _loadTokensFromStorage();
    
    debugPrint('TokenManager: After loading from storage - cachedToken: ${_cachedToken != null ? "EXISTS" : "NULL"}');
    
    if (_cachedToken != null && _isTokenValid()) {
      debugPrint('TokenManager: Returning token from storage');
      return _cachedToken;
    }

    // Token expired or missing, try refresh
    if (_cachedRefreshToken != null) {
      debugPrint('TokenManager: Attempting token refresh');
      if (await refreshToken()) {
        return _cachedToken;
      }
    }

    debugPrint('TokenManager: No valid token available');
    return null;
  }


  /// Refresh the access token using refresh token
  Future<bool> refreshToken() async {
    debugPrint('🔄 TokenManager: refreshToken() called - Starting token refresh process');
    AICOLog.debug('Token refresh initiated', topic: 'network/token/refresh/debug');
    
    if (_cachedToken == null) {
      debugPrint('❌ TokenManager: No current token available for refresh');
      AICOLog.warn('No current token available for refresh', topic: 'network/token/refresh/no_token');
      return false;
    }

    try {
      debugPrint('🚀 TokenManager: Attempting token refresh with current token');
      AICOLog.info('Attempting token refresh', topic: 'network/token/refresh/start');
      
      // Create Dio instance for refresh request
      final dio = Dio();
      
      // Make refresh request to backend
      final response = await dio.post(
        'http://127.0.0.1:8771/api/v1/users/refresh',
        options: Options(
          headers: {
            'Authorization': 'Bearer $_cachedToken',
            'Content-Type': 'application/json',
          },
        ),
      );

      if (response.statusCode == 200 && response.data != null) {
        final data = response.data as Map<String, dynamic>;
        
        if (data['success'] == true && data['jwt_token'] != null) {
          final newToken = data['jwt_token'] as String;
          
          // Extract expiry from new token
          final newExpiry = JWTDecoder.getExpiryTime(newToken);
          
          debugPrint('✅ TokenManager: Token refresh successful! New expiry: ${newExpiry?.toIso8601String()}');
          
          // Update cached tokens
          _cachedToken = newToken;
          _tokenExpiry = newExpiry;
          
          // Store new token in secure storage
          await _storeTokensInStorage();
          
          debugPrint('💾 TokenManager: New token stored in secure storage');
          AICOLog.info('Token refresh successful', 
            topic: 'network/token/refresh/success',
            extra: {
              'new_expiry': newExpiry?.toIso8601String(),
            });
          
          return true;
        }
      }
      
      debugPrint('❌ TokenManager: Token refresh failed - invalid response. Status: ${response.statusCode}');
      AICOLog.error('Token refresh failed - invalid response', 
        topic: 'network/token/refresh/invalid_response',
        extra: {'status_code': response.statusCode});
      return false;
      
    } catch (e) {
      debugPrint('💥 TokenManager: Token refresh failed with error: $e');
      AICOLog.error('Token refresh failed', 
        topic: 'network/token/refresh/error',
        extra: {'error': e.toString()});
      return false;
    }
  }


  /// Check if current token is valid (not expired)
  bool _isTokenValid() {
    debugPrint('TokenManager: Validating token - cachedToken: ${_cachedToken != null ? "EXISTS" : "NULL"}, tokenExpiry: ${_tokenExpiry?.toString() ?? "NULL"}');
    
    // If no expiry is stored, assume token is valid (for backward compatibility)
    if (_tokenExpiry == null) {
      debugPrint('TokenManager: No expiry stored, assuming token is valid');
      return true;
    }
    
    final isValid = DateTime.now().isBefore(_tokenExpiry!.subtract(const Duration(minutes: 5)));
    debugPrint('TokenManager: Token expiry check result: $isValid');
    return isValid;
  }

  /// Check if token needs refresh (expires within 5 minutes)
  bool _shouldRefreshToken() {
    if (_tokenExpiry == null || _cachedToken == null) {
      return false;
    }
    
    // Refresh if token expires within 5 minutes
    final shouldRefresh = DateTime.now().isAfter(_tokenExpiry!.subtract(const Duration(minutes: 5)));
    debugPrint('TokenManager: Should refresh token: $shouldRefresh');
    return shouldRefresh;
  }

  /// Proactively refresh token if it's close to expiring
  Future<void> ensureTokenFreshness() async {
    debugPrint('🔍 TokenManager: ensureTokenFreshness() called - Checking if refresh needed');
    AICOLog.debug('Token freshness check initiated', topic: 'network/token/freshness_check');
    
    if (_shouldRefreshToken()) {
      debugPrint('⚠️ TokenManager: Token needs refresh - calling refreshToken()');
      AICOLog.info('Proactively refreshing token before expiry', topic: 'network/token/proactive_refresh');
      await refreshToken();
    } else {
      debugPrint('✅ TokenManager: Token is still fresh - no refresh needed');
      AICOLog.debug('Token is still fresh', topic: 'network/token/fresh');
    }
  }


  /// Load tokens from secure storage
  Future<void> _loadTokensFromStorage() async {
    try {
      final accessToken = await _secureStorage.read(key: _keyAccessToken);
      final refreshToken = await _secureStorage.read(key: _keyRefreshToken);
      final expiryString = await _secureStorage.read(key: _keyTokenExpiry);

      debugPrint('TokenManager: Loading from storage - accessToken: ${accessToken != null ? "FOUND (${accessToken.substring(0, 20)}...)" : "NOT FOUND"}, refreshToken: ${refreshToken != null ? "FOUND" : "NOT FOUND"}');

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

  /// Start background token refresh monitoring
  void startBackgroundRefresh() {
    debugPrint('🚀 TokenManager: Starting background token refresh monitoring');
    debugPrint('📊 TokenManager: Current state - cachedToken: ${_cachedToken != null ? "EXISTS" : "NULL"}, tokenExpiry: ${_tokenExpiry?.toIso8601String() ?? "NULL"}');
    
    // Cancel existing timer if any
    _refreshTimer?.cancel();
    
    // Check and refresh token every 5 minutes
    _refreshTimer = Timer.periodic(const Duration(minutes: 5), (timer) async {
      try {
        debugPrint('⏰ TokenManager: Background refresh timer triggered - checking token freshness');
        AICOLog.debug('Background refresh timer triggered', topic: 'auth/token/background_refresh/timer');
        await ensureTokenFreshness();
      } catch (e) {
        debugPrint('💥 TokenManager: Background refresh failed: $e');
        AICOLog.error('Background token refresh failed', 
          topic: 'auth/token/background_refresh',
          extra: {'error': e.toString()});
      }
    });
    
    AICOLog.info('Background token refresh monitoring started', 
      topic: 'auth/token/background_refresh',
      extra: {'interval_minutes': 5});
  }

  /// Stop background token refresh monitoring
  void stopBackgroundRefresh() {
    debugPrint('TokenManager: Stopping background token refresh monitoring');
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
      await _secureStorage.delete(key: _keyAccessToken);
      await _secureStorage.delete(key: _keyRefreshToken);
      await _secureStorage.delete(key: _keyTokenExpiry);
    } catch (e) {
      debugPrint('Failed to clear secure storage: $e');
    }
  }
  
}

