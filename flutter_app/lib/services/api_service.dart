// ============================================================
// api_service.dart — HTTP client for all FastAPI endpoints.
// Handles JWT storage, error parsing, and response decoding.
// ============================================================

import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class ApiService {
  // ── Configuration ──────────────────────────────────────────────────────────
  // Change to your production URL when deploying.
  static const String _baseUrl = 'http://127.0.0.1:8000';
  static const String _tokenKey = 'access_token';
  static const String _userIdKey = 'user_id';

  // ── Token helpers ──────────────────────────────────────────────────────────

  /// Saves the JWT and user ID locally after login/register.
  static Future<void> saveCredentials(String token, String userId) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_tokenKey, token);
    await prefs.setString(_userIdKey, userId);
  }

  /// Returns the stored JWT, or null if not logged in.
  static Future<String?> getToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_tokenKey);
  }

  /// Returns the stored user ID, or null if not logged in.
  static Future<String?> getUserId() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_userIdKey);
  }

  /// Clears credentials on logout.
  static Future<void> clearCredentials() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_tokenKey);
    await prefs.remove(_userIdKey);
  }

  // ── Shared request builder ─────────────────────────────────────────────────

  static Future<Map<String, String>> _authHeaders() async {
    final token = await getToken();
    return {
      'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  /// Generic POST helper. Throws [ApiException] on non-2xx responses.
  static Future<Map<String, dynamic>> _post(
    String path,
    Map<String, dynamic> body,
  ) async {
    final headers = await _authHeaders();
    final response = await http
        .post(
          Uri.parse('$_baseUrl$path'),
          headers: headers,
          body: jsonEncode(body),
        )
        .timeout(const Duration(seconds: 15));

    return _handle(response);
  }

  /// Generic GET helper.
  static Future<Map<String, dynamic>> _get(String path) async {
    final headers = await _authHeaders();
    final response = await http
        .get(Uri.parse('$_baseUrl$path'), headers: headers)
        .timeout(const Duration(seconds: 15));

    return _handle(response);
  }

  /// Parses the HTTP response or throws an [ApiException].
  static Map<String, dynamic> _handle(http.Response response) {
    final body = jsonDecode(response.body) as Map<String, dynamic>;
    if (response.statusCode >= 200 && response.statusCode < 300) {
      return body;
    }
    final detail = body['detail'] ?? 'Unknown error';
    throw ApiException(response.statusCode, detail.toString());
  }

  // ══════════════════════════════════════════════════════════════════════════
  // AUTH ENDPOINTS
  // ══════════════════════════════════════════════════════════════════════════

  /// POST /auth/register
  static Future<Map<String, dynamic>> register(String email, String password) async {
    final data = await _post('/auth/register', {
      'email': email,
      'password': password,
    });
    await saveCredentials(data['access_token'], data['user_id']);
    return data;
  }

  /// POST /auth/login
  static Future<Map<String, dynamic>> login(String email, String password) async {
    final data = await _post('/auth/login', {
      'email': email,
      'password': password,
    });
    await saveCredentials(data['access_token'], data['user_id']);
    return data;
  }

  /// POST /auth/onboard
  static Future<Map<String, dynamic>> onboard({
    required String userId,
    required int age,
    required String gender,
    required double heightCm,
    required double weightKg,
    double? bodyFat,
    double? neckCm,
    double? waistCm,
    double? hipCm,
    required double activityLevel,
    required String goal,
    required double targetRate,
  }) async {
    return _post('/auth/onboard', {
      'user_id': userId,
      'age': age,
      'gender': gender,
      'height_cm': heightCm,
      'weight_kg': weightKg,
      if (bodyFat != null) 'body_fat': bodyFat,
      if (neckCm != null) 'neck_cm': neckCm,
      if (waistCm != null) 'waist_cm': waistCm,
      if (hipCm != null) 'hip_cm': hipCm,
      'activity_level': activityLevel,
      'goal': goal,
      'target_rate': targetRate,
    });
  }

  // ══════════════════════════════════════════════════════════════════════════
  // DASHBOARD
  // ══════════════════════════════════════════════════════════════════════════

  /// GET /dashboard/{user_id}
  static Future<Map<String, dynamic>> getDashboard(String userId) async {
    return _get('/dashboard/$userId');
  }

  /// GET /dashboard/{user_id}/avatar
  static Future<Map<String, dynamic>> getAvatarMetrics(String userId) async {
    return _get('/dashboard/$userId/avatar');
  }

  /// GET /dashboard/{user_id}/history
  static Future<Map<String, dynamic>> getHistory(String userId) async {
    return _get('/dashboard/$userId/history');
  }

  // ══════════════════════════════════════════════════════════════════════════
  // LOGGING
  // ══════════════════════════════════════════════════════════════════════════

  /// POST /log/food
  static Future<Map<String, dynamic>> logFood({
    required String userId,
    required double calories,
    required double proteinG,
  }) async {
    return _post('/log/food', {
      'user_id': userId,
      'calories': calories,
      'protein_g': proteinG,
    });
  }

  /// POST /log/weight
  static Future<Map<String, dynamic>> logWeight({
    required String userId,
    required double weightKg,
  }) async {
    return _post('/log/weight', {
      'user_id': userId,
      'weight_kg': weightKg,
    });
  }

  // ══════════════════════════════════════════════════════════════════════════
  // ACTIONS
  // ══════════════════════════════════════════════════════════════════════════

  /// POST /action/refeed
  static Future<Map<String, dynamic>> activateRefeed(String userId) async {
    return _post('/action/refeed', {'user_id': userId});
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Custom exception for API errors
// ─────────────────────────────────────────────────────────────────────────────
class ApiException implements Exception {
  final int statusCode;
  final String message;

  const ApiException(this.statusCode, this.message);

  @override
  String toString() => 'ApiException [$statusCode]: $message';
}
