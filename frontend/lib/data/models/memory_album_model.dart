/// Memory Album Data Models
/// 
/// Client-side models for Memory Album feature.
/// Maps to backend API schemas with additional UI metadata.
library;

import 'package:flutter/material.dart';

/// Memory entry representing a saved moment from conversation
class MemoryEntry {
  final String memoryId;
  final String conversationId;
  final String? messageId;
  
  // Content
  final String content;
  final MemoryContentType contentType;
  final MemoryType type;
  final String category;
  final String? userNote;
  
  // Categorization
  final List<String> tags;
  final String? emotionalTone;
  
  // Temporal context
  final DateTime createdAt;
  final DateTime updatedAt;
  
  // Conversation-level fields
  final String? conversationTitle;
  final String? conversationSummary;
  final String? turnRange;
  final List<String>? keyMoments;
  
  // Engagement
  final int revisitCount;
  final DateTime? lastRevisited;
  final bool isFavorite;

  const MemoryEntry({
    required this.memoryId,
    required this.conversationId,
    this.messageId,
    required this.content,
    required this.contentType,
    required this.type,
    required this.category,
    this.userNote,
    required this.tags,
    this.emotionalTone,
    required this.createdAt,
    required this.updatedAt,
    this.conversationTitle,
    this.conversationSummary,
    this.turnRange,
    this.keyMoments,
    required this.revisitCount,
    this.lastRevisited,
    required this.isFavorite,
  });

  /// Create from API response JSON
  factory MemoryEntry.fromJson(Map<String, dynamic> json) {
    return MemoryEntry(
      memoryId: json['fact_id'] as String,
      conversationId: json['source_conversation_id'] as String,
      messageId: json['source_message_id'] as String?,
      content: json['content'] as String,
      contentType: MemoryContentType.fromString(json['content_type'] as String? ?? 'message'),
      type: MemoryType.fromString(json['memory_type'] as String? ?? 'fact'),
      category: json['category'] as String,
      userNote: json['user_note'] as String?,
      tags: (json['tags'] as List<dynamic>?)?.map((e) => e as String).toList() ?? [],
      emotionalTone: json['emotional_tone'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
      conversationTitle: json['conversation_title'] as String?,
      conversationSummary: json['conversation_summary'] as String?,
      turnRange: json['turn_range'] as String?,
      keyMoments: (json['key_moments'] as List<dynamic>?)?.map((e) => e as String).toList(),
      revisitCount: json['revisit_count'] as int? ?? 0,
      lastRevisited: json['last_revisited'] != null 
          ? DateTime.parse(json['last_revisited'] as String)
          : null,
      isFavorite: json['is_favorite'] as bool? ?? false,
    );
  }

  /// Convert to JSON for API requests
  Map<String, dynamic> toJson() {
    return {
      'fact_id': memoryId,
      'source_conversation_id': conversationId,
      'source_message_id': messageId,
      'content': content,
      'content_type': contentType.value,
      'memory_type': type.value,
      'category': category,
      'user_note': userNote,
      'tags': tags,
      'emotional_tone': emotionalTone,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
      'conversation_title': conversationTitle,
      'conversation_summary': conversationSummary,
      'turn_range': turnRange,
      'key_moments': keyMoments,
      'revisit_count': revisitCount,
      'last_revisited': lastRevisited?.toIso8601String(),
      'is_favorite': isFavorite,
    };
  }

  /// Copy with updated fields
  MemoryEntry copyWith({
    String? userNote,
    List<String>? tags,
    bool? isFavorite,
    int? revisitCount,
    DateTime? lastRevisited,
  }) {
    return MemoryEntry(
      memoryId: memoryId,
      conversationId: conversationId,
      messageId: messageId,
      content: content,
      contentType: contentType,
      type: type,
      category: category,
      userNote: userNote ?? this.userNote,
      tags: tags ?? this.tags,
      emotionalTone: emotionalTone,
      createdAt: createdAt,
      updatedAt: DateTime.now(),
      conversationTitle: conversationTitle,
      conversationSummary: conversationSummary,
      turnRange: turnRange,
      keyMoments: keyMoments,
      revisitCount: revisitCount ?? this.revisitCount,
      lastRevisited: lastRevisited ?? this.lastRevisited,
      isFavorite: isFavorite ?? this.isFavorite,
    );
  }

  /// Get accent color based on emotional tone
  Color get accentColor {
    switch (emotionalTone?.toLowerCase()) {
      case 'joyful':
      case 'happy':
        return const Color(0xFF8DD686); // Muted green
      case 'reflective':
      case 'thoughtful':
        return const Color(0xFFB8A1EA); // Soft purple
      case 'vulnerable':
      case 'sad':
        return const Color(0xFF8DD6B8); // Mint
      case 'excited':
        return const Color(0xFFB8A1EA); // Soft purple
      default:
        return const Color(0xFFB8A1EA); // Default purple accent
    }
  }

  /// Get icon emoji based on memory type
  String get iconEmoji {
    switch (type) {
      case MemoryType.fact:
        return '💡';
      case MemoryType.insight:
        return '✨';
      case MemoryType.moment:
        return '🌟';
      case MemoryType.milestone:
        return '🎯';
      case MemoryType.wisdom:
        return '🧠';
    }
  }

  /// Check if this is a conversation-level memory
  bool get isConversationMemory => contentType == MemoryContentType.conversation;
}

/// Type of memory content
enum MemoryContentType {
  message,
  conversation,
  excerpt;

