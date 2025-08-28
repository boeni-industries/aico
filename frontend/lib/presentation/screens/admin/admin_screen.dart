import 'package:aico_frontend/presentation/screens/admin/encryption_test_screen.dart';
import 'package:flutter/material.dart';

/// Admin screen for system administration and developer tools.
class AdminScreen extends StatelessWidget {
  const AdminScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Admin & Developer Tools'),
      ),
      body: ListView(
        children: [
          ListTile(
            leading: const Icon(Icons.security),
            title: const Text('Transport Encryption Test'),
            subtitle: const Text('Verify client-server end-to-end encryption'),
            onTap: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => const EncryptionTestScreen()),
              );
            },
          ),
          const Divider(),
        ],
      ),
    );
  }
}
