import 'package:flutter/material.dart';
import '../services/api_service.dart';

class AppState extends ChangeNotifier {
  String? userId;
  bool isInitializing = true;
  
  // Dashboard state cache
  Map<String, dynamic>? dashboardData;
  Map<String, dynamic>? historyData;
  String? dashboardError;
  bool isDashboardLoading = false;

  /// Call this when the app first opens to see if we have a saved token.
  Future<void> initializeAuth() async {
    isInitializing = true;
    notifyListeners();
    
    final storedId = await ApiService.getUserId();
    if (storedId != null) {
      userId = storedId;
    }
    
    isInitializing = false;
    notifyListeners();
  }

  /// Sets the currently active user (e.g., after login/register).
  void setAuth(String newUserId) {
    userId = newUserId;
    notifyListeners();
  }

  /// Clears auth and cached data (e.g., on logout).
  Future<void> clearAuth() async {
    await ApiService.clearCredentials();
    userId = null;
    dashboardData = null;
    historyData = null;
    notifyListeners();
  }

  /// Refreshes the global dashboard data from the backend.
  Future<void> fetchDashboard() async {
    if (userId == null) return;
    
    isDashboardLoading = true;
    dashboardError = null;
    notifyListeners();

    try {
      final data = await ApiService.getDashboard(userId!);
      dashboardData = data;
      
      // Also fetch history
      try {
        final history = await ApiService.getHistory(userId!);
        historyData = history;
      } catch (_) {
        // Soft fail for history
      }
      
    } on ApiException catch (e) {
      dashboardError = e.message;
    } catch (_) {
      dashboardError = 'Failed to load dashboard. Check connection.';
    } finally {
      isDashboardLoading = false;
      notifyListeners();
    }
  }

  /// Wrapper for logging food that automatically refreshes the dashboard state.
  Future<String> logFood(double calories, double proteinG) async {
    if (userId == null) throw Exception("User not logged in");
    
    final result = await ApiService.logFood(
      userId: userId!,
      calories: calories,
      proteinG: proteinG,
    );
    
    // Background refresh data
    fetchDashboard();
    
    return result['message'] ?? 'Logged successfully!';
  }

  /// Wrapper for logging weight that automatically refreshes the dashboard state.
  Future<Map<String, dynamic>> logWeight(double weightKg) async {
    if (userId == null) throw Exception("User not logged in");
    
    final result = await ApiService.logWeight(
      userId: userId!,
      weightKg: weightKg,
    );
    
    // Background refresh data
    fetchDashboard();
    
    return result;
  }
}
