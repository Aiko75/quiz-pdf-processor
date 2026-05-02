import 'dart:convert';
import 'dart:io';
import 'package:path/path.dart' as p;
import 'settings_service.dart';

class BackendService {
  static final BackendService _instance = BackendService._internal();
  factory BackendService() => _instance;
  BackendService._internal();

  Process? _currentProcess;

  Future<void> runAction({
    required String action,
    Map<String, String>? params,
    required Function(String) onLog,
    required Function(Map<String, dynamic>) onResult,
    required Function(String) onError,
  }) async {
    try {
      // Xác định đường dẫn tới quiz_cli
      // Trong môi trường dev, nó nằm ở thư mục cha: ../quiz_cli.py
      // Trong môi trường production, nó nằm cùng thư mục với file exe: quiz_cli.exe
      
      final appDir = p.dirname(Platform.resolvedExecutable);
      final exePath = p.join(appDir, 'quiz_cli.exe');
      
      // Tìm kiếm script ở nhiều vị trí (cho môi trường dev)
      final possibleScriptPaths = [
        p.join(Directory.current.path, 'quiz_cli.py'),
        p.join(Directory.current.path, '..', 'quiz_cli.py'),
        p.join(Directory.current.path, '..', '..', 'quiz_cli.py'),
        // Thêm đường dẫn tuyệt đối dựa trên vị trí workspace nếu cần
      ];

      String executable = '';
      List<String> args = [];

      if (await File(exePath).exists()) {
        executable = exePath;
        args.add('--action');
        args.add(action);
      } else {
        String? foundScript;
        for (final path in possibleScriptPaths) {
          if (await File(path).exists()) {
            foundScript = path;
            break;
          }
        }

        if (foundScript != null) {
          executable = 'python';
          args.add(foundScript);
          args.add('--action');
          args.add(action);
        } else {
          onError("Không tìm thấy 'quiz_cli.exe' trong thư mục ứng dụng hoặc 'quiz_cli.py' trong thư mục nguồn.\n"
                  "Nếu bạn đang chạy bản build, hãy đảm bảo đã copy file 'quiz_cli.exe' vào cùng thư mục với ứng dụng.");
          return;
        }
      }

      if (params != null) {
        params.forEach((key, value) {
          args.add('--$key');
          if (value.isNotEmpty) {
            args.add(value);
          }
        });
      }

      // Add workspace path
      final settings = await SettingsService.getInstance();
      args.add('--workspace');
      args.add(settings.workspacePath);

      // TODO: Khi đóng gói, chúng ta sẽ gọi file .exe thay vì python script
      _currentProcess = await Process.start(executable, args);

      bool resultReceived = false;
      _currentProcess!.stdout
          .transform(utf8.decoder)
          .transform(const LineSplitter())
          .listen((line) {
        try {
          final data = jsonDecode(line);
          if (data['type'] == 'log') {
            onLog(data['message']);
          } else if (data['type'] == 'result') {
            resultReceived = true;
            onResult(data);
          }
        } catch (e) {
          if (line.trim().isNotEmpty) onLog(line);
        }
      });

      _currentProcess!.stderr
          .transform(utf8.decoder)
          .transform(const LineSplitter())
          .listen((line) {
        if (line.trim().isNotEmpty) onLog("[STDERR] $line");
      });

      final exitCode = await _currentProcess!.exitCode;
      _currentProcess = null;
      
      if (exitCode != 0 && !resultReceived) {
        onError("Tiến trình lỗi (Mã: $exitCode). Kiểm tra Log để biết chi tiết.");
      }
    } catch (e) {
      onError("Không thể khởi động tiến trình: $e");
    } finally {
      _currentProcess = null;
    }
  }

  void stop() {
    _currentProcess?.kill();
  }
}
