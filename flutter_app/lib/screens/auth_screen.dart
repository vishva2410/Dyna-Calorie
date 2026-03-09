// ============================================================
// screens/auth_screen.dart — Login & Registration UI.
// ============================================================

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/app_state.dart';
import '../services/api_service.dart';
import 'onboarding_screen.dart';
import 'dashboard_screen.dart';

class AuthScreen extends StatefulWidget {
  const AuthScreen({super.key});

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  final _emailController    = TextEditingController();
  final _passwordController = TextEditingController();
  final _formKey            = GlobalKey<FormState>();

  bool _isLoading = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  // ── Handlers ──────────────────────────────────────────────────────────────

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() { _isLoading = true; _errorMessage = null; });

    try {
      final isLogin = _tabController.index == 0;
      final email    = _emailController.text.trim();
      final password = _passwordController.text.trim();

      if (isLogin) {
        final data = await ApiService.login(email, password);
        if (!mounted) return;
        
        final appState = context.read<AppState>();
        appState.setAuth(data['user_id']);
        appState.fetchDashboard();
        
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(builder: (_) => DashboardScreen(userId: data['user_id'])),
        );
      } else {
        final data = await ApiService.register(email, password);
        if (!mounted) return;
        
        context.read<AppState>().setAuth(data['user_id']);
        
        // After registration, go onboard
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(builder: (_) => OnboardingScreen(userId: data['user_id'])),
        );
      }
    } on ApiException catch (e) {
      setState(() => _errorMessage = e.message);
    } catch (e) {
      setState(() => _errorMessage = 'Unexpected error. Check your connection.');
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  // ── UI ────────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 28),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 56),

                // ── Logo / Title ─────────────────────────────────────────
                Text('DynaCalorie', style: theme.textTheme.headlineLarge),
                Text(
                  'AI-Powered Metabolic Tracker',
                  style: theme.textTheme.bodyLarge,
                ),
                const SizedBox(height: 40),

                // ── Tab bar ──────────────────────────────────────────────
                Container(
                  decoration: BoxDecoration(
                    color: const Color(0xFF1A1A2E),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: TabBar(
                    controller: _tabController,
                    labelColor: Colors.white,
                    unselectedLabelColor: const Color(0xFF8888A8),
                    indicator: BoxDecoration(
                      color: const Color(0xFF6C63FF),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    tabs: const [
                      Tab(text: 'Login'),
                      Tab(text: 'Register'),
                    ],
                  ),
                ),
                const SizedBox(height: 32),

                // ── Email field ──────────────────────────────────────────
                TextFormField(
                  controller: _emailController,
                  keyboardType: TextInputType.emailAddress,
                  decoration: const InputDecoration(
                    labelText: 'Email',
                    prefixIcon: Icon(Icons.email_outlined),
                  ),
                  validator: (v) => (v == null || !v.contains('@'))
                      ? 'Enter a valid email.' : null,
                ),
                const SizedBox(height: 16),

                // ── Password field ───────────────────────────────────────
                TextFormField(
                  controller: _passwordController,
                  obscureText: true,
                  decoration: const InputDecoration(
                    labelText: 'Password',
                    prefixIcon: Icon(Icons.lock_outline),
                  ),
                  validator: (v) => (v == null || v.length < 8)
                      ? 'At least 8 characters required.' : null,
                ),
                const SizedBox(height: 24),

                // ── Error message ────────────────────────────────────────
                if (_errorMessage != null) ...[
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: const Color(0xFF2E1A1A),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.error_outline, color: Color(0xFFFF6B6B), size: 18),
                        const SizedBox(width: 10),
                        Expanded(child: Text(_errorMessage!, style: const TextStyle(color: Color(0xFFFF6B6B)))),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),
                ],

                // ── Submit button ────────────────────────────────────────
                AnimatedBuilder(
                  animation: _tabController,
                  builder: (_, __) => ElevatedButton(
                    onPressed: _isLoading ? null : _submit,
                    child: _isLoading
                        ? const SizedBox(height: 22, width: 22,
                            child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                        : Text(_tabController.index == 0 ? 'Login' : 'Create Account'),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
