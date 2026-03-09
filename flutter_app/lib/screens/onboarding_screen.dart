// ============================================================
// screens/onboarding_screen.dart — Multi-step baseline form.
// Collects metabolic profile after first registration.
// ============================================================

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/app_state.dart';
import '../services/api_service.dart';
import 'dashboard_screen.dart';

class OnboardingScreen extends StatefulWidget {
  final String userId;
  const OnboardingScreen({super.key, required this.userId});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  final _pageController = PageController();
  int _currentPage = 0;

  // ── Form fields ──────────────────────────────────────────────────────────
  final _ageController    = TextEditingController();
  final _heightController = TextEditingController();
  final _weightController = TextEditingController();
  final _bfController     = TextEditingController();
  final _neckController   = TextEditingController();
  final _waistController  = TextEditingController();
  final _hipController    = TextEditingController();

  String _selectedGender  = 'male';
  double _activityLevel   = 1.375; // Lightly active default
  String _goal            = 'fat_loss';
  double _targetRate      = 0.5;

  bool _isLoading = false;
  String? _errorMessage;

  final _formKeys = List.generate(3, (_) => GlobalKey<FormState>());

  @override
  void dispose() {
    _pageController.dispose();
    _ageController.dispose();
    _heightController.dispose();
    _weightController.dispose();
    _bfController.dispose();
    _neckController.dispose();
    _waistController.dispose();
    _hipController.dispose();
    super.dispose();
  }

  void _nextPage() {
    if (_formKeys[_currentPage].currentState!.validate()) {
      _pageController.nextPage(
        duration: const Duration(milliseconds: 400),
        curve: Curves.easeInOut,
      );
    }
  }

