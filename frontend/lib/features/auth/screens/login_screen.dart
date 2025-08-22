import 'package:aico_frontend/core/theme/aico_theme.dart';
import 'package:aico_frontend/core/widgets/atoms/aico_button.dart';
import 'package:aico_frontend/core/widgets/atoms/aico_text_field.dart';
import 'package:aico_frontend/core/widgets/molecules/loading_overlay.dart';
import 'package:aico_frontend/features/auth/bloc/auth_bloc.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen>
    with TickerProviderStateMixin {
  final _formKey = GlobalKey<FormState>();
  final _userUuidController = TextEditingController();
  final _pinController = TextEditingController();
  
  late AnimationController _fadeController;
  late AnimationController _slideController;
  late Animation<double> _fadeAnimation;
  late Animation<Offset> _slideAnimation;
  
  bool _obscurePin = true;
  bool _rememberMe = false;

  @override
  void initState() {
    super.initState();
    
    // Initialize animations
    _fadeController = AnimationController(
      duration: const Duration(milliseconds: 800),
      vsync: this,
    );
    
    _slideController = AnimationController(
      duration: const Duration(milliseconds: 600),
      vsync: this,
    );
    
    _fadeAnimation = Tween<double>(
      begin: 0.0,
      end: 1.0,
    ).animate(CurvedAnimation(
      parent: _fadeController,
      curve: Curves.easeOutCubic,
    ));
    
    _slideAnimation = Tween<Offset>(
      begin: const Offset(0, 0.3),
      end: Offset.zero,
    ).animate(CurvedAnimation(
      parent: _slideController,
      curve: Curves.easeOutCubic,
    ));
    
    // Start animations
    _fadeController.forward();
    _slideController.forward();
  }

  @override
  void dispose() {
    _fadeController.dispose();
    _slideController.dispose();
    _userUuidController.dispose();
    _pinController.dispose();
    super.dispose();
  }

  void _handleSubmit() {
    if (_formKey.currentState?.validate() ?? false) {
      context.read<AuthBloc>().add(
        AuthLoginRequested(
          userUuid: _userUuidController.text.trim(),
          pin: _pinController.text,
          rememberMe: _rememberMe,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final aicoTheme = theme.extension<AicoThemeExtension>()!;
    
    return Scaffold(
      backgroundColor: aicoTheme.colors.background,
      body: BlocConsumer<AuthBloc, AuthState>(
        listener: (context, state) {
          if (state is AuthFailure) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text(state.message),
                backgroundColor: aicoTheme.colors.error,
                behavior: SnackBarBehavior.floating,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
            );
          }
        },
        builder: (context, state) {
          return Stack(
            children: [
              // Background gradient
              Container(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [
                      aicoTheme.colors.background,
                      aicoTheme.colors.surface,
                    ],
                  ),
                ),
              ),
              
              // Main content
              SafeArea(
                child: FadeTransition(
                  opacity: _fadeAnimation,
                  child: SlideTransition(
                    position: _slideAnimation,
                    child: Center(
                      child: SingleChildScrollView(
                        padding: const EdgeInsets.all(24.0),
                        child: ConstrainedBox(
                          constraints: const BoxConstraints(maxWidth: 400),
                          child: _buildLoginCard(context, aicoTheme),
                        ),
                      ),
                    ),
                  ),
                ),
              ),
              
              // Loading overlay
              if (state is AuthLoading)
                const LoadingOverlay(
                  message: "Connecting to AICO...",
                ),
            ],
          );
        },
      ),
    );
  }

  Widget _buildLoginCard(BuildContext context, AicoThemeExtension aicoTheme) {
    return Card(
      elevation: 8,
      shadowColor: aicoTheme.colors.shadow,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(24),
      ),
      child: Padding(
        padding: const EdgeInsets.all(32.0),
        child: Form(
          key: _formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // AICO Avatar & Branding
              _buildHeader(aicoTheme),
              
              const SizedBox(height: 32),
              
              // User UUID Field
              _buildUserUuidField(aicoTheme),
              
              const SizedBox(height: 20),
              
              // PIN Field
              _buildPinField(aicoTheme),
              
              const SizedBox(height: 16),
              
              // Remember Me & Forgot PIN
              _buildOptionsRow(aicoTheme),
              
              const SizedBox(height: 32),
              
              // Sign In Button
              _buildSignInButton(aicoTheme),
              
              const SizedBox(height: 24),
              
              // Help Text
              _buildHelpText(aicoTheme),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeader(AicoThemeExtension aicoTheme) {
    return Column(
      children: [
        // AICO Avatar
        Container(
          width: 80,
          height: 80,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: LinearGradient(
              colors: [
                aicoTheme.colors.primary.withValues(alpha: 0.2),
                aicoTheme.colors.primary.withValues(alpha: 0.1),
              ],
            ),
            border: Border.all(
              color: aicoTheme.colors.primary.withValues(alpha: 0.05),
              width: 2,
            ),
          ),
          child: Icon(
            Icons.psychology_outlined,
            size: 40,
            color: aicoTheme.colors.primary,
          ),
        ),
        
        const SizedBox(height: 16),
        
        // Welcome Text
        Text(
          'Welcome to AICO',
          style: aicoTheme.textTheme.headlineLarge?.copyWith(
            color: aicoTheme.colors.onSurface,
            fontWeight: FontWeight.w700,
          ),
        ),
        
        const SizedBox(height: 8),
        
        Text(
          'Sign in to continue your companion experience',
          style: aicoTheme.textTheme.bodyMedium?.copyWith(
            color: aicoTheme.colors.onSurface.withValues(alpha: 0.7),
          ),
          textAlign: TextAlign.center,
        ),
      ],
    );
  }

  Widget _buildUserUuidField(AicoThemeExtension aicoTheme) {
    return AicoTextField(
      controller: _userUuidController,
      label: 'User ID',
      hint: 'Enter your user identifier',
      prefixIcon: Icons.person_outline,
      keyboardType: TextInputType.text,
      textInputAction: TextInputAction.next,
      validator: (value) {
        if (value?.isEmpty ?? true) {
          return 'User ID is required';
        }
        // Basic UUID format validation
        final uuidRegex = RegExp(
          r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
        );
        if (!uuidRegex.hasMatch(value!)) {
          return 'Please enter a valid user ID';
        }
        return null;
      },
    );
  }

  Widget _buildPinField(AicoThemeExtension aicoTheme) {
    return AicoTextField(
      controller: _pinController,
      label: 'PIN',
      hint: 'Enter your PIN',
      prefixIcon: Icons.lock_outline,
      obscureText: _obscurePin,
      keyboardType: TextInputType.number,
      textInputAction: TextInputAction.done,
      onSubmitted: (_) => _handleSubmit(),
      suffixIcon: IconButton(
        icon: Icon(
          _obscurePin ? Icons.visibility_outlined : Icons.visibility_off_outlined,
          color: aicoTheme.colors.onSurface.withValues(alpha: 0.6),
        ),
        onPressed: () {
          setState(() {
            _obscurePin = !_obscurePin;
          });
        },
      ),
      validator: (value) {
        if (value?.isEmpty ?? true) {
          return 'PIN is required';
        }
        if (value!.length < 4) {
          return 'PIN must be at least 4 digits';
        }
        return null;
      },
    );
  }

  Widget _buildOptionsRow(AicoThemeExtension aicoTheme) {
    return Row(
      children: [
        // Remember Me
        Expanded(
          child: Row(
            children: [
              Checkbox(
                value: _rememberMe,
                onChanged: (value) {
                  setState(() {
                    _rememberMe = value ?? false;
                  });
                },
                activeColor: aicoTheme.colors.primary,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(4),
                ),
              ),
              Text(
                'Remember me',
                style: aicoTheme.textTheme.bodySmall?.copyWith(
                  color: aicoTheme.colors.onSurface.withValues(alpha: 0.8),
                ),
              ),
            ],
          ),
        ),
        
        // Forgot PIN
        TextButton(
          onPressed: () {
            // TODO: Implement forgot PIN flow
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                content: Text('Contact your administrator to reset your PIN'),
                behavior: SnackBarBehavior.floating,
              ),
            );
          },
          child: Text(
            'Forgot PIN?',
            style: aicoTheme.textTheme.bodySmall?.copyWith(
              color: aicoTheme.colors.primary,
              fontWeight: FontWeight.w500,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildSignInButton(AicoThemeExtension aicoTheme) {
    return SizedBox(
      width: double.infinity,
      child: AicoButton.primary(
        onPressed: _handleSubmit,
        child: Text(
          'Sign In to AICO',
          style: aicoTheme.textTheme.labelLarge?.copyWith(
            color: aicoTheme.colors.onPrimary,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
    );
  }

  Widget _buildHelpText(AicoThemeExtension aicoTheme) {
    return Text(
      'Need help? Contact your administrator or check the user guide.',
      style: aicoTheme.textTheme.bodySmall?.copyWith(
        color: aicoTheme.colors.onSurface.withValues(alpha: 0.6),
      ),
      textAlign: TextAlign.center,
    );
  }
}
