import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';

// Core HTTP client provider
final dioProvider = Provider<Dio>((ref) {
  final dio = Dio();
  
  // Configure base options
  dio.options.baseUrl = 'http://localhost:8080/api'; // TODO: Use environment config
  dio.options.connectTimeout = const Duration(seconds: 30);
  dio.options.receiveTimeout = const Duration(seconds: 30);
  
  // Add interceptors for logging, auth, etc.
  dio.interceptors.add(LogInterceptor(
    requestBody: true,
    responseBody: true,
    logPrint: (obj) => debugPrint(obj.toString()),
  ));
  
  return dio;
});

// Secure storage provider
final secureStorageProvider = Provider<FlutterSecureStorage>((ref) {
  return const FlutterSecureStorage(
    aOptions: AndroidOptions(
      encryptedSharedPreferences: true,
    ),
    iOptions: IOSOptions(
      accessibility: KeychainAccessibility.first_unlock_this_device,
    ),
  );
});

// Shared preferences provider - will be overridden in main.dart
final sharedPreferencesProvider = Provider<SharedPreferences>((ref) {
  throw UnimplementedError('SharedPreferences must be overridden with actual instance in main.dart');
});

// Provider for initializing SharedPreferences
final sharedPreferencesInitProvider = FutureProvider<SharedPreferences>((ref) async {
  return await SharedPreferences.getInstance();
});
