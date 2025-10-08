import 'package:aico_frontend/presentation/widgets/chat/thinking_bubble.dart';
import 'package:flutter/material.dart';

/// Test screen to preview the thinking bubble animation
class ThinkingBubbleTestScreen extends StatelessWidget {
  const ThinkingBubbleTestScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF5F6FA), // Soft white-neutral background
      appBar: AppBar(
        title: const Text('Thinking Bubble Test'),
        backgroundColor: Colors.transparent,
        elevation: 0,
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text(
              'AICO is thinking...',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w600,
                color: Colors.black87,
              ),
            ),
            const SizedBox(height: 32),
            
            // The thinking bubble
            Container(
              padding: const EdgeInsets.all(24),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Avatar
                  CircleAvatar(
                    radius: 16,
                    backgroundColor: const Color(0xFFB8A1EA).withOpacity(0.1),
                    child: const Icon(
                      Icons.face,
                      size: 16,
                      color: Color(0xFFB8A1EA),
                    ),
                  ),
                  const SizedBox(width: 12),
                  
                  // Thinking bubble
                  const Expanded(
                    child: ThinkingBubble(),
                  ),
                ],
              ),
            ),
            
            const SizedBox(height: 32),
            
            const Text(
              'Watch the particles form and converge!',
              style: TextStyle(
                fontSize: 14,
                color: Colors.black54,
                fontStyle: FontStyle.italic,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