  Future<void> _submit() async {
    if (!_formKeys[2].currentState!.validate()) return;
    setState(() { _isLoading = true; _errorMessage = null; });

    final bf = double.tryParse(_bfController.text);
    final neck = double.tryParse(_neckController.text);
    final waist = double.tryParse(_waistController.text);
    final hip = double.tryParse(_hipController.text);

    if (bf == null && (neck == null || waist == null || (_selectedGender == 'female' && hip == null))) {
      setState(() => _errorMessage = 'Please provide either Body Fat % OR (Neck, Waist, and for females, Hips) measurements.');
      if (mounted) setState(() => _isLoading = false);
      return;
    }

    try {
      await ApiService.onboard(
        userId:        widget.userId,
        age:           int.parse(_ageController.text),
        gender:        _selectedGender,
        heightCm:      double.parse(_heightController.text),
        weightKg:      double.parse(_weightController.text),
        bodyFat:       bf,
        neckCm:        neck,
        waistCm:       waist,
        hipCm:         hip,
        activityLevel: _activityLevel,
        goal:          _goal,
        targetRate:    _targetRate,
      );

      if (!mounted) return;
      
      context.read<AppState>().fetchDashboard();
      
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => DashboardScreen(userId: widget.userId)),
      );
    } on ApiException catch (e) {
      setState(() => _errorMessage = e.message);
    } catch (_) {
      setState(() => _errorMessage = 'Could not save profile. Try again.');
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  // ── Page builders ──────────────────────────────────────────────────────────

  Widget _page1(ThemeData theme) => Form(
    key: _formKeys[0],
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Basic Info', style: theme.textTheme.headlineMedium),
        const SizedBox(height: 8),
        Text('Tell us about yourself', style: theme.textTheme.bodyLarge),
        const SizedBox(height: 32),
        TextFormField(
          controller: _ageController,
          keyboardType: TextInputType.number,
          decoration: const InputDecoration(labelText: 'Age (years)'),
          validator: (v) {
            final age = int.tryParse(v ?? '');
            return (age == null || age < 10 || age > 100) ? 'Enter valid age.' : null;
          },
        ),
        const SizedBox(height: 16),
        DropdownButtonFormField<String>(
          value: _selectedGender,
          decoration: const InputDecoration(labelText: 'Gender'),
          dropdownColor: const Color(0xFF252540),
          items: const [
            DropdownMenuItem(value: 'male',   child: Text('Male')),
            DropdownMenuItem(value: 'female', child: Text('Female')),
            DropdownMenuItem(value: 'other',  child: Text('Other')),
          ],
          onChanged: (v) => setState(() => _selectedGender = v!),
        ),
        const SizedBox(height: 16),
        TextFormField(
          controller: _heightController,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          decoration: const InputDecoration(labelText: 'Height (cm)'),
          validator: (v) {
            final h = double.tryParse(v ?? '');
            return (h == null || h < 100 || h > 250) ? 'Enter valid height.' : null;
          },
        ),
      ],
    ),
  );

  Widget _page2(ThemeData theme) => Form(
    key: _formKeys[1],
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Body Composition', style: theme.textTheme.headlineMedium),
        const SizedBox(height: 8),
        Text('Used to calculate your exact metabolic rate', style: theme.textTheme.bodyLarge),
        const SizedBox(height: 32),
        TextFormField(
          controller: _weightController,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          decoration: const InputDecoration(labelText: 'Weight (kg)'),
          validator: (v) {
            final w = double.tryParse(v ?? '');
            return (w == null || w < 30 || w > 300) ? 'Enter valid weight.' : null;
          },
        ),
        const SizedBox(height: 16),
        TextFormField(
          controller: _bfController,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          decoration: const InputDecoration(labelText: 'Body Fat % (Optional)'),
          validator: (v) {
            if (v == null || v.isEmpty) return null;
            final bf = double.tryParse(v);
            return (bf == null || bf < 3 || bf > 60) ? 'Enter valid body fat %.' : null;
          },
        ),
        const SizedBox(height: 16),
        Text('Or input Tape Measurements for 3D body prediction:', style: theme.textTheme.bodyMedium?.copyWith(color: Colors.grey[400])),
        const SizedBox(height: 16),
        Row(
          children: [
            Expanded(child: TextFormField(
              controller: _neckController,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              decoration: const InputDecoration(labelText: 'Neck (cm)'),
            )),
            const SizedBox(width: 8),
            Expanded(child: TextFormField(
              controller: _waistController,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              decoration: const InputDecoration(labelText: 'Waist (cm)'),
            )),
          ],
        ),
        if (_selectedGender == 'female') ...[
          const SizedBox(height: 16),
          TextFormField(
            controller: _hipController,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            decoration: const InputDecoration(labelText: 'Hips (cm)'),
          ),
        ],
        const SizedBox(height: 24),
        Text('Activity Level', style: theme.textTheme.titleLarge),
        const SizedBox(height: 12),
        ...[
          [1.2,   'Sedentary (desk job, no exercise)'],
          [1.375, 'Lightly Active (1–3 days/week)'],
          [1.55,  'Moderately Active (3–5 days/week)'],
          [1.725, 'Very Active (6–7 days/week)'],
          [1.9,   'Athlete / Physical job (2× daily)'],
        ].map((entry) => RadioListTile<double>(
          value:    entry[0] as double,
          groupValue: _activityLevel,
          title: Text(entry[1] as String, style: theme.textTheme.bodyLarge),
          activeColor: const Color(0xFF6C63FF),
          contentPadding: EdgeInsets.zero,
          onChanged: (v) => setState(() => _activityLevel = v!),
        )),
      ],
    ),
  );

  Widget _page3(ThemeData theme) => Form(
    key: _formKeys[2],
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Your Goal', style: theme.textTheme.headlineMedium),
        const SizedBox(height: 8),
        Text('We\'ll calculate your weekly calorie budget accordingly', style: theme.textTheme.bodyLarge),
        const SizedBox(height: 32),
        ...[
          ['fat_loss',     'Fat Loss',      Icons.trending_down],
          ['maintenance',  'Maintenance',   Icons.balance],
          ['muscle_gain',  'Muscle Gain',   Icons.trending_up],
        ].map((entry) => _GoalCard(
          label:     entry[1] as String,
          icon:      entry[2] as IconData,
          isSelected: _goal == entry[0],
          onTap:    () => setState(() => _goal = entry[0] as String),
        )),
        const SizedBox(height: 24),
        Text('Target Rate of Change', style: theme.textTheme.titleLarge),
        Text(
          '${_targetRate.toStringAsFixed(2)} kg / week',
          style: const TextStyle(color: Color(0xFF6C63FF), fontWeight: FontWeight.bold, fontSize: 18),
        ),
        Slider(
          min: 0.1, max: 1.5,
          divisions: 14,
          value: _targetRate,
          activeColor: const Color(0xFF6C63FF),
          onChanged: (v) => setState(() => _targetRate = v),
        ),
      ],
    ),
  );

  // ── Build ──────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 28),
          child: Column(
            children: [
              const SizedBox(height: 32),
              // Step indicators
              Row(
                children: List.generate(3, (i) => Expanded(
                  child: Container(
                    height: 4,
                    margin: const EdgeInsets.symmetric(horizontal: 3),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(2),
                      color: i <= _currentPage
                          ? const Color(0xFF6C63FF)
                          : const Color(0xFF2A2A40),
                    ),
                  ),
                )),
              ),
              const SizedBox(height: 32),
              Expanded(
                child: PageView(
                  controller: _pageController,
                  physics: const NeverScrollableScrollPhysics(),
                  onPageChanged: (p) => setState(() => _currentPage = p),
                  children: [
                    SingleChildScrollView(child: _page1(theme)),
                    SingleChildScrollView(child: _page2(theme)),
                    SingleChildScrollView(child: _page3(theme)),
                  ],
                ),
              ),
              if (_errorMessage != null)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 8),
                  child: Text(_errorMessage!, style: const TextStyle(color: Color(0xFFFF6B6B))),
                ),
              Padding(
                padding: const EdgeInsets.only(bottom: 24, top: 8),
                child: ElevatedButton(
                  onPressed: _isLoading ? null : (_currentPage < 2 ? _nextPage : _submit),
                  child: _isLoading
                      ? const SizedBox(height: 22, width: 22,
                          child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                      : Text(_currentPage < 2 ? 'Continue' : 'Start Tracking'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _GoalCard extends StatelessWidget {
  final String label;
  final IconData icon;
  final bool isSelected;
  final VoidCallback onTap;
  const _GoalCard({required this.label, required this.icon, required this.isSelected, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: isSelected ? const Color(0xFF6C63FF) : const Color(0xFF2A2A40),
            width: isSelected ? 2 : 1,
          ),
          color: isSelected ? const Color(0xFF1E1B40) : const Color(0xFF1A1A2E),
        ),
        child: Row(
          children: [
            Icon(icon, color: isSelected ? const Color(0xFF6C63FF) : const Color(0xFF8888A8)),
            const SizedBox(width: 12),
            Text(label, style: TextStyle(
              fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
              color: isSelected ? Colors.white : const Color(0xFF9E9EBE),
              fontSize: 16,
            )),
            const Spacer(),
            if (isSelected) const Icon(Icons.check_circle, color: Color(0xFF6C63FF)),
          ],
        ),
      ),
    );
  }
}
