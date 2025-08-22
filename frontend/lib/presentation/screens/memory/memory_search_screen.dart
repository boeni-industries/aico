import 'package:flutter/material.dart';

/// Memory search screen for finding specific conversations and moments.
class MemorySearchScreen extends StatelessWidget {
  final String? initialQuery;

  const MemorySearchScreen({
    super.key,
    this.initialQuery,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Search Memories'),
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.search, size: 64, color: Colors.grey),
            const SizedBox(height: 16),
            const Text('Memory Search', 
                 style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
            Text('Search functionality coming soon${initialQuery != null ? ' (Query: $initialQuery)' : ''}'),
          ],
        ),
      ),
    );
  }
}
