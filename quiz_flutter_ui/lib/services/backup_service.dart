import 'dart:io';
import 'package:archive/archive_io.dart';
import 'package:path/path.dart' as p;
import 'settings_service.dart';

class BackupService {
  static Future<String?> createBackup() async {
    try {
      final settings = await SettingsService.getInstance();
      final sourceDir = Directory(settings.workspacePath);
      
      final timestamp = DateTime.now().toIso8601String().replaceAll(':', '-');
      final zipPath = p.join(p.dirname(settings.workspacePath), 'quiz_backup_$timestamp.zip');
      
      final encoder = ZipFileEncoder();
      encoder.create(zipPath);
      encoder.addDirectory(sourceDir);
      encoder.close();
      
      return zipPath;
    } catch (e) {
      return null;
    }
  }

  static Future<bool> restoreBackup(String zipPath) async {
    try {
      final settings = await SettingsService.getInstance();
      final destinationDir = Directory(settings.workspacePath);
      
      if (await destinationDir.exists()) {
        await destinationDir.delete(recursive: true);
      }
      await destinationDir.create(recursive: true);
      
      final bytes = File(zipPath).readAsBytesSync();
      final archive = ZipDecoder().decodeBytes(bytes);
      
      for (final file in archive) {
        final filename = file.name;
        if (file.isFile) {
          final data = file.content as List<int>;
          File(p.join(destinationDir.path, filename))
            ..createSync(recursive: true)
            ..writeAsBytesSync(data);
        } else {
          Directory(p.join(destinationDir.path, filename)).createSync(recursive: true);
        }
      }
      return true;
    } catch (e) {
      return false;
    }
  }
}
