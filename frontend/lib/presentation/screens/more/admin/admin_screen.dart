import 'package:flutter/material.dart';

/// Admin screen for system administration and developer tools.
class AdminScreen extends StatelessWidget {
  const AdminScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('System Administration'),
      ),
      body: const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.admin_panel_settings, size: 64, color: Colors.grey),
            SizedBox(height: 16),
            Text('Admin Dashboard', 
                 style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
            Text('System administration coming soon'),
          ],
        ),
      ),
    );
  }
}
