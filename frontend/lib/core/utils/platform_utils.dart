import 'dart:io';
import 'package:flutter/foundation.dart';

/// Cross-platform utility class for handling platform-specific functionality
class PlatformUtils {
  /// Check if the current platform is a desktop platform
  static bool get isDesktop {
    if (kIsWeb) return false;
    return Platform.isWindows || Platform.isLinux || Platform.isMacOS;
  }

  /// Check if the current platform is a mobile platform
  static bool get isMobile {
    if (kIsWeb) return false;
    return Platform.isAndroid || Platform.isIOS;
  }

  /// Check if the current platform is web
  static bool get isWeb => kIsWeb;

  /// Get the current platform name as a string
  static String get platformName {
    if (kIsWeb) return 'Web';
    if (Platform.isWindows) return 'Windows';
    if (Platform.isMacOS) return 'macOS';
    if (Platform.isLinux) return 'Linux';
    if (Platform.isAndroid) return 'Android';
    if (Platform.isIOS) return 'iOS';
    return 'Unknown';
  }

  /// Check if the current platform supports window management
  static bool get supportsWindowManagement {
    return !kIsWeb && (Platform.isWindows || Platform.isLinux || Platform.isMacOS);
  }

  /// Check if the current platform supports system notifications
  static bool get supportsSystemNotifications {
    return !kIsWeb || (kIsWeb && kDebugMode);
  }

  /// Check if the current platform supports file system access
  static bool get supportsFileSystem {
    return !kIsWeb;
  }

  /// Get platform-specific error message for network issues
  static String getNetworkErrorMessage() {
    if (isWeb) {
      return 'Unable to connect to AICO. Please check your internet connection and try again.';
    } else if (isMobile) {
      return 'Unable to connect to AICO. Please check your network connection or try switching between WiFi and mobile data.';
    } else {
      return 'Unable to connect to AICO. Please check your network connection and firewall settings.';
    }
  }

  /// Get platform-specific error message for authentication issues
  static String getAuthErrorMessage() {
    if (isWeb) {
      return 'Authentication failed. Please clear your browser cache and try again.';
    } else {
      return 'Authentication failed. Please check your credentials and try again.';
    }
  }

  /// Check if the current platform supports biometric authentication
  static bool get supportsBiometrics {
    return !kIsWeb && (Platform.isAndroid || Platform.isIOS);
  }

  /// Check if the current platform supports secure storage
  static bool get supportsSecureStorage {
    return !kIsWeb;
  }

  /// Get platform-specific storage location description
  static String get storageLocationDescription {
    if (kIsWeb) {
      return 'browser local storage';
    } else if (Platform.isWindows) {
      return 'Windows credential manager';
    } else if (Platform.isMacOS) {
      return 'macOS keychain';
    } else if (Platform.isLinux) {
      return 'system keyring';
    } else if (Platform.isAndroid) {
      return 'Android keystore';
    } else if (Platform.isIOS) {
      return 'iOS keychain';
    } else {
      return 'secure storage';
    }
  }
}
