// ============================================================
// screens/logging_screen.dart — Manual Food & Weight Entry
// ============================================================

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_state.dart';
import '../services/api_service.dart';

class LoggingScreen extends StatefulWidget {
  final String userId;
  const LoggingScreen({super.key, required this.userId});

  @override
  State<LoggingScreen> createState() => _LoggingScreenState();
}

class _LoggingScreenState extends State<LoggingScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  // ── Food Log Fields ────────────────────────────────────────────────────────
  final _foodFormKey  = GlobalKey<FormState>();
  final _calController = TextEditingController();
  final _proController = TextEditingController();

  // ── Weight Log Fields ──────────────────────────────────────────────────────
  final _weightFormKey    = GlobalKey<FormState>();
  final _weightController = TextEditingController();

  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    _calController.dispose();
    _proController.dispose();
    _weightController.dispose();
    super.dispose();
  }

  // ── Handlers ─────────────────────────────────────────────────────────────

  Future<void> _submitFood() async {
    if (!_foodFormKey.currentState!.validate()) return;
    setState(() => _isLoading = true);

    try {
      final msg = await context.read<AppState>().logFood(
        double.parse(_calController.text),
        double.parse(_proController.text),
      );
      
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(msg), backgroundColor: const Color(0xFF00D4AA)),
      );
      Navigator.of(context).pop(); // Return to dashboard
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.message), backgroundColor: const Color(0xFFFF6B6B)),
      );
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _submitWeight() async {
    if (!_weightFormKey.currentState!.validate()) return;
    setState(() => _isLoading = true);

    try {
      final data = await context.read<AppState>().logWeight(
        double.parse(_weightController.text),
      );
      
      if (!mounted) return;
      
      final msg = data['recalibrated'] == true 
          ? 'Weight logged! 14-day recalibration triggered.'
          : data['message'] ?? 'Weight logged!';

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(msg), backgroundColor: const Color(0xFF6C63FF)),
      );

      // If recalibrated, maybe show the summary dialog before popping, or just pop
      Navigator.of(context).pop(); 
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.message), backgroundColor: const Color(0xFFFF6B6B)),
      );
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  // ── UI ───────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(
        title: const Text('Log Entry'),
        backgroundColor: Colors.transparent,
        elevation: 0,
        bottom: TabBar(
          controller: _tabController,
          labelColor: const Color(0xFF6C63FF),
          unselectedLabelColor: const Color(0xFF8888A8),
          indicatorColor: const Color(0xFF6C63FF),
          tabs: const [
            Tab(icon: Icon(Icons.fastfood), text: 'Food / Macros'),
            Tab(icon: Icon(Icons.monitor_weight), text: 'Weight'),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _buildFoodTab(theme),
          _buildWeightTab(theme),
        ],
      ),
    );
  }

  Widget _buildFoodTab(ThemeData theme) {
    return Padding(
      padding: const EdgeInsets.all(28.0),
      child: Form(
        key: _foodFormKey,
        child: Column(
          children: [
            const Icon(Icons.local_fire_department, size: 64, color: Color(0xFF6C63FF)),
            const SizedBox(height: 16),
            Text('Quick Add Calories', style: theme.textTheme.headlineMedium),
            const SizedBox(height: 32),
            TextFormField(
              controller: _calController,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              decoration: const InputDecoration(
                labelText: 'Total Calories',
                suffixText: 'kcal',
                prefixIcon: Icon(Icons.restaurant_menu),
              ),
              validator: (v) {
                final c = double.tryParse(v ?? '');
                return (c == null || c < 0) ? 'Enter valid calories' : null;
              },
            ),
            const SizedBox(height: 20),
            TextFormField(
              controller: _proController,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              decoration: const InputDecoration(
                labelText: 'Total Protein',
                suffixText: 'g',
                prefixIcon: Icon(Icons.fitness_center),
              ),
              validator: (v) {
                final p = double.tryParse(v ?? '');
                return (p == null || p < 0) ? 'Enter valid protein' : null;
              },
            ),
            const Spacer(),
            ElevatedButton(
              onPressed: _isLoading ? null : _submitFood,
              child: _isLoading 
                ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                : const Text('Save Food Log'),
            ),
            const SizedBox(height: 20),
          ],
        ),
      ),
    );
  }

  Widget _buildWeightTab(ThemeData theme) {
    return Padding(
      padding: const EdgeInsets.all(28.0),
      child: Form(
        key: _weightFormKey,
        child: Column(
          children: [
            const Icon(Icons.monitor_weight_outlined, size: 64, color: Color(0xFF00D4AA)),
            const SizedBox(height: 16),
            Text('Log Morning Weight', style: theme.textTheme.headlineMedium),
            Text(
              'A 14-day recalibration will trigger automatically if due.',
              textAlign: TextAlign.center,
              style: theme.textTheme.bodyMedium,
            ),
            const SizedBox(height: 32),
            TextFormField(
              controller: _weightController,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: Color(0xFF00D4AA)),
              textAlign: TextAlign.center,
              decoration: const InputDecoration(
                labelText: 'Current Weight',
                suffixText: 'kg',
              ),
              validator: (v) {
                final w = double.tryParse(v ?? '');
                return (w == null || w <= 0) ? 'Enter a valid weight' : null;
              },
            ),
            const Spacer(),
            ElevatedButton(
              style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF00D4AA)),
              onPressed: _isLoading ? null : _submitWeight,
              child: _isLoading 
                ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                : const Text('Save Weight Log'),
            ),
            const SizedBox(height: 20),
          ],
        ),
      ),
    );
  }
}
