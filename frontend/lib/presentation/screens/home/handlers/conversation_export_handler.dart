import 'dart:io';

import 'package:aico_frontend/presentation/providers/conversation_provider.dart';
import 'package:aico_frontend/presentation/widgets/conversation/share_conversation_modal.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

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
    
    // Generate filename: topic_date_time.extension
    final extension = config.format == ExportFormat.markdown ? 'md' : 'pdf';
    final filename = _generateFilename(conversationState, extension);
    
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
      
    } catch (e, stackTrace) {
      // Log the actual error for debugging
      print('═══════════════════════════════════════════════════════');
      print('FILE SAVE ERROR:');
      print('Error: $e');
      print('Stack trace: $stackTrace');
      print('═══════════════════════════════════════════════════════');
      
      // Fallback to clipboard if file picker fails
      await Clipboard.setData(ClipboardData(text: content));
      
      // Return simple message for UI (detailed error is in console)
      return 'File save failed - copied to clipboard';
    }
  }

  /// Generate unique filename: topic_YYYY-MM-DD_HHmmss.ext
  String _generateFilename(dynamic conversationState, String extension) {
    final now = DateTime.now();
    
    // Format date: YYYY-MM-DD
    final dateStr = '${now.year}-'
        '${now.month.toString().padLeft(2, '0')}-'
        '${now.day.toString().padLeft(2, '0')}';
    
    // Format time: HHmmss (24-hour)
    final timeStr = '${now.hour.toString().padLeft(2, '0')}'
        '${now.minute.toString().padLeft(2, '0')}'
        '${now.second.toString().padLeft(2, '0')}';
    
    // Generate topic slug from conversation
    final topicSlug = _generateTopicSlug(conversationState);
    
    return '${topicSlug}_${dateStr}_${timeStr}.$extension';
  }

  /// Extract topic from conversation for filename
  String _generateTopicSlug(dynamic conversationState) {
    // Try to get first user message for topic
    if (conversationState.messages.isNotEmpty) {
      final firstUserMessage = conversationState.messages.firstWhere(
        (m) => m.userId != 'aico',
        orElse: () => conversationState.messages.first,
      );
      
      if (firstUserMessage.content.isNotEmpty) {
        return _slugify(firstUserMessage.content, maxWords: 4);
      }
    }
    
    // Fallback to generic
    return 'conversation';
  }

  /// Convert text to slug (kebab-case, max words)
  String _slugify(String text, {int maxWords = 4}) {
    // Remove special characters, lowercase, limit words
    final words = text
        .toLowerCase()
        .replaceAll(RegExp(r'[^\w\s-]'), '')
        .split(RegExp(r'\s+'))
        .take(maxWords)
        .toList();
    
    return words.join('-');
  }
}
