// ============================================================
// main.dart — App entry point, theming, and routing.
// ============================================================

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:provider/provider.dart';

import 'providers/app_state.dart';
import 'screens/auth_screen.dart';
import 'screens/dashboard_screen.dart';
import 'services/api_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(
    ChangeNotifierProvider(
      create: (_) => AppState(),
      child: const DynaCalorieApp(),
    ),
  );
}

class DynaCalorieApp extends StatelessWidget {
  const DynaCalorieApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'DynaCalorie AI',
      debugShowCheckedModeBanner: false,
      // ── Dark theme ──────────────────────────────────────────────────────
      themeMode: ThemeMode.dark,
      darkTheme: ThemeData(
        useMaterial3: true,
        brightness: Brightness.dark,
        // Rich dark surface palette
        colorScheme: const ColorScheme.dark(
          primary:    Color(0xFF6C63FF),   // Electric violet
          secondary:  Color(0xFF00D4AA),   // Teal accent
          surface:    Color(0xFF1A1A2E),   // Deep navy
          error:      Color(0xFFFF6B6B),
          onPrimary:  Colors.white,
          onSurface:  Color(0xFFE8E8F0),
        ),
        scaffoldBackgroundColor: const Color(0xFF0F0F1A),
        cardTheme: CardThemeData(
          color: const Color(0xFF1A1A2E),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          elevation: 8,
          shadowColor: Colors.black54,
        ),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: const Color(0xFF252540),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(14),
            borderSide: BorderSide.none,
          ),
          labelStyle: const TextStyle(color: Color(0xFF9E9EBE)),
        ),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor: const Color(0xFF6C63FF),
            foregroundColor: Colors.white,
            shape:       RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
            minimumSize: const Size.fromHeight(52),
            textStyle:   const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
          ),
        ),
        textTheme: const TextTheme(
          headlineLarge: TextStyle(fontFamily: 'Outfit', fontWeight: FontWeight.bold, fontSize: 32, color: Color(0xFFE8E8F0)),
          headlineMedium: TextStyle(fontFamily: 'Outfit', fontWeight: FontWeight.w600, fontSize: 24, color: Color(0xFFE8E8F0)),
          titleLarge:    TextStyle(fontFamily: 'Outfit', fontWeight: FontWeight.w500, fontSize: 18, color: Color(0xFFE8E8F0)),
          bodyLarge:     TextStyle(fontSize: 15, color: Color(0xFFB0B0CC)),
          bodyMedium:    TextStyle(fontSize: 13, color: Color(0xFF8888A8)),
        ),
      ),
      // ── Routing ─────────────────────────────────────────────────────────
      home: const _SplashGate(),
    );
  }
}

/// Checks if a token is already stored; routes to Dashboard or Auth accordingly.
class _SplashGate extends StatefulWidget {
  const _SplashGate();
  @override
  State<_SplashGate> createState() => _SplashGateState();
}

class _SplashGateState extends State<_SplashGate> {
  @override
  void initState() {
    super.initState();
    _route();
  }

  Future<void> _route() async {
    final appState = context.read<AppState>();
    await appState.initializeAuth();

    if (!mounted) return;

    if (appState.userId != null && await ApiService.getToken() != null) {
      appState.fetchDashboard(); // Kick off data load
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => DashboardScreen(userId: appState.userId!)),
      );
    } else {
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => const AuthScreen()),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      body: Center(child: CircularProgressIndicator()),
    );
  }
}
