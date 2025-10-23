import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:aico_frontend/presentation/providers/conversation_provider.dart';
import 'package:aico_frontend/presentation/widgets/conversation/share_conversation_modal.dart';

/// Handles conversation export to clipboard and file
class ConversationExportHandler {
  final WidgetRef ref;

  ConversationExportHandler(this.ref);

  /// Quick copy conversation to clipboard
  Future<String> copyToClipboard() async {
    final conversationState = ref.read(conversationProvider);
    
    // Generate simple markdown
    final buffer = StringBuffer();
    buffer.writeln('# Conversation with AICO');
    buffer.writeln();
    
    for (final message in conversationState.messages) {
      final sender = message.userId == 'aico' ? 'AICO' : 'You';
      buffer.writeln('**$sender:** ${message.content}');
      buffer.writeln();
    }
    
    final content = buffer.toString();
    await Clipboard.setData(ClipboardData(text: content));
    
    return 'Copied to clipboard';
  }

  /// Export conversation to file (markdown or PDF)
  Future<String> exportToFile(ShareConversationConfig config) async {
    final conversationState = ref.read(conversationProvider);
    
    // Generate markdown content
    final buffer = StringBuffer();
    buffer.writeln('# Conversation with AICO');
    buffer.writeln('**Date:** ${DateTime.now().toString().split('.')[0]}');
    buffer.writeln();
    
    for (final message in conversationState.messages) {
      final sender = message.userId == 'aico' ? 'AICO' : 'You';
      final time = message.timestamp.toString().split(' ')[1].substring(0, 5);
      buffer.writeln('**$sender ($time):** ${message.content}');
      buffer.writeln();
    }
    
    final content = buffer.toString();
    
    // Generate filename with timestamp
    final timestamp = DateTime.now().toIso8601String().split('T')[0];
    final extension = config.format == ExportFormat.markdown ? 'md' : 'pdf';
    final filename = 'conversation-$timestamp.$extension';
    
    // Save to file
    final result = await _saveToFile(filename, content);
    return result;
  }

  /// Save content to file with file picker
  Future<String> _saveToFile(String filename, String content) async {
    // TODO: Implement actual file picker and save
    // For now, fallback to clipboard
    // 
    // Implementation plan:
    // 1. Add file_picker package to pubspec.yaml
    // 2. Use FilePicker.platform.saveFile() for native file picker
    // 3. Write content to selected file path
    // 
    // Example implementation:
    // ```dart
    // import 'package:file_picker/file_picker.dart';
    // import 'dart:io';
    // 
    // String? outputPath = await FilePicker.platform.saveFile(
    //   dialogTitle: 'Save conversation',
    //   fileName: filename,
    // );
    // 
    // if (outputPath != null) {
    //   final file = File(outputPath);
    //   await file.writeAsString(content);
    //   return 'Saved to $outputPath';
    // }
    // ```
    
    await Clipboard.setData(ClipboardData(text: content));
    return 'File save coming soon - copied to clipboard';
  }
}
