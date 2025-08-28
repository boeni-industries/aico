import 'package:aico_frontend/core/constants/route_names.dart';
import 'package:aico_frontend/presentation/screens/admin/admin_screen.dart';
import 'package:aico_frontend/presentation/screens/admin/logs_screen.dart';
import 'package:aico_frontend/presentation/screens/home/home_screen.dart';
import 'package:aico_frontend/presentation/screens/memory/memory_screen.dart';
import 'package:aico_frontend/presentation/screens/memory/memory_search_screen.dart';
import 'package:aico_frontend/presentation/screens/settings/privacy_settings_screen.dart';
import 'package:aico_frontend/presentation/screens/settings/settings_screen.dart';
import 'package:aico_frontend/presentation/widgets/navigation/main_layout.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

/// AICO's declarative router configuration implementing hub-and-spoke navigation
/// with progressive disclosure and cross-platform deep linking support.
class AppRouter {
  static final GoRouter _router = GoRouter(
    initialLocation: RouteNames.home,
    debugLogDiagnostics: true,
    routes: [
      // Shell route provides persistent navigation structure
      ShellRoute(
        builder: (context, state, child) => MainLayout(child: child),
        routes: [
          // Home - Avatar Central Hub
          GoRoute(
            path: RouteNames.home,
            name: 'home',
            builder: (context, state) => const HomeScreen(),
          ),


          // Direct routes to main sections
          GoRoute(
            path: '/memory',
            name: 'memory',
            builder: (context, state) => const MemoryScreen(),
            routes: [
              GoRoute(
                path: '/search',
                name: 'memory-search',
                builder: (context, state) {
                  final query = state.uri.queryParameters['q'];
                  return MemorySearchScreen(initialQuery: query);
                },
              ),
            ],
          ),

          GoRoute(
            path: '/settings',
            name: 'settings',
            builder: (context, state) => const SettingsScreen(),
            routes: [
              GoRoute(
                path: '/privacy',
                name: 'privacy-settings',
                builder: (context, state) => const PrivacySettingsScreen(),
              ),
            ],
          ),

          GoRoute(
            path: '/admin',
            name: 'admin',
            builder: (context, state) => const AdminScreen(),
            routes: [
              GoRoute(
                path: '/logs',
                name: 'admin-logs',
                builder: (context, state) => const LogsScreen(),
              ),
            ],
          ),
        ],
      ),
    ],

    // Error handling for invalid routes
    errorBuilder: (context, state) => Scaffold(
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(
              Icons.error_outline,
              size: 64,
              color: Colors.grey,
            ),
            const SizedBox(height: 16),
            Text(
              'Page not found',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 8),
            Text(
              'The page you\'re looking for doesn\'t exist.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: () => context.go(RouteNames.home),
              child: const Text('Go Home'),
            ),
          ],
        ),
      ),
    ),

    // Navigation guards and redirects
    redirect: (context, state) {
      // Add authentication checks here if needed
      // For admin routes, could check permissions
      if (state.matchedLocation.startsWith('/admin')) {
        // TODO: Add admin authentication check
        // if (!isAdminAuthenticated) return '/settings';
      }
      
      return null; // No redirect needed
    },
  );

  static GoRouter get router => _router;
}
