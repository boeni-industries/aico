import 'package:flutter/material.dart';

/// Conversation history screen showing past conversations.
class ConversationHistoryScreen extends StatelessWidget {
  const ConversationHistoryScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Conversation History'),
      ),
      body: const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.history, size: 64, color: Colors.grey),
            SizedBox(height: 16),
            Text('Conversation History', style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
            Text('Conversation history coming soon'),
          ],
        ),
      ),
    );
  }
}