  String get value {
    switch (this) {
      case MemoryContentType.message:
        return 'message';
      case MemoryContentType.conversation:
        return 'conversation';
      case MemoryContentType.excerpt:
        return 'excerpt';
    }
  }

  static MemoryContentType fromString(String value) {
    switch (value.toLowerCase()) {
      case 'conversation':
        return MemoryContentType.conversation;
      case 'excerpt':
        return MemoryContentType.excerpt;
      default:
        return MemoryContentType.message;
    }
  }
}

/// Type of memory
enum MemoryType {
  fact,        // "I'm allergic to shellfish"
  insight,     // "I realized I need to set boundaries"
  moment,      // "When AICO made me laugh"
  milestone,   // "First time I opened up about anxiety"
  wisdom;      // "AICO's advice that helped"

  String get value {
    switch (this) {
      case MemoryType.fact:
        return 'fact';
      case MemoryType.insight:
        return 'insight';
      case MemoryType.moment:
        return 'moment';
      case MemoryType.milestone:
        return 'milestone';
      case MemoryType.wisdom:
        return 'wisdom';
    }
  }

  static MemoryType fromString(String value) {
    switch (value.toLowerCase()) {
      case 'insight':
        return MemoryType.insight;
      case 'moment':
        return MemoryType.moment;
      case 'milestone':
        return MemoryType.milestone;
      case 'wisdom':
        return MemoryType.wisdom;
      default:
        return MemoryType.fact;
    }
  }
}

/// Request to remember a message or conversation
class RememberRequest {
  final String conversationId;
  final String? messageId;
  final String content;
  final MemoryContentType contentType;
  final String factType;
  final String category;
  final String? userNote;
  final List<String>? tags;
  final String? emotionalTone;
  final String memoryType;
  
  // Conversation-level fields
  final String? conversationTitle;
  final String? conversationSummary;
  final String? turnRange;
  final List<String>? keyMoments;

  const RememberRequest({
    required this.conversationId,
    this.messageId,
    required this.content,
    this.contentType = MemoryContentType.message,
    this.factType = 'preference',
    this.category = 'personal',
    this.userNote,
    this.tags,
    this.emotionalTone,
    this.memoryType = 'fact',
    this.conversationTitle,
    this.conversationSummary,
    this.turnRange,
    this.keyMoments,
  });

  Map<String, dynamic> toJson() {
    return {
      'conversation_id': conversationId,
      'message_id': messageId,
      'content': content,
      'content_type': contentType.value,
      'fact_type': factType,
      'category': category,
      'user_note': userNote,
      'tags': tags,
      'emotional_tone': emotionalTone,
      'memory_type': memoryType,
      'conversation_title': conversationTitle,
      'conversation_summary': conversationSummary,
      'turn_range': turnRange,
      'key_moments': keyMoments,
    };
  }
}

/// Request to update memory metadata
class UpdateMemoryRequest {
  final String? userNote;
  final List<String>? tags;
  final bool? isFavorite;

  const UpdateMemoryRequest({
    this.userNote,
    this.tags,
    this.isFavorite,
  });

  Map<String, dynamic> toJson() {
    return {
      if (userNote != null) 'user_note': userNote,
      if (tags != null) 'tags': tags,
      if (isFavorite != null) 'is_favorite': isFavorite,
    };
  }
}
