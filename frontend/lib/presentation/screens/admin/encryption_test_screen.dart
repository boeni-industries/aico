import 'package:aico_frontend/core/providers/networking_providers.dart';
import 'package:aico_frontend/presentation/widgets/common/animated_button.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

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
      final encryptionService = ref.read(networkingEncryptionServiceProvider);
      
      _log('Running encryption session test...');
      _log('Using API client: ${apiClient.runtimeType}');
      _log('Using encryption service: ${encryptionService.runtimeType}');
      _log('Encryption initialized: ${encryptionService.isInitialized}');
      _log('Session active: ${encryptionService.isSessionActive}');
      
      if (!encryptionService.isSessionActive) {
        _log('⚠️ No active encryption session - handshake required');
        _log('Encryption session must be established via API handshake');
      } else {
        _log('✅ Encryption session is active');
        _log('Client ID: ${encryptionService.clientId}');
      }
      
    } catch (e) {
      _log('Echo test failed: $e');
    } finally {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
            Consumer(
              builder: (context, ref, child) {
                final encryptionService = ref.watch(networkingEncryptionServiceProvider);
                final status = encryptionService.isSessionActive 
                    ? 'Session Active' 
                    : encryptionService.isInitialized 
                        ? 'Initialized (No Session)' 
                        : 'Not Initialized';
                return Text(
                  'Encryption Status: $status',
                  style: Theme.of(context).textTheme.titleMedium,
                );
              },
            ),
            const SizedBox(height: 16),
            if (_isLoading)
              const Center(child: CircularProgressIndicator())
            else ...[
              AnimatedButton(
                onPressed: _runHandshake,
                icon: Icons.security,
                size: 48,
                borderRadius: 24,
                backgroundColor: Theme.of(context).brightness == Brightness.dark
                    ? Theme.of(context).colorScheme.primary.withValues(alpha: 0.20)
                    : Theme.of(context).colorScheme.primary.withValues(alpha: 0.18),
                foregroundColor: Theme.of(context).colorScheme.primary,
                tooltip: '1. Perform Handshake',
              ),
              const SizedBox(height: 12),
              AnimatedButton(
                onPressed: _runEchoTest,
                icon: Icons.send,
                size: 48,
                borderRadius: 24,
                backgroundColor: Theme.of(context).brightness == Brightness.dark
                    ? Theme.of(context).colorScheme.primary.withValues(alpha: 0.20)
                    : Theme.of(context).colorScheme.primary.withValues(alpha: 0.18),
                foregroundColor: Theme.of(context).colorScheme.primary,
                tooltip: '2. Send Encrypted Echo',
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
        );
  }
}
