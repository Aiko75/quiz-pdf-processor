import 'package:flutter/material.dart';
import 'package:window_manager/window_manager.dart';
import 'package:file_picker/file_picker.dart';
import '../services/settings_service.dart';
import '../services/backup_service.dart';
import '../services/update_service.dart';
import '../main.dart';

const _windowSizeOptions = [
  {'label': '1280 × 720 (Mặc định)', 'width': 1280.0, 'height': 720.0},
  {'label': '1366 × 768 (Laptop)', 'width': 1366.0, 'height': 768.0},
  {'label': '1600 × 900', 'width': 1600.0, 'height': 900.0},
  {'label': '1920 × 1080 (Full HD)', 'width': 1920.0, 'height': 1080.0},
];

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  late SettingsService _settings;
  bool _loaded = false;
  bool _shuffleEnabled = true;
  double _windowWidth = 1280;
  double _windowHeight = 720;
  bool _darkMode = false;
  String _workspacePath = '';

  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async {
    _settings = await SettingsService.getInstance();
    setState(() {
      _shuffleEnabled = _settings.shuffleEnabled;
      _windowWidth = _settings.windowWidth;
      _windowHeight = _settings.windowHeight;
      _darkMode = _settings.darkMode;
      _workspacePath = _settings.workspacePath;
      _loaded = true;
    });
  }

  Future<void> _pickWorkspace() async {
    String? result = await FilePicker.getDirectoryPath();
    if (result != null) {
      await _settings.setWorkspacePath(result);
      await _settings.ensureWorkspaceExists();
      setState(() => _workspacePath = result);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Đã cập nhật thư mục làm việc.')),
        );
      }
    }
  }

  Future<void> _applyWindowSize(double w, double h) async {
    await _settings.setWindowSize(w, h);
    await windowManager.setSize(Size(w, h));
    setState(() {
      _windowWidth = w;
      _windowHeight = h;
    });
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Đã đổi kích thước: ${w.toInt()} × ${h.toInt()}')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!_loaded) return const Center(child: CircularProgressIndicator());

    return Padding(
      padding: const EdgeInsets.all(32.0),
      child: ListView(
        children: [
          Text('Cài đặt', style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 32),

          // ---- Bài kiểm tra ----
          Text('Bài kiểm tra', style: Theme.of(context).textTheme.titleMedium?.copyWith(color: Theme.of(context).colorScheme.primary)),
          const SizedBox(height: 8),
          Card(
            child: Column(
              children: [
                SwitchListTile(
                  title: const Text('Trộn thứ tự câu hỏi ngẫu nhiên'),
                  subtitle: const Text('Đảo thứ tự câu hỏi mỗi lần vào phòng thi.'),
                  value: _shuffleEnabled,
                  onChanged: (val) async {
                    await _settings.setShuffleEnabled(val);
                    setState(() => _shuffleEnabled = val);
                  },
                ),
              ],
            ),
          ),

          const SizedBox(height: 24),

          // ---- Giao diện ----
          Text('Giao diện', style: Theme.of(context).textTheme.titleMedium?.copyWith(color: Theme.of(context).colorScheme.primary)),
          const SizedBox(height: 8),
          Card(
            child: Column(
              children: [
                SwitchListTile(
                  title: const Text('Giao diện tối (Dark Mode)'),
                  value: _darkMode,
                  onChanged: (val) async {
                    await _settings.setDarkMode(val);
                    themeNotifier.value = val ? ThemeMode.dark : ThemeMode.light;
                    setState(() => _darkMode = val);
                    if (mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Đã cập nhật giao diện.')),
                      );
                    }
                  },
                ),
                const Divider(height: 1),
                Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Kích thước cửa sổ', style: Theme.of(context).textTheme.titleSmall),
                      const SizedBox(height: 12),
                      Wrap(
                        spacing: 12,
                        runSpacing: 12,
                        children: _windowSizeOptions.map((option) {
                          final label = option['label'] as String;
                          final w = option['width'] as double;
                          final h = option['height'] as double;
                          final isSelected = _windowWidth == w && _windowHeight == h;
                          return ChoiceChip(
                            label: Text(label),
                            selected: isSelected,
                            onSelected: (_) => _applyWindowSize(w, h),
                          );
                        }).toList(),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: 24),

          // ---- Hệ thống ----
          Text('Hệ thống', style: Theme.of(context).textTheme.titleMedium?.copyWith(color: Theme.of(context).colorScheme.primary)),
          const SizedBox(height: 8),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Thư mục làm việc (Workspace)', style: Theme.of(context).textTheme.titleSmall),
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: Theme.of(context).colorScheme.surfaceContainerHighest,
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      _workspacePath,
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      FilledButton.icon(
                        onPressed: _pickWorkspace,
                        icon: const Icon(Icons.folder_open),
                        label: const Text('Thay đổi thư mục'),
                      ),
                      const SizedBox(width: 8),
                      OutlinedButton.icon(
                        onPressed: () async {
                          final path = await BackupService.createBackup();
                          if (mounted && path != null) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(content: Text('Đã sao lưu tại: $path')),
                            );
                          }
                        },
                        icon: const Icon(Icons.backup),
                        label: const Text('Sao lưu (Zip)'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),

          const SizedBox(height: 32),
          Center(
            child: Column(
              children: [
                Text(
                  'Quiz Processor v1.3.1',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Theme.of(context).colorScheme.outline),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 8),
                TextButton.icon(
                  onPressed: () async {
                    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Đang kiểm tra bản cập nhật...')));
                    final update = await UpdateService.checkForUpdate();
                    if (!mounted) return;
                    if (update != null) {
                      showDialog(
                        context: context,
                        builder: (context) => AlertDialog(
                          title: Text('Có bản cập nhật mới: ${update['version']}'),
                          content: Text(update['description'] ?? 'Bạn có muốn cập nhật ngay không?'),
                          actions: [
                            TextButton(onPressed: () => Navigator.pop(context), child: const Text('Để sau')),
                            FilledButton(
                              onPressed: () => UpdateService.launchUpdateUrl(update['url']),
                              child: const Text('Cập nhật ngay'),
                            ),
                          ],
                        ),
                      );
                    } else {
                      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Ứng dụng đã là bản mới nhất!')));
                    }
                  },
                  icon: const Icon(Icons.system_update_alt, size: 16),
                  label: const Text('Kiểm tra cập nhật'),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
