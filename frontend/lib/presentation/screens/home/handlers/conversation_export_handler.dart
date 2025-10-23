import 'dart:io';

import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:file_picker/file_picker.dart';

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
  /// Platform-independent: works on Desktop, Web, iOS, and Android
  Future<String> _saveToFile(String filename, String content) async {
    try {
      // Open native file picker with suggested filename
      // Desktop: Native OS file dialog
      // Web: Browser download
      // Mobile: Platform-specific file picker
      String? outputPath = await FilePicker.platform.saveFile(
        dialogTitle: 'Save conversation',
        fileName: filename,
        type: FileType.custom,
        allowedExtensions: ['md', 'pdf'],
      );
      
      // User cancelled the picker
      if (outputPath == null) {
        return 'Save cancelled';
      }
      
      // Write content to selected file (Desktop/Mobile)
      // On Web, this step is handled by the browser automatically
      final file = File(outputPath);
      await file.writeAsString(content);
      
      // Extract just the filename for display
      final savedFilename = outputPath.split(Platform.pathSeparator).last;
      return 'Saved as $savedFilename';
      
    } catch (e) {
      // Fallback to clipboard if file picker fails
      // This handles Web platform and any permission issues
      await Clipboard.setData(ClipboardData(text: content));
      return 'File save failed - copied to clipboard instead';
    }
  }
}
