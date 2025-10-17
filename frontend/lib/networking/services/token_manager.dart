import 'dart:async';

import 'package:aico_frontend/core/logging/aico_log.dart';
import 'package:aico_frontend/networking/services/jwt_decoder.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

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
  
  // Re-authentication completion tracking
  Completer<bool>? _reAuthCompleter;

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

    // If re-authentication is in progress, wait for it to complete
    if (_reAuthCompleter != null && !_reAuthCompleter!.isCompleted) {
      AICOLog.info('Waiting for re-authentication to complete',
        topic: 'auth/token/waiting_for_reauth');
      
      try {
        // Wait up to 20 seconds for re-auth to complete
        final success = await _reAuthCompleter!.future.timeout(
          const Duration(seconds: 20),
          onTimeout: () {
            AICOLog.warn('Re-authentication timeout',
              topic: 'auth/token/reauth_timeout');
            return false;
          },
        );
        
        if (success && _cachedToken != null && _isTokenValid()) {
          AICOLog.info('Re-authentication completed successfully',
            topic: 'auth/token/reauth_success');
          return _cachedToken;
        }
      } catch (e) {
        AICOLog.error('Error waiting for re-authentication',
          topic: 'auth/token/reauth_wait_error',
          error: e);
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
  /// This method is designed to be non-blocking and fail-fast
  Future<bool> refreshToken() async {
    try {
      // If no refresh token available, trigger automatic re-authentication
      if (_cachedRefreshToken == null) {
        await _loadTokensFromStorage();
        if (_cachedRefreshToken == null) {
          AICOLog.warn('No refresh token available, triggering automatic re-authentication',
            topic: 'auth/token/auto_reauth_required');
          _triggerAutoReAuthentication();
          return false;
        }
      }
      
      // Use refresh token to get new access token
      final response = await _apiClient.postForTokenRefresh('/auth/refresh', {
        'refresh_token': _cachedRefreshToken,
      });
      
      if (response != null && response['success'] == true) {
        _cachedToken = response['access_token'];
        _tokenExpiry = JWTDecoder.getExpiryTime(_cachedToken!);
        
        // Update refresh token if provided
        if (response['refresh_token'] != null) {
          _cachedRefreshToken = response['refresh_token'];
        }
        
        await _storeTokensInStorage();
        _scheduleProactiveRefresh();
        return true;
      } else {
        AICOLog.warn('Token refresh failed - invalid response, triggering re-authentication',
          topic: 'auth/token/refresh_failed',
          extra: {'response': response});
        _triggerAutoReAuthentication();
      }
    } catch (e) {
      // Check if this is a backend unavailable error
      if (e.toString().contains('connection refused') || 
          e.toString().contains('SocketException') ||
          e.toString().contains('timeout')) {
        AICOLog.warn('Token refresh failed - backend unavailable, will retry later', 
          topic: 'auth/token/refresh_backend_unavailable',
          extra: {'error': e.toString()});
        // Schedule retry for network errors
        _scheduleRefreshRetry();
        return false;
      }
      
      // Check for authentication errors (refresh token expired/invalid)
      if (e.toString().contains('401') || e.toString().contains('403')) {
        AICOLog.warn('Refresh token expired/invalid, triggering re-authentication', 
          topic: 'auth/token/refresh_token_expired',
          extra: {'error': e.toString()});
        _triggerAutoReAuthentication();
        return false;
      }
      
      AICOLog.error('Token refresh failed with exception, triggering re-authentication', 
        topic: 'auth/token/refresh_error',
        extra: {'error': e.toString()});
      
      _triggerAutoReAuthentication();
    }
    return false;
  }
  
  /// Schedule proactive token refresh before expiry
  void _scheduleProactiveRefresh() {
    _refreshTimer?.cancel();
    
    if (_tokenExpiry != null) {
      final now = DateTime.now();
      final timeUntilExpiry = _tokenExpiry!.difference(now);
      
      // Refresh when 10 minutes remain or at 80% of token lifetime, whichever is sooner
      final refreshBuffer = Duration(minutes: 10);
      final eightyPercentLifetime = Duration(milliseconds: (timeUntilExpiry.inMilliseconds * 0.8).round());
      final refreshIn = timeUntilExpiry.compareTo(refreshBuffer) > 0 
          ? (eightyPercentLifetime.compareTo(refreshBuffer) < 0 ? eightyPercentLifetime : refreshBuffer)
          : Duration(seconds: 30); // If very close to expiry, refresh soon
      
      debugPrint('TokenManager: Scheduling proactive refresh in ${refreshIn.inMinutes} minutes');
      
      _refreshTimer = Timer(refreshIn, () {
        debugPrint('TokenManager: Proactive token refresh triggered');
        refreshToken();
      });
    }
  }
  
  /// Schedule retry for failed refresh attempts
  void _scheduleRefreshRetry() {
    _refreshTimer?.cancel();
    
    debugPrint('TokenManager: Scheduling refresh retry in 2 minutes');
    _refreshTimer = Timer(const Duration(minutes: 2), () {
      debugPrint('TokenManager: Retrying token refresh after network error');
      refreshToken();
    });
  }
  
  // Re-authentication stream for UI integration
  final StreamController<ReAuthenticationRequired> _reAuthController = StreamController<ReAuthenticationRequired>.broadcast();
  
  /// Stream for re-authentication events
  Stream<ReAuthenticationRequired> get reAuthenticationStream => _reAuthController.stream;
  
  /// Trigger automatic re-authentication flow
  /// Emits event for UI layer - follows message-driven architecture
  void _triggerAutoReAuthentication() {
    // Don't clear tokens immediately - let AuthProvider handle it
    // This prevents infinite loops where cleared tokens trigger more refresh attempts
    
    // Create completer if not already in progress
    if (_reAuthCompleter == null || _reAuthCompleter!.isCompleted) {
      _reAuthCompleter = Completer<bool>();
    }
    
    AICOLog.info('Token refresh failed - triggering re-authentication',
      topic: 'auth/token/reauth_required');
    
    // Simple event emission - let existing AuthProvider handle the logic
    _reAuthController.add(ReAuthenticationRequired(
      reason: 'Token refresh failed',
      timestamp: DateTime.now(),
    ));
  }
  
  /// Notify that re-authentication completed (called by AuthProvider)
  void notifyReAuthenticationComplete(bool success) {
    if (_reAuthCompleter != null && !_reAuthCompleter!.isCompleted) {
      _reAuthCompleter!.complete(success);
      AICOLog.info('Re-authentication completion notified',
        topic: 'auth/token/reauth_notified',
        extra: {'success': success});
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

  /// Check if token is expired
  bool _isTokenExpired() {
    if (_tokenExpiry == null) {
      return false;
    }
    return DateTime.now().isAfter(_tokenExpiry!);
  }

  /// Ensure token freshness - refresh if expired or expiring soon
  Future<bool> ensureTokenFreshness() async {
    // If no token, cannot ensure freshness - but don't trigger refresh loops
    if (_cachedToken == null) {
      return false;
    }

    // If token is expired, attempt refresh
    if (_isTokenExpired()) {
      AICOLog.info('Token expired, attempting refresh',
        topic: 'auth/token/expired_refresh');
      return await refreshToken();
    }

    // Proactively refresh if token expires within 5 minutes
    if (_tokenExpiry != null) {
      final timeUntilExpiry = _tokenExpiry!.difference(DateTime.now());
      if (timeUntilExpiry.inMinutes <= 5) {
        AICOLog.info('Token expiring soon, proactive refresh',
          topic: 'auth/token/proactive_refresh',
          extra: {'minutes_until_expiry': timeUntilExpiry.inMinutes});
        return await refreshToken();
      }
    }

    return true;
  }


  /// Load tokens from secure storage
  Future<void> _loadTokensFromStorage() async {
    try {
      final accessToken = await _storage.read(key: _keyAccessToken);
      final refreshToken = await _storage.read(key: _keyRefreshToken);
      final expiryString = await _storage.read(key: _keyTokenExpiry);

      // Load tokens silently

      if (accessToken != null && accessToken.isNotEmpty) {
        // Validate token format before storing
        if (_isValidJWTFormat(accessToken)) {
          _cachedToken = accessToken;
          _cachedRefreshToken = refreshToken;
          
          // Try to extract expiry from JWT token directly
          _tokenExpiry = JWTDecoder.getExpiryTime(accessToken);
          
          // Fallback to stored expiry string if JWT parsing fails
          if (_tokenExpiry == null && expiryString != null && expiryString.isNotEmpty) {
            try {
              _tokenExpiry = DateTime.parse(expiryString);
            } catch (e) {
              debugPrint('Invalid token expiry format: $expiryString');
            }
          }
        } else {
          debugPrint('Invalid JWT token format, clearing stored tokens');
          await clearTokens();
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
    if (_cachedToken != null) {
      await _storage.write(key: _keyAccessToken, value: _cachedToken!);
      if (_tokenExpiry != null) {
        await _storage.write(
          key: _keyTokenExpiry, 
          value: _tokenExpiry!.millisecondsSinceEpoch.toString()
        );
      }
      
      AICOLog.debug('Tokens stored in secure storage',
        topic: 'auth/token/storage_success',
        extra: {
          'has_token': _cachedToken != null,
          'has_expiry': _tokenExpiry != null,
          'expiry': _tokenExpiry?.toIso8601String()
        });
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
    _refreshTimer?.cancel();
    _refreshTimer = Timer.periodic(const Duration(seconds: 30), (timer) async {
      if (_cachedToken != null) {
        // Check if token needs refresh (expired or expiring soon)
        if (_isTokenExpired()) {
          AICOLog.info('Background refresh: token expired',
            topic: 'auth/token/background_expired');
          await refreshToken();
        } else if (_tokenExpiry != null) {
          final timeUntilExpiry = _tokenExpiry!.difference(DateTime.now());
          if (timeUntilExpiry.inMinutes <= 10) {
            AICOLog.info('Background refresh: token expiring soon',
              topic: 'auth/token/background_expiring',
              extra: {'minutes_until_expiry': timeUntilExpiry.inMinutes});
            await refreshToken();
          }
        }
      } else {
        AICOLog.debug('Background refresh: no token to refresh',
          topic: 'auth/token/background_no_token');
      }
    });
  }

  /// Stop background token refresh monitoring
  void stopBackgroundRefresh() {
    _refreshTimer?.cancel();
    _refreshTimer = null;
    
    AICOLog.info('Background token refresh monitoring stopped', 
      topic: 'auth/token/background_refresh');
  }

  /// Validate JWT token format
  bool _isValidJWTFormat(String token) {
    // Basic JWT format check: should have 3 parts separated by dots
    final parts = token.split('.');
    if (parts.length != 3) return false;
    
    // Each part should be base64 encoded (basic check)
    for (final part in parts) {
      if (part.isEmpty) return false;
    }
    
    return true;
  }

  /// Clear all tokens from memory and storage
  Future<void> clearTokens() async {
    // Stop background refresh when clearing tokens
    stopBackgroundRefresh();
    
    _cachedToken = null;
    _cachedRefreshToken = null;
    _tokenExpiry = null;
    
    try {
      await _storage.delete(key: _keyAccessToken);
      await _storage.delete(key: _keyRefreshToken);
      await _storage.delete(key: _keyTokenExpiry);
    } catch (e) {
      debugPrint('Failed to clear secure storage: $e');
    }
  }
  
  /// Dispose resources
  void dispose() {
    _refreshTimer?.cancel();
    _reAuthController.close();
  }
}

/// Re-authentication required event
class ReAuthenticationRequired {
  final String reason;
  final DateTime timestamp;
  
  const ReAuthenticationRequired({
    required this.reason,
    required this.timestamp,
  });
}

