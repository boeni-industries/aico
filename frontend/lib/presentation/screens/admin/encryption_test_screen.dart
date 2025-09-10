import 'package:flutter/material.dart';

class EncryptionTestScreen extends StatefulWidget {
  const EncryptionTestScreen({super.key});

  @override
  State<EncryptionTestScreen> createState() => _EncryptionTestScreenState();
}

class _EncryptionTestScreenState extends State<EncryptionTestScreen> {
  // TODO: Replace with Riverpod providers when these services are migrated
  // final UnifiedApiClient _apiService = ref.read(unifiedApiClientProvider);
  // final EncryptionService _encryptionService = ref.read(encryptionServiceProvider);
  final List<String> _logs = [];
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _log('Encryption Test Screen Initialized.');
    _log('TODO: Encryption service needs to be migrated to Riverpod providers');
  }

  void _log(String message) {
    setState(() {
      _logs.add('[${DateTime.now().toIso8601String()}] $message');
    });
  }

  Future<void> _runHandshake() async {
    setState(() => _isLoading = true);
    _log('TODO: Handshake functionality needs migration to Riverpod providers');
    setState(() => _isLoading = false);
  }

  Future<void> _runEchoTest() async {
    setState(() => _isLoading = true);
    _log('TODO: Echo test functionality needs migration to Riverpod providers');
    setState(() => _isLoading = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Transport Encryption Test'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text('Encryption Status: TODO - Migrate to Riverpod', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 16),
            if (_isLoading)
              const Center(child: CircularProgressIndicator())
            else ...[
              ElevatedButton(
                onPressed: _runHandshake,
                child: const Text('1. Perform Handshake'),
              ),
              const SizedBox(height: 8),
              ElevatedButton(
                onPressed: _runEchoTest,
                child: const Text('2. Send Encrypted Echo'),
              ),
            ],
            const SizedBox(height: 16),
            const Text('Logs', style: TextStyle(fontWeight: FontWeight.bold)),
            const Divider(),
            Expanded(
              child: Container(
                color: Theme.of(context).colorScheme.surfaceContainerHighest,
                padding: const EdgeInsets.all(8.0),
                child: ListView.builder(
                  itemCount: _logs.length,
                  itemBuilder: (context, index) {
                    return Text(_logs[index], style: const TextStyle(fontFamily: 'monospace', fontSize: 12));
                  },
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
