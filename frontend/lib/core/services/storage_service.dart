import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';

/// Service for persistent local storage operations
class StorageService {
  SharedPreferences? _prefs;
  bool _isInitialized = false;

  /// Initialize the storage service
  Future<void> initialize() async {
    _prefs = await SharedPreferences.getInstance();
    _isInitialized = true;
  }

  /// Check if service is initialized
  bool get isInitialized => _isInitialized;

  /// Store a string value
  Future<bool> setString(String key, String value) async {
    _ensureInitialized();
    return await _prefs!.setString(key, value);
  }

  /// Retrieve a string value
  String? getString(String key) {
    _ensureInitialized();
    return _prefs!.getString(key);
  }

  /// Store an integer value
  Future<bool> setInt(String key, int value) async {
    _ensureInitialized();
    return await _prefs!.setInt(key, value);
  }

  /// Retrieve an integer value
  int? getInt(String key) {
    _ensureInitialized();
    return _prefs!.getInt(key);
  }

  /// Store a boolean value
  Future<bool> setBool(String key, bool value) async {
    _ensureInitialized();
    return await _prefs!.setBool(key, value);
  }

  /// Retrieve a boolean value
  bool? getBool(String key) {
    _ensureInitialized();
    return _prefs!.getBool(key);
  }

  /// Store a double value
  Future<bool> setDouble(String key, double value) async {
    _ensureInitialized();
    return await _prefs!.setDouble(key, value);
  }

  /// Retrieve a double value
  double? getDouble(String key) {
    _ensureInitialized();
    return _prefs!.getDouble(key);
  }

  /// Store a list of strings
  Future<bool> setStringList(String key, List<String> value) async {
    _ensureInitialized();
    return await _prefs!.setStringList(key, value);
  }

  /// Retrieve a list of strings
  List<String>? getStringList(String key) {
    _ensureInitialized();
    return _prefs!.getStringList(key);
  }

  /// Store a JSON object
  Future<bool> setJson(String key, Map<String, dynamic> value) async {
    _ensureInitialized();
    final jsonString = json.encode(value);
    return await _prefs!.setString(key, jsonString);
  }

  /// Retrieve a JSON object
  Map<String, dynamic>? getJson(String key) {
    _ensureInitialized();
    final jsonString = _prefs!.getString(key);
    if (jsonString == null) return null;
    
    try {
      return json.decode(jsonString) as Map<String, dynamic>;
    } catch (e) {
      return null;
    }
  }

  /// Remove a key
  Future<bool> remove(String key) async {
    _ensureInitialized();
    return await _prefs!.remove(key);
  }

  /// Clear all stored data
  Future<bool> clear() async {
    _ensureInitialized();
    return await _prefs!.clear();
  }

  /// Check if a key exists
  bool containsKey(String key) {
    _ensureInitialized();
    return _prefs!.containsKey(key);
  }

  /// Get all keys
  Set<String> getKeys() {
    _ensureInitialized();
    return _prefs!.getKeys();
  }

  void _ensureInitialized() {
    if (!_isInitialized) {
      throw StateError('StorageService not initialized. Call initialize() first.');
    }
  }

  /// Dispose of resources
  Future<void> dispose() async {
    // SharedPreferences doesn't need explicit disposal
    _isInitialized = false;
  }
}
