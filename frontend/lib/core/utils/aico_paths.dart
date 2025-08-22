import 'dart:io';
import 'package:path_provider/path_provider.dart';
import 'package:yaml/yaml.dart';
import 'package:path/path.dart' as path;

/// Unified path resolver that reads from AICO's core.yaml configuration
/// Provides consistent cross-platform path resolution for frontend persistence
class AICOPaths {
  static Map<String, dynamic>? _config;
  static String? _baseDataDir;

  /// Initialize paths by reading core.yaml configuration
  static Future<void> initialize() async {
    if (_config != null) return; // Already initialized

    try {
      // Get platform-appropriate data directory
      final appDataDir = await getApplicationSupportDirectory();
      _baseDataDir = path.join(appDataDir.path, 'boeni-industries', 'aico');

      // Read core.yaml configuration
      final configFile = File(path.join(_baseDataDir!, 'config', 'defaults', 'core.yaml'));
      if (await configFile.exists()) {
        final yamlString = await configFile.readAsString();
        _config = loadYaml(yamlString) as Map<String, dynamic>;
      } else {
        // Fallback to default configuration
        _config = _getDefaultConfig();
      }
    } catch (e) {
      // Fallback to default configuration on any error
      _config = _getDefaultConfig();
    }
  }

  /// Get the base data directory
  static Future<String> getBaseDataDirectory() async {
    await initialize();
    return _baseDataDir ?? '';
  }

  /// Get frontend state persistence directory
  static Future<String> getStatePath() async {
    await initialize();
    final frontendSubdir = _config?['system']?['paths']?['frontend_subdirectory'] ?? 'frontend';
    return path.join(_baseDataDir!, frontendSubdir, 'state');
  }

  /// Get frontend cache directory
  static Future<String> getCachePath() async {
    await initialize();
    final cacheSubdir = _config?['system']?['paths']?['cache_subdirectory'] ?? 'cache';
    return path.join(_baseDataDir!, cacheSubdir, 'frontend');
  }

  /// Get frontend offline queue directory
  static Future<String> getOfflineQueuePath() async {
    await initialize();
    final frontendSubdir = _config?['system']?['paths']?['frontend_subdirectory'] ?? 'frontend';
    return path.join(_baseDataDir!, frontendSubdir, 'offline_queue');
  }

  /// Get logs directory
  static Future<String> getLogsPath() async {
    await initialize();
    final logsSubdir = _config?['system']?['paths']?['logs_subdirectory'] ?? 'logs';
    return path.join(_baseDataDir!, logsSubdir);
  }

  /// Ensure directory exists, create if needed
  static Future<Directory> ensureDirectory(String dirPath) async {
    final directory = Directory(dirPath);
    if (!await directory.exists()) {
      await directory.create(recursive: true);
    }
    return directory;
  }

  /// Default configuration fallback
  static Map<String, dynamic> _getDefaultConfig() {
    return {
      'system': {
        'paths': {
          'data_subdirectory': 'data',
          'config_subdirectory': 'config',
          'cache_subdirectory': 'cache',
          'logs_subdirectory': 'logs',
          'frontend_subdirectory': 'frontend',
        }
      }
    };
  }
}
