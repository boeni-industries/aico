import 'package:flutter/material.dart';

/// Settings screen for user preferences and configuration.
class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.settings, size: 64, color: Colors.grey),
          SizedBox(height: 16),
          Text('Settings', 
               style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
          Text('User preferences coming soon'),
        ],
      ),
    );
  }
}
