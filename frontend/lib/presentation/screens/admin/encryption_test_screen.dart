import 'package:aico_frontend/core/di/service_locator.dart';
import 'package:aico_frontend/core/services/encryption_service.dart';
import 'package:aico_frontend/networking/clients/unified_api_client.dart';
import 'package:flutter/material.dart';

class EncryptionTestScreen extends StatefulWidget {
  const EncryptionTestScreen({super.key});

  @override
  State<EncryptionTestScreen> createState() => _EncryptionTestScreenState();
}

class _EncryptionTestScreenState extends State<EncryptionTestScreen> {
  final UnifiedApiClient _apiService = ServiceLocator.get<UnifiedApiClient>();
  final EncryptionService _encryptionService = ServiceLocator.get<EncryptionService>();
  final List<String> _logs = [];
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _log('Encryption Test Screen Initialized.');
    _log('Encryption Service Initialized: ${_encryptionService.isInitialized}');
    _log('Encryption Session Active: ${_encryptionService.isSessionActive}');
  }

  void _log(String message) {
    setState(() {
      _logs.add('[${DateTime.now().toIso8601String()}] $message');
    });
  }

  Future<void> _runHandshake() async {
    setState(() => _isLoading = true);
    _log('Attempting to initialize API client...');
    try {
      await _apiService.initialize();
      _log('✅ API client initialized!');
      _log('Encryption Service Initialized: ${_encryptionService.isInitialized}');
      _log('Encryption Session Active: ${_encryptionService.isSessionActive}');
    } catch (e) {
      _log('❌ API client initialization failed: $e');
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _runEchoTest() async {
    if (!_encryptionService.isSessionActive) {
      _log('⚠️ Cannot run echo test: Encryption session not active.');
      return;
    }
    setState(() => _isLoading = true);
    _log('Sending encrypted echo request...');
    try {
      final response = await _apiService.post('/echo', data: {'message': 'Hello from the AICO app!'});
      _log('✅ Echo successful!');
      _log('Server response: ${response.toString()}');
    } catch (e) {
      _log('❌ Echo failed: $e');
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
            Text('Encryption Status: ${_encryptionService.isSessionActive ? "Active" : "Inactive"}', style: Theme.of(context).textTheme.titleMedium),
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
                onPressed: _encryptionService.isSessionActive ? _runEchoTest : null,
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
