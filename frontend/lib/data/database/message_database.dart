import 'dart:io';
import 'package:aico_frontend/core/services/local_key_manager.dart';
import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:path_provider/path_provider.dart';
import 'package:path/path.dart' as p;
import 'package:sqlcipher_flutter_libs/sqlcipher_flutter_libs.dart';

part 'message_database.g.dart';

/// Messages table definition
class Messages extends Table {
  TextColumn get id => text()();
  TextColumn get conversationId => text()();
  TextColumn get userId => text()();
  TextColumn get content => text()();
  TextColumn get role => text()();
  DateTimeColumn get timestamp => dateTime()();
  TextColumn get messageType => text().withDefault(const Constant('text'))();
  TextColumn get status => text().withDefault(const Constant('sent'))();
  DateTimeColumn get syncedAt => dateTime().nullable()();
  BoolColumn get needsSync => boolean().withDefault(const Constant(false))();

  @override
  Set<Column> get primaryKey => {id};
}

/// Local message database using Drift with SQLCipher encryption
@DriftDatabase(tables: [Messages])
class MessageDatabase extends _$MessageDatabase {
  MessageDatabase() : super(_openConnection());

  @override
  int get schemaVersion => 1;

  @override
  MigrationStrategy get migration => MigrationStrategy(
    onCreate: (Migrator m) async {
      await m.createAll();
      // Create indexes
      await customStatement(
        'CREATE INDEX idx_conversation_timestamp ON messages(conversation_id, timestamp)'
      );
      await customStatement(
        'CREATE INDEX idx_needs_sync ON messages(needs_sync) WHERE needs_sync = 1'
      );
    },
  );

  /// Insert conversation pair atomically (user message + AI response)
  Future<void> insertConversationPair(
    MessagesCompanion userMessage,
    MessagesCompanion aiMessage,
  ) async {
    await transaction(() async {
      await into(messages).insert(userMessage);
      await into(messages).insert(aiMessage);
    });
  }

  /// Get messages for a conversation (most recent first, limited to 100)
  Future<List<Message>> getConversationMessages(String conversationId, {int limit = 100}) {
    return (select(messages)
      ..where((t) => t.conversationId.equals(conversationId))
      ..orderBy([(t) => OrderingTerm.desc(t.timestamp)])
      ..limit(limit))
      .get();
  }

  /// Get messages since timestamp
  Future<List<Message>> getMessagesSince(String conversationId, DateTime since) {
    return (select(messages)
      ..where((t) => t.conversationId.equals(conversationId) & t.timestamp.isBiggerThanValue(since))
      ..orderBy([(t) => OrderingTerm.asc(t.timestamp)]))
      .get();
  }

  /// Get unsynced messages
  Future<List<Message>> getUnsyncedMessages() {
    return (select(messages)
      ..where((t) => t.needsSync.equals(true)))
      .get();
  }

  /// Mark message as synced
  Future<void> markAsSynced(String messageId) {
    return (update(messages)..where((t) => t.id.equals(messageId)))
      .write(MessagesCompanion(
        needsSync: const Value(false),
        syncedAt: Value(DateTime.now()),
      ));
  }
}

LazyDatabase _openConnection() {
  return LazyDatabase(() async {
    final dbFolder = await getApplicationDocumentsDirectory();
    final file = File(p.join(dbFolder.path, 'aico_messages.db'));
    
    // Debug: Print database location
    print('📁 [Database] Location: ${file.path}');

    if (Platform.isAndroid) {
      await applyWorkaroundToOpenSqlCipherOnOldAndroidVersions();
    }

    final keyManager = LocalKeyManager.instance();
    final keyBytes = await keyManager.deriveDatabaseKey(file.path);
    final keyHex = keyBytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();

    return NativeDatabase.createInBackground(
      file,
      setup: (rawDb) {
        rawDb.execute("PRAGMA key = 'x\"$keyHex\"'");
        rawDb.execute('PRAGMA cipher_page_size = 4096');
        rawDb.execute('PRAGMA kdf_iter = 64000');
        rawDb.execute('PRAGMA cipher_hmac_algorithm = HMAC_SHA512');
        rawDb.execute('PRAGMA cipher_kdf_algorithm = PBKDF2_HMAC_SHA512');
      },
    );
  });
}
