import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:aico_frontend/core/providers/networking_providers.dart';
import 'package:aico_frontend/core/providers/storage_providers.dart';

class EncryptionTestScreen extends ConsumerStatefulWidget {
  const EncryptionTestScreen({super.key});

  @override
  ConsumerState<EncryptionTestScreen> createState() => _EncryptionTestScreenState();
}

class _EncryptionTestScreenState extends ConsumerState<EncryptionTestScreen> {
  final List<String> _logs = [];
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _log('Encryption Test Screen Initialized.');
    _log('Encryption service loaded via Riverpod providers');
  }

  void _log(String message) {
    setState(() {
      _logs.add('[${DateTime.now().toIso8601String()}] $message');
    });
  }

  Future<void> _runHandshake() async {
    setState(() => _isLoading = true);
    
    try {
      final apiClient = ref.read(unifiedApiClientProvider);
      _log('Starting handshake with backend...');
      
      // Initialize encryption handshake
      await apiClient.initialize();
      _log('Handshake completed successfully');
      _log('API client initialized: ${apiClient.runtimeType}');
      
    } catch (e) {
      _log('Handshake failed: $e');
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _runEchoTest() async {
    setState(() => _isLoading = true);
    
    try {
      final apiClient = ref.read(unifiedApiClientProvider);
      final encryptionService = ref.read(encryptionServiceProvider);
      
      _log('Running encrypted echo test...');
      _log('Using API client: ${apiClient.runtimeType}');
      _log('Using encryption service: ${encryptionService.runtimeType}');
      
      const testMessage = 'Hello, encrypted world!';
      final encrypted = encryptionService.encrypt(testMessage);
      final decrypted = encryptionService.decrypt(encrypted);
      
      _log('Original: $testMessage');
      _log('Encrypted: $encrypted');
      _log('Decrypted: $decrypted');
      
      if (testMessage == decrypted) {
        _log('✅ Encryption test passed');
      } else {
        _log('❌ Encryption test failed');
      }
      
    } catch (e) {
      _log('Echo test failed: $e');
    } finally {
      setState(() => _isLoading = false);
    }
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
            Consumer(
              builder: (context, ref, child) {
                final encryptionService = ref.watch(encryptionServiceProvider);
                return Text(
                  'Encryption Status: Ready (${encryptionService.runtimeType})',
                  style: Theme.of(context).textTheme.titleMedium,
                );
              },
            ),
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
