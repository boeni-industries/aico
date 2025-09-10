import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';

import 'package:aico_frontend/core/logging/models/log_entry.dart';

/// Compression utilities for log batches to optimize network transfer
class LogCompression {
  /// Compress a batch of log entries using GZIP
  static Uint8List compressBatch(List<LogEntry> entries) {
    if (entries.isEmpty) return Uint8List(0);

    try {
      // Convert entries to JSON array
      final jsonArray = entries.map((e) => e.toJson()).toList();
      final jsonString = jsonEncode(jsonArray);
      
      // Convert to bytes
      final bytes = utf8.encode(jsonString);
      
      // Compress using GZIP
      final compressed = gzip.encode(bytes);
      
      return Uint8List.fromList(compressed);
    } catch (e) {
      debugPrint('Failed to compress log batch: $e');
      // Fallback to uncompressed JSON
      final jsonArray = entries.map((e) => e.toJson()).toList();
      final jsonString = jsonEncode(jsonArray);
      return Uint8List.fromList(utf8.encode(jsonString));
    }
  }

  /// Decompress a batch of log entries from GZIP
  static List<LogEntry> decompressBatch(Uint8List compressedData) {
    if (compressedData.isEmpty) return [];

    try {
      // Decompress using GZIP
      final decompressed = gzip.decode(compressedData);
      
      // Convert to string
      final jsonString = utf8.decode(decompressed);
      
      // Parse JSON array
      final jsonArray = jsonDecode(jsonString) as List<dynamic>;
      
      // Convert to LogEntry objects
      return jsonArray
          .map((json) => LogEntry.fromJson(json as Map<String, dynamic>))
          .toList();
    } catch (e) {
      debugPrint('Failed to decompress log batch: $e');
      
      // Try to parse as uncompressed JSON
      try {
        final jsonString = utf8.decode(compressedData);
        final jsonArray = jsonDecode(jsonString) as List<dynamic>;
        return jsonArray
            .map((json) => LogEntry.fromJson(json as Map<String, dynamic>))
            .toList();
      } catch (e2) {
        debugPrint('Failed to parse uncompressed log batch: $e2');
        return [];
      }
    }
  }

  /// Calculate compression ratio for monitoring
  static double calculateCompressionRatio(List<LogEntry> entries, Uint8List compressed) {
    if (entries.isEmpty || compressed.isEmpty) return 0.0;

    try {
      final jsonArray = entries.map((e) => e.toJson()).toList();
      final jsonString = jsonEncode(jsonArray);
      final originalSize = utf8.encode(jsonString).length;
      final compressedSize = compressed.length;
      
      return compressedSize / originalSize;
    } catch (e) {
      return 1.0; // No compression
    }
  }

  /// Check if compression is beneficial for a batch
  static bool shouldCompress(List<LogEntry> entries) {
    // Only compress if we have multiple entries or large messages
    if (entries.length < 3) return false;
    
    // Check total message size
    final totalMessageLength = entries
        .map((e) => e.message.length + (e.extra?.toString().length ?? 0))
        .fold(0, (sum, length) => sum + length);
    
    // Compress if total content is over 1KB
    return totalMessageLength > 1024;
  }
}
