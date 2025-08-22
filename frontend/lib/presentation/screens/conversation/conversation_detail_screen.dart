import 'package:flutter/material.dart';

/// Individual conversation detail screen for specific conversation sessions.
class ConversationDetailScreen extends StatelessWidget {
  final String conversationId;

  const ConversationDetailScreen({
    super.key,
    required this.conversationId,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Conversation $conversationId'),
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.chat, size: 64, color: Colors.grey),
            const SizedBox(height: 16),
            Text('Conversation $conversationId', 
                 style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
            const Text('Individual conversation view coming soon'),
          ],
        ),
      ),
    );
  }
}
