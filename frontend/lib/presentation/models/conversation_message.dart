class ConversationMessage {
  final String? id;
  final bool isFromAico;
  final String message;
  final DateTime timestamp;

  ConversationMessage({
    this.id,
    required this.isFromAico,
    required this.message,
    required this.timestamp,
  });
}
