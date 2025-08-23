import 'package:flutter/material.dart';

/// Memory timeline screen showing personal experiences and shared moments.
class MemoryScreen extends StatelessWidget {
  const MemoryScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.auto_stories, size: 64, color: Colors.grey),
          SizedBox(height: 16),
          Text('Memory Timeline', 
               style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
          Text('Personal memory timeline coming soon'),
        ],
      ),
    );
  }
}
