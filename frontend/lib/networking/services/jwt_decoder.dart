import 'package:dart_jsonwebtoken/dart_jsonwebtoken.dart';

/// JWT token decoder utility for extracting claims and expiry information
class JWTDecoder {
  /// Decode JWT token and extract expiry time
  /// Returns null if token is invalid or doesn't contain exp claim
  static DateTime? getExpiryTime(String token) {
    try {
      // Decode without verification (we only need to read claims)
      final jwt = JWT.decode(token);
      
      // Extract exp claim (Unix timestamp)
      final exp = jwt.payload['exp'];
      if (exp == null) return null;
      
      // Convert Unix timestamp to DateTime
      return DateTime.fromMillisecondsSinceEpoch(exp * 1000, isUtc: true);
    } catch (e) {
      // Invalid token format
      return null;
    }
  }
  
  /// Check if token is expired
  static bool isExpired(String token) {
    final expiryTime = getExpiryTime(token);
    if (expiryTime == null) return true;
    
    return DateTime.now().toUtc().isAfter(expiryTime);
  }
  
  /// Get all claims from JWT token
  /// Returns null if token is invalid
  static Map<String, dynamic>? getClaims(String token) {
    try {
      final jwt = JWT.decode(token);
      return jwt.payload;
    } catch (e) {
      return null;
    }
  }
  
  /// Extract user UUID from token
  static String? getUserUuid(String token) {
    final claims = getClaims(token);
    return claims?['user_uuid'] ?? claims?['sub'];
  }
  
  /// Extract username from token
  static String? getUsername(String token) {
    final claims = getClaims(token);
    return claims?['username'];
  }
  
  /// Extract roles from token
  static List<String> getRoles(String token) {
    final claims = getClaims(token);
    final roles = claims?['roles'];
    if (roles is List) {
      return roles.cast<String>();
    }
    return [];
  }
}
