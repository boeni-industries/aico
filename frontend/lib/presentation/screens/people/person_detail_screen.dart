import 'package:flutter/material.dart';

/// Individual person detail screen for relationship management.
class PersonDetailScreen extends StatelessWidget {
  final String personId;

  const PersonDetailScreen({
    super.key,
    required this.personId,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Person $personId'),
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.person, size: 64, color: Colors.grey),
            const SizedBox(height: 16),
            Text('Person $personId', 
                 style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
            const Text('Individual relationship details coming soon'),
          ],
        ),
      ),
    );
  }
}
