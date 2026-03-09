// ============================================================
// screens/dashboard_screen.dart — Main app view.
// Shows weekly calorie budget, remaining calories (progress bar),
// protein compliance, expected weight change, and guardrail alerts.
// ============================================================

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:fl_chart/fl_chart.dart';

import '../providers/app_state.dart';
import '../services/api_service.dart';
import 'logging_screen.dart';
import 'auth_screen.dart';
import 'avatar_screen.dart';

class DashboardScreen extends StatefulWidget {
  final String userId;
  const DashboardScreen({super.key, required this.userId});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  @override
  void initState() {
    super.initState();
    // Fetch dashboard initial state if empty
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (context.read<AppState>().dashboardData == null) {
        context.read<AppState>().fetchDashboard();
      }
    });
  }

  Future<void> _activateRefeed() async {
    try {
      final result = await ApiService.activateRefeed(widget.userId);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(result['message'] ?? 'Refeed activated!'),
          backgroundColor: const Color(0xFF6C63FF),
          behavior: SnackBarBehavior.floating,
        ),
      );
      context.read<AppState>().fetchDashboard();
    } on ApiException catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.message), backgroundColor: const Color(0xFFFF6B6B)),
      );
    }
  }

  Future<void> _logout() async {
    final appState = context.read<AppState>();
    await appState.clearAuth();
    if (!mounted) return;
    Navigator.of(context).pushReplacement(
      MaterialPageRoute(builder: (_) => const AuthScreen()),
    );
  }

  // ── UI ─────────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final appState = context.watch<AppState>();
    
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: Text('DynaCalorie', style: theme.textTheme.titleLarge),
        actions: [
          IconButton(icon: const Icon(Icons.logout), onPressed: _logout, tooltip: 'Logout'),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () {
          Navigator.of(context).push(
            MaterialPageRoute(builder: (_) => LoggingScreen(userId: widget.userId)),
          );
        },
        label: const Text('Log Today'),
        icon: const Icon(Icons.add),
        backgroundColor: const Color(0xFF6C63FF),
      ),
      body: RefreshIndicator(
        color: const Color(0xFF6C63FF),
        onRefresh: () async => context.read<AppState>().fetchDashboard(),
        child: appState.isDashboardLoading && appState.dashboardData == null
            ? const Center(child: CircularProgressIndicator())
            : appState.dashboardError != null
                ? Center(child: Text(appState.dashboardError!, style: const TextStyle(color: Color(0xFFFF6B6B))))
                : appState.dashboardData == null 
                    ? const Center(child: Text('No data'))
                    : _buildBody(theme, appState.dashboardData!),
      ),
    );
  }

  Widget _buildBody(ThemeData theme, Map<String, dynamic> d) {
    final weekly   = (d['weekly_budget_kcal'] as num).toDouble();
    final remaining = (d['remaining_budget_kcal'] as num).toDouble();
    final calToday  = (d['calories_consumed_today'] as num).toDouble();
    final protToday = (d['protein_consumed_today'] as num).toDouble();
    final protTarget = (d['protein_target_g'] as num).toDouble();
    final weightKg  = (d['current_weight_kg'] as num).toDouble();
    final expectedDelta = (d['expected_weight_change_kg'] as num).toDouble();
    final warnings  = List<String>.from(d['guardrail_warnings'] ?? []);
    final consumedFraction = ((weekly - remaining) / weekly).clamp(0.0, 1.0);
    final protFraction = protTarget > 0 ? (protToday / protTarget).clamp(0.0, 1.0) : 0.0;
    
    final appState = context.read<AppState>();

    return ListView(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
      children: [
        // ── Greeting ─────────────────────────────────────────────────────
        Text('Your Week at a Glance', style: theme.textTheme.headlineMedium),
        Text(
          'Current Weight: ${weightKg.toStringAsFixed(1)} kg',
          style: theme.textTheme.bodyLarge,
        ),
        const SizedBox(height: 24),

        // ── Weekly Calorie Budget Card ────────────────────────────────────
        _SectionCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(Icons.local_fire_department, color: Color(0xFF6C63FF)),
                  const SizedBox(width: 8),
                  Text('Weekly Calorie Budget', style: theme.textTheme.titleLarge),
                ],
              ),
              const SizedBox(height: 16),
              _BudgetRow(
                label: 'Total Budget',
                value: '${weekly.toStringAsFixed(0)} kcal',
                color: const Color(0xFF6C63FF),
              ),
              const SizedBox(height: 8),
              _BudgetRow(
                label: 'Remaining',
                value: '${remaining.toStringAsFixed(0)} kcal',
                color: remaining < 0 ? const Color(0xFFFF6B6B) : const Color(0xFF00D4AA),
              ),
              const SizedBox(height: 16),
              // Remaining progress bar
              ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: LinearProgressIndicator(
                  value: 1.0 - consumedFraction,
                  minHeight: 14,
                  backgroundColor: const Color(0xFF2A2A40),
                  valueColor: AlwaysStoppedAnimation<Color>(
                    remaining < 0 ? const Color(0xFFFF6B6B) : const Color(0xFF6C63FF),
                  ),
                ),
              ),
              const SizedBox(height: 8),
              Text(
                '${((1 - consumedFraction) * 100).toStringAsFixed(0)}% remaining',
                style: theme.textTheme.bodyMedium,
              ),
              const SizedBox(height: 8),
              Text(
                'Logged today: ${calToday.toStringAsFixed(0)} kcal',
                style: theme.textTheme.bodyMedium,
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),

        // ── Protein Compliance Card ───────────────────────────────────────
        _SectionCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(Icons.fitness_center, color: Color(0xFF00D4AA)),
                  const SizedBox(width: 8),
                  Text('Protein Compliance', style: theme.textTheme.titleLarge),
                ],
              ),
              const SizedBox(height: 16),
              ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: LinearProgressIndicator(
                  value: protFraction,
                  minHeight: 14,
                  backgroundColor: const Color(0xFF2A2A40),
                  valueColor: AlwaysStoppedAnimation<Color>(
                    protFraction >= 1.0 ? const Color(0xFF00D4AA) : const Color(0xFFFFB347),
                  ),
                ),
              ),
              const SizedBox(height: 10),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text('${protToday.toStringAsFixed(0)} g / ${protTarget.toStringAsFixed(0)} g',
                      style: theme.textTheme.bodyLarge),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(20),
                      color: d['protein_compliant'] == true
                          ? const Color(0xFF1A3A2E)
                          : const Color(0xFF3A1A1A),
                    ),
                    child: Text(
                      d['protein_compliant'] == true ? '✓ On Target' : '⚠ Low',
                      style: TextStyle(
                        color: d['protein_compliant'] == true
                            ? const Color(0xFF00D4AA)
                            : const Color(0xFFFF6B6B),
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),

        // ── Expected Weight Change ────────────────────────────────────────
        _SectionCard(
          child: Row(
            children: [
              const Icon(Icons.trending_down, color: Color(0xFF6C63FF), size: 32),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Expected Change', style: theme.textTheme.titleLarge),
                    const SizedBox(height: 4),
                    Text(
                      '${expectedDelta > 0 ? '+' : ''}${expectedDelta.toStringAsFixed(3)} kg this week',
                      style: TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.bold,
                        color: expectedDelta <= 0
                            ? const Color(0xFF00D4AA)
                            : const Color(0xFFFF6B6B),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),

        // ── Guardrail Warnings ────────────────────────────────────────────
        if (warnings.isNotEmpty) ...[
          ...warnings.map((w) => Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: _SectionCard(
              color: const Color(0xFF2E1A1A),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(Icons.warning_amber_rounded, color: Color(0xFFFF6B6B)),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(w, style: const TextStyle(color: Color(0xFFFF9999))),
                  ),
                ],
              ),
            ),
          )),
          const SizedBox(height: 8),
        ],

        // ── Charts ────────────────────────────────────────────────────────
        if (appState.historyData != null && appState.historyData!['weight_history'] != null)
          _buildWeightChart(theme, appState.historyData!['weight_history'] as List),
        if (appState.historyData != null && appState.historyData!['calorie_history'] != null)
          _buildCalorieChart(theme, appState.historyData!['calorie_history'] as List, weekly / 7),

        // ── View 3D Body Button ───────────────────────────────────────────
        ElevatedButton.icon(
          onPressed: () {
            Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => AvatarScreen(userId: widget.userId)),
            );
          },
          icon: const Icon(Icons.accessibility_new, color: Colors.white),
          label: const Text('View Predicted 3D Body', style: TextStyle(color: Colors.white)),
          style: ElevatedButton.styleFrom(
            backgroundColor: const Color(0xFF6C63FF),
            foregroundColor: Colors.white,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
            minimumSize: const Size.fromHeight(48),
          ),
        ),
        const SizedBox(height: 16),

        // ── Refeed Mode Toggle ────────────────────────────────────────────
        _SectionCard(
          child: SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: Text('Refeed Mode', style: theme.textTheme.titleLarge),
            subtitle: const Text('Temporarily boost budget for recovery', style: TextStyle(color: Color(0xFF9E9EBE), fontSize: 13)),
            activeColor: const Color(0xFF6C63FF),
            value: false, // State management feature for Phase 4
            onChanged: (val) async {
               if (val) {
                 await _activateRefeed();
               }
            },
          ),
        ),
        const SizedBox(height: 80), // FAB clearance
      ],
    );
  }

  // ── Chart Builders ─────────────────────────────────────────────────────────

  Widget _buildWeightChart(ThemeData theme, List history) {
    if (history.isEmpty) return const SizedBox();
    
    // Map data to FlSpot
    final spots = <FlSpot>[];
    double minW = 999;
    double maxW = 0;
    
    for (int i = 0; i < history.length; i++) {
        final double w = (history[i]['weight_kg'] as num).toDouble();
        spots.add(FlSpot(i.toDouble(), w));
        if (w < minW) minW = w;
        if (w > maxW) maxW = w;
    }
    
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: _SectionCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.show_chart, color: Color(0xFF00D4AA)),
                const SizedBox(width: 8),
                Text('Weight Trend (14 days)', style: theme.textTheme.titleLarge),
              ],
            ),
            const SizedBox(height: 24),
            SizedBox(
              height: 150,
              child: LineChart(
                LineChartData(
                  gridData: const FlGridData(show: false),
                  titlesData: const FlTitlesData(
                    rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                    topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                    bottomTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                    leftTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  ),
                  borderData: FlBorderData(show: false),
                  minX: 0,
                  maxX: (history.length - 1).toDouble() < 1 ? 1 : (history.length - 1).toDouble(),
                  minY: minW - 2,
                  maxY: maxW + 2,
                  lineBarsData: [
                    LineChartBarData(
                      spots: spots,
                      isCurved: true,
                      color: const Color(0xFF00D4AA),
                      barWidth: 3,
                      isStrokeCapRound: true,
                      dotData: const FlDotData(show: true),
                      belowBarData: BarAreaData(
                        show: true,
                        color: const Color(0xFF00D4AA).withOpacity(0.1),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCalorieChart(ThemeData theme, List history, double dailyAvgTarget) {
    if (history.isEmpty) return const SizedBox();

    final barGroups = <BarChartGroupData>[];
    for (int i = 0; i < history.length; i++) {
        final double c = (history[i]['calories_consumed'] as num).toDouble();
        barGroups.add(
            BarChartGroupData(
                x: i,
                barRods: [
                    BarChartRodData(
                        toY: c,
                        color: c > dailyAvgTarget ? const Color(0xFFFF6B6B) : const Color(0xFF6C63FF),
                        width: 14,
                        borderRadius: BorderRadius.circular(4),
                    ),
                ],
            ),
        );
    }

    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: _SectionCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.bar_chart, color: Color(0xFF6C63FF)),
                const SizedBox(width: 8),
                Text('Calorie Intake vs Target', style: theme.textTheme.titleLarge),
              ],
            ),
            const SizedBox(height: 24),
            SizedBox(
              height: 150,
              child: BarChart(
                BarChartData(
                  gridData: const FlGridData(show: false),
                  titlesData: const FlTitlesData(
                    rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                    topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                    bottomTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                    leftTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  ),
                  borderData: FlBorderData(show: false),
                  barGroups: barGroups,
                  extraLinesData: ExtraLinesData(
                    horizontalLines: [
                      HorizontalLine(
                        y: dailyAvgTarget,
                        color: const Color(0xFF00D4AA).withOpacity(0.5),
                        strokeWidth: 2,
                        dashArray: [5, 5],
                      )
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Rounded card wrapper
class _SectionCard extends StatelessWidget {
  final Widget child;
  final Color? color;
  const _SectionCard({required this.child, this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: color ?? const Color(0xFF1A1A2E),
        borderRadius: BorderRadius.circular(20),
      ),
      child: child,
    );
  }
}

class _BudgetRow extends StatelessWidget {
  final String label;
  final String value;
  final Color color;
  const _BudgetRow({required this.label, required this.value, required this.color});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: const TextStyle(color: Color(0xFF9E9EBE))),
        Text(value, style: TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 16)),
      ],
    );
  }
}
