import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';
import '../services/api_service.dart';

class AvatarScreen extends StatefulWidget {
  final String userId;
  const AvatarScreen({super.key, required this.userId});

  @override
  State<AvatarScreen> createState() => _AvatarScreenState();
}

class _AvatarScreenState extends State<AvatarScreen> {
  late final WebViewController _controller;
  Map<String, dynamic>? _metrics;
  bool _isLoading = true;
  String? _errorMessage;
  double _weeksPredict = 0.0; // 0 to 12 weeks
  bool _webviewLoaded = false;

  @override
  void initState() {
    super.initState();
    _initWebView();
    _fetchMetrics();
  }

  void _initWebView() {
    // Note: Assuming a local machine or iOS simulator (127.0.0.1 works).
    // For Android emulator, you would use 10.0.2.2.
    _controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(const Color(0xFFF0F0F0))
      ..addJavaScriptChannel(
        'AvatarWebViewChannel',
        onMessageReceived: (JavaScriptMessage message) {
          debugPrint("WebView Content: ${message.message}");
        },
      )
      ..setNavigationDelegate(
        NavigationDelegate(
          onPageFinished: (String url) {
            setState(() {
              _webviewLoaded = true;
            });
            _updateAvatarInWebView();
          },
        ),
      )
      ..loadRequest(Uri.parse('http://127.0.0.1:8000/static/index.html'));
  }

  Future<void> _fetchMetrics() async {
    setState(() { _isLoading = true; _errorMessage = null; });
    try {
      final metrics = await ApiService.getAvatarMetrics(widget.userId);
      setState(() { _metrics = metrics; });
      if (_webviewLoaded) {
        _updateAvatarInWebView();
      }
    } on ApiException catch (e) {
      setState(() => _errorMessage = e.message);
    } catch (_) {
      setState(() => _errorMessage = 'Failed to load avatar metrics.');
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  void _updateAvatarInWebView() {
    if (!_webviewLoaded || _metrics == null) return;
    
    // Convert current dictionary to JSON string to pass into the Javascript environment.
    final jsonStr = jsonEncode(_metrics).replaceAll("'", "\\'").replaceAll('"', '\\"');
    
    _controller.runJavaScript("window.updateAvatar('$jsonStr', $_weeksPredict);").catchError((e) {
      debugPrint("JS execution error: $e");
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    
    return Scaffold(
      appBar: AppBar(
        title: const Text('Predictive 3D Body'),
        backgroundColor: Colors.transparent,
        elevation: 0,
      ),
      body: Column(
        children: [
          // Metrics Info
          if (_isLoading)
            const LinearProgressIndicator(color: Color(0xFF6C63FF))
          else if (_errorMessage != null)
            Padding(
              padding: const EdgeInsets.all(16.0),
              child: Text(_errorMessage!, style: const TextStyle(color: Colors.red)),
            )
          else if (_metrics != null)
            Padding(
              padding: const EdgeInsets.all(16.0),
              child: Text(
                'Expected change: ${(_metrics!['expected_weight_change_kg'] as num).toStringAsFixed(2)} kg/week\n'
                'Current Weight: ${_metrics!['weight_kg']} kg  |  Est. Body Fat: ${(_metrics!['body_fat'] as num).toStringAsFixed(1)}%',
                style: theme.textTheme.bodyMedium?.copyWith(color: Colors.grey[400]),
                textAlign: TextAlign.center,
              ),
            ),
            
          // The 3D WebView Canvas
          Expanded(
            child: ClipRRect(
              borderRadius: BorderRadius.circular(20),
              child: Container(
                margin: const EdgeInsets.symmetric(horizontal: 16),
                decoration: BoxDecoration(
                  border: Border.all(color: const Color(0xFF2A2A40), width: 2),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: WebViewWidget(controller: _controller),
              ),
            ),
          ),
          
          // Slider for future weeks
          Padding(
            padding: const EdgeInsets.all(24.0),
            child: Column(
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text('Current', style: theme.textTheme.titleMedium),
                    Text('In 12 Weeks', style: theme.textTheme.titleMedium),
                  ],
                ),
                Slider(
                  value: _weeksPredict,
                  min: 0,
                  max: 12,
                  divisions: 12,
                  activeColor: const Color(0xFF6C63FF),
                  inactiveColor: const Color(0xFF2A2A40),
                  label: '${_weeksPredict.toInt()} Weeks',
                  onChanged: (val) {
                    setState(() {
                      _weeksPredict = val;
                    });
                    _updateAvatarInWebView();
                  },
                ),
                Text(
                  'Slide to preview body changes if you maintain current deficit/surplus',
                  style: theme.textTheme.bodySmall?.copyWith(color: Colors.grey[500]),
                  textAlign: TextAlign.center,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
