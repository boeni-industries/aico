import 'package:flutter/foundation.dart';

class TokenManager {
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

  /// Store access and refresh tokens with expiry
  Future<void> storeTokens({
    required String accessToken,
    String? refreshToken,
    required DateTime expiresAt,
  }) async {
    _cachedToken = accessToken;
    _cachedRefreshToken = refreshToken;
    _tokenExpiry = expiresAt;
  }

  /// Alias for storeTokens for backward compatibility
  Future<void> saveToken({
    required String token,
    required DateTime expiresAt,
  }) async {
    await storeTokens(
      accessToken: token,
      expiresAt: expiresAt,
    );
  }

  /// Clear all stored tokens
  Future<void> clearTokens() async {
    _cachedToken = null;
    _cachedRefreshToken = null;
    _tokenExpiry = null;
  }

  /// Check if current token is valid (not expired)
  bool _isTokenValid() {
    if (_tokenExpiry == null) return false;
    return DateTime.now().isBefore(_tokenExpiry!.subtract(const Duration(minutes: 5)));
  }

  /// Load tokens from secure storage
  Future<void> _loadTokensFromStorage() async {
    try {
      // Placeholder - tokens only persist in memory for now
      _cachedToken = null;
      _cachedRefreshToken = null;
      _tokenExpiry = null;
    } catch (e) {
      debugPrint('Failed to load tokens from storage: $e');
    }
  }
}
