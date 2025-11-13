import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:crypto/crypto.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:sodium/sodium.dart';
import 'package:sodium_libs/sodium_libs.dart' as sodium_libs;

class LocalKeyManager {
  static const _masterKeyStorageKey = 'aico_master_key_v1';

  static const _secureStorage = FlutterSecureStorage(
    aOptions: AndroidOptions(
      encryptedSharedPreferences: true,
    ),
    iOptions: IOSOptions(
      accessibility: KeychainAccessibility.first_unlock_this_device,
    ),
  );

  static LocalKeyManager? _instance;

  Sodium? _sodium;
  SecureKey? _masterKey;

  LocalKeyManager._();

  static LocalKeyManager instance() {
    _instance ??= LocalKeyManager._();
    return _instance!;
  }

  Future<void> initialize() async {
    if (_sodium != null && _masterKey != null) {
      return;
    }

    _sodium = await sodium_libs.SodiumInit.init();
    await _loadOrGenerateMasterKey();
  }

  Future<void> _loadOrGenerateMasterKey() async {
    final existing = await _secureStorage.read(key: _masterKeyStorageKey);
    if (existing != null) {
      final bytes = base64Decode(existing);
      _masterKey = _sodium!.secureCopy(Uint8List.fromList(bytes));
      return;
    }

    final bytes = _sodium!.randombytes.buf(32);
    _masterKey = _sodium!.secureCopy(bytes);
    await _secureStorage.write(
      key: _masterKeyStorageKey,
      value: base64Encode(bytes),
    );
  }

  Future<Uint8List> deriveDatabaseKey(String dbPath) async {
    await initialize();

    final dbFile = File(dbPath);
    final saltFile = File('${dbFile.path}.salt');

    Uint8List salt;
    if (await saltFile.exists()) {
      salt = await saltFile.readAsBytes();
    } else {
      salt = _sodium!.randombytes.buf(16);
      await saltFile.parent.create(recursive: true);
      await saltFile.writeAsBytes(salt, flush: true);
      if (!Platform.isWindows) {
        try {
          await Process.run('chmod', ['600', saltFile.path]);
        } catch (_) {}
      }
    }

    final masterKeyBytes = _masterKey!.extractBytes();
    final context = utf8.encode('aico-db-messages');
    final combined = Uint8List.fromList([...masterKeyBytes, ...context]);
    
    final digest = sha256.convert(combined);
    final derivedKey = Uint8List.fromList(digest.bytes);

    return derivedKey;
  }
}
