class ConversationMessage {
  final bool isFromAico;
  final String message;
  final DateTime timestamp;

  ConversationMessage({
    required this.isFromAico,
    required this.message,
    required this.timestamp,
  });
}
