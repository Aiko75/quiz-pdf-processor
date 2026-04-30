import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:package_info_plus/package_info_plus.dart';
import 'package:url_launcher/url_launcher.dart';

class UpdateService {
  static const String repoOwner = 'Aiko75';
  static const String repoName = 'Auto_Handling_File';
  static const String apiUrl = 'https://api.github.com/repos/$repoOwner/$repoName/tags';

  static Future<Map<String, dynamic>?> checkForUpdate() async {
    try {
      final response = await http.get(Uri.parse(apiUrl));
      if (response.statusCode == 200) {
        final List<dynamic> tags = jsonDecode(response.body);
        if (tags.isEmpty) return null;

        final latestTag = tags.first;
        final latestVersion = latestTag['name'] as String; // e.g., "v1.3.1"
        
        final packageInfo = await PackageInfo.fromPlatform();
        final currentVersion = 'v${packageInfo.version}';
        
        if (_isNewer(latestVersion, currentVersion)) {
          return {
            'version': latestVersion,
            'url': 'https://github.com/$repoOwner/$repoName/releases/tag/$latestVersion',
            'description': 'Đã có bản cập nhật mới $latestVersion. Nhấn nút bên dưới để xem chi tiết và tải về.',
          };
        }
      }
    } catch (e) {
      // Log error
    }
    return null;
  }

  static bool _isNewer(String latest, String current) {
    // Basic semver comparison (v1.3.1 vs v1.3.0)
    final v1 = latest.replaceAll('v', '').split('.').map(int.parse).toList();
    final v2 = current.replaceAll('v', '').split('.').map(int.parse).toList();
    
    for (var i = 0; i < v1.length && i < v2.length; i++) {
      if (v1[i] > v2[i]) return true;
      if (v1[i] < v2[i]) return false;
    }
    return v1.length > v2.length;
  }

  static Future<void> launchUpdateUrl(String url) async {
    final uri = Uri.parse(url);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }
}
