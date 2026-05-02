import 'package:flutter/material.dart';
import 'package:path/path.dart' as p;
import 'dart:io';
import 'dart:convert';
import 'package:file_picker/file_picker.dart';
import '../widgets/path_selector.dart';
import '../widgets/log_console.dart';
import '../services/backend_service.dart';
import '../services/settings_service.dart';
import '../services/database_service.dart';
import 'quiz_taking_screen.dart';
import 'quiz_result_screen.dart';

class ExamListScreen extends StatelessWidget {
  const ExamListScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 3,
      child: Column(
        children: [
          const TabBar(
            tabs: [
              Tab(icon: Icon(Icons.computer), text: 'Bài thi trực tuyến'),
              Tab(icon: Icon(Icons.document_scanner), text: 'Chấm file'),
              Tab(icon: Icon(Icons.history), text: 'Lịch sử làm bài'),
            ],
          ),
          const Expanded(
            child: TabBarView(
              children: [
                _InteractiveExamList(),
                _FileGradingWidget(),
                _HistoryTab(),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _InteractiveExamList extends StatefulWidget {
  const _InteractiveExamList();

  @override
  State<_InteractiveExamList> createState() => _InteractiveExamListState();
}

class _InteractiveExamListState extends State<_InteractiveExamList> {
  List<Map<String, dynamic>> _items = []; // Can be folders or exams
  bool _isLoading = true;
  String _currentSubPath = '';
  String _viewMode = 'list';
  late SettingsService _settings;

  @override
  void initState() {
    super.initState();
    _loadExams();
  }

  Future<void> _loadExams() async {
    setState(() => _isLoading = true);
    try {
      _settings = await SettingsService.getInstance();
      _viewMode = _settings.examViewMode;

      final currentDir = Directory(
        p.join(_settings.examsPath, _currentSubPath),
      );
      if (!await currentDir.exists()) {
        await currentDir.create(recursive: true);
      }

      final List<Map<String, dynamic>> items = [];
      final entities = currentDir.listSync();

      for (var entity in entities) {
        final name = p.basename(entity.path);
        if (entity is Directory) {
          items.add({'type': 'folder', 'name': name, 'path': entity.path});
        } else if (entity is File && entity.path.endsWith('.json')) {
          try {
            final content = await entity.readAsString();
            final data = jsonDecode(content);
            items.add({
              'type': 'exam',
              'name': name,
              'file_path': entity.path,
              ...data,
            });
          } catch (e) {}
        }
      }

      items.sort((a, b) {
        if (a['type'] == b['type']) {
          return (a['title'] ?? a['name']).toString().compareTo(
            (b['title'] ?? b['name']).toString(),
          );
        }
        return a['type'] == 'folder' ? -1 : 1;
      });

      setState(() {
        _items = items;
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _createFolder() async {
    final controller = TextEditingController();
    final name = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Tạo thư mục mới'),
        content: TextField(
          controller: controller,
          autofocus: true,
          decoration: const InputDecoration(
            labelText: 'Tên thư mục',
            hintText: 'Ví dụ: Toán Cao Cấp',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Hủy'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, controller.text),
            child: const Text('Tạo'),
          ),
        ],
      ),
    );

    if (name != null && name.isNotEmpty) {
      final newDir = Directory(
        p.join(_settings.examsPath, _currentSubPath, name),
      );
      await newDir.create(recursive: true);
      _loadExams();
    }
  }

  Future<void> _moveItem(Map<String, dynamic> item) async {
    final folders = _settings.getExamSubFolders();
    String? target = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Di chuyển "${item['name'] ?? item['title']}"'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Chọn thư mục đích:'),
            const SizedBox(height: 16),
            SizedBox(
              width: double.maxFinite,
              child: DropdownButtonFormField<String>(
                decoration: const InputDecoration(
                  border: OutlineInputBorder(),
                  isDense: true,
                ),
                items: [
                  const DropdownMenuItem(value: '', child: Text('Thư mục gốc')),
                  ...folders.map(
                    (f) => DropdownMenuItem(value: f, child: Text(f)),
                  ),
                ],
                onChanged: (v) => Navigator.pop(ctx, v),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Hủy'),
          ),
        ],
      ),
    );

    if (target != null) {
      try {
        final currentPath = item['type'] == 'folder'
            ? item['path']
            : item['file_path'];
        final newPath = p.join(
          _settings.examsPath,
          target,
          p.basename(currentPath),
        );

        if (currentPath == newPath) return;

        if (item['type'] == 'folder') {
          await Directory(currentPath).rename(newPath);
        } else {
          await File(currentPath).rename(newPath);
        }
        _loadExams();
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Đã di chuyển thành công!')),
        );
      } catch (e) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Lỗi khi di chuyển: $e')));
      }
    }
  }

  Future<void> _openExamsDirectory() async {
    final path = p.join(_settings.examsPath, _currentSubPath);
    // On Windows: explorer.exe
    Process.run('explorer.exe', [path]);
  }

  Future<void> _showImportDialog(BuildContext context) async {
    String? filePath;
    final titleController = TextEditingController();
    int timeLimit = 60;
    String targetFolder = _currentSubPath;
    final folders = _settings.getExamSubFolders();

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          title: const Text('Nhập đề thi mới'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Card(
                  color: Theme.of(context).colorScheme.surfaceContainerHighest,
                  child: Padding(
                    padding: const EdgeInsets.all(12.0),
                    child: Row(
                      children: [
                        const Icon(Icons.description, color: Colors.blue),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Text(
                            filePath == null
                                ? 'Chưa chọn file .json'
                                : p.basename(filePath!),
                            style: TextStyle(
                              fontWeight: filePath == null
                                  ? null
                                  : FontWeight.bold,
                              fontStyle: filePath == null
                                  ? FontStyle.italic
                                  : null,
                            ),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        TextButton(
                          onPressed: () async {
                            final result = await FilePicker.pickFiles(
                              type: FileType.custom,
                              allowedExtensions: ['json'],
                              initialDirectory: _settings.examsPath,
                            );
                            if (result != null) {
                              setDialogState(() {
                                filePath = result.files.single.path;
                                if (titleController.text.isEmpty) {
                                  titleController.text = p
                                      .basenameWithoutExtension(filePath!);
                                }
                              });
                            }
                          },
                          child: const Text('Chọn file'),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: titleController,
                  decoration: const InputDecoration(
                    labelText: 'Tiêu đề bài thi',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 16),
                DropdownButtonFormField<String>(
                  initialValue: targetFolder,
                  decoration: const InputDecoration(
                    labelText: 'Thư mục đích',
                    border: OutlineInputBorder(),
                  ),
                  items: [
                    const DropdownMenuItem(
                      value: '',
                      child: Text('Thư mục gốc'),
                    ),
                    ...folders.map(
                      (f) => DropdownMenuItem(value: f, child: Text(f)),
                    ),
                  ],
                  onChanged: (v) =>
                      setDialogState(() => targetFolder = v ?? ''),
                ),
                const SizedBox(height: 16),
                Row(
                  children: [
                    const Text('Thời gian (phút):'),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Slider(
                        value: timeLimit.toDouble(),
                        min: 5,
                        max: 180,
                        divisions: 35,
                        label: timeLimit.toString(),
                        onChanged: (v) =>
                            setDialogState(() => timeLimit = v.toInt()),
                      ),
                    ),
                    Text('$timeLimit p'),
                  ],
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('Hủy'),
            ),
            FilledButton(
              onPressed: filePath == null
                  ? null
                  : () => Navigator.pop(ctx, true),
              child: const Text('Nhập ngay'),
            ),
          ],
        ),
      ),
    );
    if (confirmed != true) return;

    if (!context.mounted) return;
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (_) => const AlertDialog(
        title: Text('Đang nhập đề...'),
        content: SizedBox(height: 8, child: LinearProgressIndicator()),
      ),
    );

    BackendService().runAction(
      action: 'import',
      params: {
        'input': filePath ?? '',
        'title': titleController.text,
        'time-limit': timeLimit.toString(),
        'folder': targetFolder,
      },
      onLog: (_) {},
      onResult: (res) {
        Navigator.of(context).pop();
        if (res['status'] == 'success') {
          _loadExams();
          ScaffoldMessenger.of(
            context,
          ).showSnackBar(const SnackBar(content: Text('Nhập đề thành công!')));
        }
      },
      onError: (err) {
        Navigator.of(context).pop();
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Lỗi: $err')));
      },
    );
  }

  Future<void> _showImportFolderDialog(BuildContext context) async {
    String? sourceDir;
    String targetFolder = _currentSubPath;
    final folders = _settings.getExamSubFolders();

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          title: const Text('Nhập từ thư mục'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Card(
                color: Theme.of(context).colorScheme.surfaceContainerHighest,
                child: Padding(
                  padding: const EdgeInsets.all(12.0),
                  child: Row(
                    children: [
                      const Icon(Icons.folder, color: Colors.amber),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          sourceDir == null
                              ? 'Chưa chọn thư mục nguồn'
                              : p.basename(sourceDir!),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      TextButton(
                        onPressed: () async {
                          final result = await FilePicker.getDirectoryPath();
                          if (result != null) {
                            setDialogState(() => sourceDir = result);
                          }
                        },
                        child: const Text('Chọn'),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
              DropdownButtonFormField<String>(
                initialValue: targetFolder,
                decoration: const InputDecoration(
                  labelText: 'Thư mục đích (trong Exams)',
                  border: OutlineInputBorder(),
                ),
                items: [
                  const DropdownMenuItem(value: '', child: Text('Thư mục gốc')),
                  ...folders.map(
                    (f) => DropdownMenuItem(value: f, child: Text(f)),
                  ),
                ],
                onChanged: (v) => setDialogState(() => targetFolder = v ?? ''),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('Hủy'),
            ),
            FilledButton(
              onPressed: sourceDir == null
                  ? null
                  : () => Navigator.pop(ctx, true),
              child: const Text('Nhập ngay'),
            ),
          ],
        ),
      ),
    );

    if (confirmed != true || sourceDir == null) return;

    setState(() => _isLoading = true);
    try {
      final dir = Directory(sourceDir!);
      final targetPath = p.join(_settings.examsPath, targetFolder);
      await Directory(targetPath).create(recursive: true);

      int count = 0;
      await for (final entity in dir.list()) {
        if (entity is File && entity.path.endsWith('.json')) {
          final fileName = p.basename(entity.path);
          await entity.copy(p.join(targetPath, fileName));
          count++;
        }
      }

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Đã nhập $count đề thi thành công!')),
      );
      _loadExams();
    } catch (e) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Lỗi khi nhập: $e')));
    } finally {
      setState(() => _isLoading = false);
    }
  }

  void _renameItem(Map<String, dynamic> item) async {
    final controller = TextEditingController(
      text: item['type'] == 'folder' ? item['name'] : item['title'],
    );
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Đổi tên'),
        content: TextField(
          controller: controller,
          decoration: const InputDecoration(labelText: 'Tên mới'),
          autofocus: true,
          onSubmitted: (_) => Navigator.pop(ctx, true),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Hủy'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Lưu'),
          ),
        ],
      ),
    );

    if (confirmed == true && controller.text.isNotEmpty) {
      try {
        if (item['type'] == 'folder') {
          final oldPath = item['path'];
          final newPath = p.join(p.dirname(oldPath), controller.text);
          await Directory(oldPath).rename(newPath);
        } else {
          final filePath = item['file_path'];
          final content = await File(filePath).readAsString();
          final data = jsonDecode(content);
          data['title'] = controller.text;
          await File(filePath).writeAsString(jsonEncode(data));
        }
        _loadExams();
      } catch (e) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Lỗi khi đổi tên: $e')));
      }
    }
  }

  void _deleteItem(Map<String, dynamic> item) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(item['type'] == 'folder' ? 'Xóa thư mục?' : 'Xóa bài thi?'),
        content: Text(
          'Bạn có chắc chắn muốn xóa "${item['name'] ?? item['title']}"?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Hủy'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            child: const Text('Xóa'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      try {
        final path = item['type'] == 'folder'
            ? item['path']
            : item['file_path'];
        if (item['type'] == 'folder') {
          await Directory(path).delete(recursive: true);
        } else {
          await File(path).delete();
        }
        _loadExams();
      } catch (e) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Lỗi khi xóa: $e')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) return const Center(child: CircularProgressIndicator());

    if (_items.isEmpty && _currentSubPath.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.quiz_outlined,
              size: 64,
              color: Theme.of(context).colorScheme.outline,
            ),
            const SizedBox(height: 16),
            Text(
              'Chưa có bài thi nào.',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            const Text(
              'Hãy sang tab "Tạo đề" và chọn "Tạo bài kiểm tra trực tuyến" để bắt đầu.',
            ),
            const SizedBox(height: 24),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                FilledButton.tonalIcon(
                  onPressed: () => _showImportDialog(context),
                  icon: const Icon(Icons.upload_file),
                  label: const Text('Nhập đề'),
                ),
                const SizedBox(width: 8),
                FilledButton.tonalIcon(
                  onPressed: () => _showImportFolderDialog(context),
                  icon: const Icon(Icons.folder_zip_outlined),
                  label: const Text('Nhập từ thư mục'),
                ),
                const SizedBox(width: 16),
                FilledButton.icon(
                  onPressed: _loadExams,
                  icon: const Icon(Icons.refresh),
                  label: const Text('Làm mới'),
                ),
              ],
            ),
          ],
        ),
      );
    }

    return Padding(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              IconButton(
                icon: const Icon(Icons.home),
                onPressed: _currentSubPath.isEmpty
                    ? null
                    : () => setState(() {
                        _currentSubPath = '';
                        _loadExams();
                      }),
              ),
              const Icon(Icons.chevron_right),
              if (_currentSubPath.isNotEmpty) ...[
                Text(
                  _currentSubPath,
                  style: const TextStyle(fontWeight: FontWeight.bold),
                ),
                const SizedBox(width: 8),
              ],
              const Spacer(),
              SegmentedButton<String>(
                segments: const [
                  ButtonSegment(value: 'list', icon: Icon(Icons.list)),
                  ButtonSegment(value: 'grid', icon: Icon(Icons.grid_view)),
                ],
                selected: {_viewMode},
                onSelectionChanged: (val) {
                  setState(() => _viewMode = val.first);
                  _settings.setExamViewMode(val.first);
                },
              ),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                _currentSubPath.isEmpty
                    ? 'Môn học / Thư mục chính'
                    : _currentSubPath,
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              Row(
                children: [
                  OutlinedButton.icon(
                    onPressed: _openExamsDirectory,
                    icon: const Icon(Icons.folder_open),
                    label: const Text('Mở thư mục'),
                  ),
                  const SizedBox(width: 8),
                  OutlinedButton.icon(
                    onPressed: _createFolder,
                    icon: const Icon(Icons.create_new_folder),
                    label: const Text('Thư mục mới'),
                  ),
                  const SizedBox(width: 8),
                  FilledButton.tonalIcon(
                    onPressed: () => _showImportDialog(context),
                    icon: const Icon(Icons.upload_file),
                    label: const Text('Nhập đề'),
                  ),
                  const SizedBox(width: 8),
                  FilledButton.tonalIcon(
                    onPressed: () => _showImportFolderDialog(context),
                    icon: const Icon(Icons.folder_zip_outlined),
                    label: const Text('Nhập từ thư mục'),
                  ),
                  const SizedBox(width: 8),
                  IconButton(
                    icon: const Icon(Icons.refresh),
                    onPressed: _loadExams,
                    tooltip: 'Làm mới',
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 24),
          Expanded(
            child: _viewMode == 'grid' ? _buildGridView() : _buildListView(),
          ),
        ],
      ),
    );
  }

  Widget _buildGridView() {
    return GridView.builder(
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 3,
        childAspectRatio: 1.5,
        crossAxisSpacing: 16,
        mainAxisSpacing: 16,
      ),
      itemCount: _items.length,
      itemBuilder: (context, index) => _buildItemCard(_items[index]),
    );
  }

  Widget _buildListView() {
    return ListView.builder(
      itemCount: _items.length,
      itemBuilder: (context, index) => _buildItemListTile(_items[index]),
    );
  }

  Widget _buildItemCard(Map<String, dynamic> item) {
    if (item['type'] == 'folder') {
      return Card(
        child: InkWell(
          onTap: () => setState(() {
            _currentSubPath = p.join(_currentSubPath, item['name']);
            _loadExams();
          }),
          child: Stack(
            children: [
              Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(Icons.folder, size: 48, color: Colors.amber),
                    const SizedBox(height: 8),
                    Text(
                      item['name'],
                      style: const TextStyle(fontWeight: FontWeight.bold),
                      textAlign: TextAlign.center,
                    ),
                  ],
                ),
              ),
              Positioned(
                top: 4,
                right: 4,
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    IconButton(
                      icon: const Icon(
                        Icons.drive_file_move_outlined,
                        size: 18,
                      ),
                      onPressed: () => _moveItem(item),
                    ),
                    IconButton(
                      icon: const Icon(Icons.delete_outline, size: 18),
                      onPressed: () => _deleteItem(item),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      );
    }
    final qCount = (item['questions'] as List?)?.length ?? 0;
    return Card(
      child: InkWell(
        onTap: () => Navigator.of(context).push(
          MaterialPageRoute(
            builder: (context) => TakingExamScreen(examData: item),
          ),
        ),
        child: Padding(
          padding: const EdgeInsets.all(12.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Text(
                      item['title'] ?? 'Bài thi',
                      style: const TextStyle(fontWeight: FontWeight.bold),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.drive_file_move_outlined, size: 18),
                    onPressed: () => _moveItem(item),
                  ),
                  IconButton(
                    icon: const Icon(
                      Icons.delete_outline,
                      size: 18,
                      color: Colors.red,
                    ),
                    onPressed: () => _deleteItem(item),
                  ),
                ],
              ),
              const Spacer(),
              Row(
                children: [
                  const Icon(Icons.help_outline, size: 14),
                  const SizedBox(width: 4),
                  Text('$qCount câu', style: const TextStyle(fontSize: 12)),
                  const SizedBox(width: 12),
                  const Icon(Icons.timer_outlined, size: 14),
                  const SizedBox(width: 4),
                  Text(
                    '${item['time_limit'] ?? 0}p',
                    style: const TextStyle(fontSize: 12),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildItemListTile(Map<String, dynamic> item) {
    if (item['type'] == 'folder') {
      return ListTile(
        leading: const Icon(Icons.folder, color: Colors.amber),
        title: Text(
          item['name'],
          style: const TextStyle(fontWeight: FontWeight.bold),
        ),
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            IconButton(
              icon: const Icon(Icons.edit_outlined),
              onPressed: () => _renameItem(item),
            ),
            IconButton(
              icon: const Icon(Icons.drive_file_move_outlined),
              onPressed: () => _moveItem(item),
            ),
            IconButton(
              icon: const Icon(Icons.delete_outline),
              onPressed: () => _deleteItem(item),
            ),
            const Icon(Icons.chevron_right),
          ],
        ),
        onTap: () => setState(() {
          _currentSubPath = p.join(_currentSubPath, item['name']);
          _loadExams();
        }),
      );
    }
    final qCount = (item['questions'] as List?)?.length ?? 0;
    return ListTile(
      leading: const Icon(Icons.description, color: Colors.blue),
      title: Text(item['title'] ?? 'Bài thi'),
      subtitle: Text('$qCount câu hỏi • ${item['time_limit'] ?? 0} phút'),
      trailing: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          IconButton(
            icon: const Icon(Icons.edit_outlined),
            onPressed: () => _renameItem(item),
          ),
          IconButton(
            icon: const Icon(Icons.drive_file_move_outlined),
            onPressed: () => _moveItem(item),
          ),
          IconButton(
            icon: const Icon(Icons.delete_outline, color: Colors.red),
            onPressed: () => _deleteItem(item),
          ),
          IconButton(
            icon: const Icon(Icons.play_circle_outline, color: Colors.green),
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute(
                builder: (context) => TakingExamScreen(examData: item),
              ),
            ),
          ),
        ],
      ),
      onTap: () => Navigator.of(context).push(
        MaterialPageRoute(
          builder: (context) => TakingExamScreen(examData: item),
        ),
      ),
    );
  }
}

class _FileGradingWidget extends StatefulWidget {
  const _FileGradingWidget();

  @override
  State<_FileGradingWidget> createState() => _FileGradingWidgetState();
}

class _FileGradingWidgetState extends State<_FileGradingWidget> {
  String _answerFile = '';
  String _submissionFile = '';
  String _outputDir = '';
  final List<String> _logs = [];
  bool _isRunning = false;
  Map<String, dynamic>? _scoreResult;

  void _runGrade() {
    if (_answerFile.isEmpty || _submissionFile.isEmpty || _outputDir.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Vui lòng chọn đầy đủ các file và thư mục output'),
        ),
      );
      return;
    }

    setState(() {
      _isRunning = true;
      _scoreResult = null;
      _logs.add('\n--- Bắt đầu: Chấm bài ---');
    });

    BackendService().runAction(
      action: 'grade',
      params: {
        'answer-file': _answerFile,
        'submission-file': _submissionFile,
        'output': _outputDir,
      },
      onLog: (msg) => setState(() => _logs.add(msg)),
      onResult: (res) {
        setState(() {
          _isRunning = false;
          if (res['status'] == 'success') {
            _scoreResult = res['score'];
          }
        });
      },
      onError: (err) {
        setState(() {
          _isRunning = false;
          _logs.add('[LỖI] $err');
        });
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          PathSelector(
            label: 'File đáp án (PDF/DOCX)',
            value: _answerFile,
            isDirectory: false,
            allowedExtensions: ['pdf', 'docx'],
            onSelected: (val) => setState(() => _answerFile = val),
          ),
          const SizedBox(height: 16),
          PathSelector(
            label: 'File bài làm (PDF/DOCX)',
            value: _submissionFile,
            isDirectory: false,
            allowedExtensions: ['pdf', 'docx'],
            onSelected: (val) => setState(() => _submissionFile = val),
          ),
          const SizedBox(height: 16),
          PathSelector(
            label: 'Thư mục Output',
            value: _outputDir,
            onSelected: (val) => setState(() => _outputDir = val),
          ),
          const SizedBox(height: 32),
          Expanded(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  flex: 2,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      FilledButton.icon(
                        onPressed: _isRunning ? null : _runGrade,
                        icon: _isRunning
                            ? const SizedBox(
                                width: 18,
                                height: 18,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                ),
                              )
                            : const Icon(Icons.grading),
                        label: const Text('Bắt đầu Chấm bài'),
                        style: FilledButton.styleFrom(
                          minimumSize: const Size(200, 50),
                        ),
                      ),
                      const SizedBox(height: 24),
                      Expanded(child: LogConsole(logs: _logs)),
                    ],
                  ),
                ),
                if (_scoreResult != null) ...[
                  const SizedBox(width: 24),
                  Expanded(
                    flex: 1,
                    child: Card(
                      elevation: 4,
                      color: Theme.of(context).colorScheme.primaryContainer,
                      child: Padding(
                        padding: const EdgeInsets.all(24.0),
                        child: Column(
                          children: [
                            Text(
                              'BẢNG ĐIỂM',
                              style: Theme.of(context).textTheme.titleLarge,
                            ),
                            const SizedBox(height: 24),
                            _buildScoreRow(
                              'Số câu đúng',
                              '${_scoreResult!['correct']}',
                              Colors.green,
                            ),
                            _buildScoreRow(
                              'Số câu sai',
                              '${_scoreResult!['wrong']}',
                              Colors.red,
                            ),
                            _buildScoreRow(
                              'Tổng số câu',
                              '${_scoreResult!['total']}',
                              Colors.blue,
                            ),
                            const Divider(height: 40),
                            Text(
                              '${((_scoreResult!['correct'] / _scoreResult!['total']) * 10).toStringAsFixed(2)} / 10',
                              style: Theme.of(context).textTheme.displaySmall
                                  ?.copyWith(fontWeight: FontWeight.bold),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildScoreRow(String label, String value, Color color) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label),
          Text(
            value,
            style: TextStyle(
              fontWeight: FontWeight.bold,
              fontSize: 18,
              color: color,
            ),
          ),
        ],
      ),
    );
  }
}

class _HistoryTab extends StatefulWidget {
  const _HistoryTab();

  @override
  State<_HistoryTab> createState() => _HistoryTabState();
}

class _HistoryTabState extends State<_HistoryTab> {
  List<Map<String, dynamic>> _history = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadHistory();
  }

  Future<void> _loadHistory() async {
    setState(() => _isLoading = true);
    try {
      final db = await DatabaseService.getInstance();
      final data = await db.getHistory();
      setState(() {
        _history = data;
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) return const Center(child: CircularProgressIndicator());

    if (_history.isEmpty) {
      return const Center(child: Text('Chưa có lịch sử làm bài.'));
    }

    // Grouping logic
    final Map<String, List<Map<String, dynamic>>> grouped = {};
    for (var item in _history) {
      final folder = item['folder']?.toString().trim();
      final key = (folder == null || folder.isEmpty) ? 'Khác' : folder;
      if (!grouped.containsKey(key)) grouped[key] = [];
      grouped[key]!.add(item);
    }

    final sortedKeys = grouped.keys.toList()..sort((a, b) {
      if (a == 'Khác') return 1;
      if (b == 'Khác') return -1;
      return a.compareTo(b);
    });

    return Padding(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Lịch sử làm bài',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              IconButton(
                onPressed: _loadHistory,
                icon: const Icon(Icons.refresh),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Expanded(
            child: ListView.builder(
              itemCount: sortedKeys.length,
              itemBuilder: (context, folderIndex) {
                final folderName = sortedKeys[folderIndex];
                final items = grouped[folderName]!;

                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 16.0),
                      child: Row(
                        children: [
                          Icon(
                            folderName == 'Khác' ? Icons.category : Icons.folder_open,
                            size: 20,
                            color: Theme.of(context).colorScheme.primary,
                          ),
                          const SizedBox(width: 8),
                          Text(
                            folderName,
                            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                                  fontWeight: FontWeight.bold,
                                  color: Theme.of(context).colorScheme.primary,
                                ),
                          ),
                          const SizedBox(width: 8),
                          Text(
                            '(${items.length} lần)',
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                        ],
                      ),
                    ),
                    ...items.map((item) {
                      final score = item['score_correct'] as int;
                      final total = item['score_total'] as int;
                      final percent = (score / total * 100).toStringAsFixed(1);
                      final date = DateTime.parse(item['timestamp']);

                      return Card(
                        margin: const EdgeInsets.only(bottom: 8, left: 16),
                        child: ListTile(
                          leading: CircleAvatar(
                            backgroundColor: score / total >= 0.5
                                ? Colors.green
                                : Colors.red,
                            child: Text(
                              '$percent%',
                              style: const TextStyle(
                                fontSize: 10,
                                color: Colors.white,
                              ),
                            ),
                          ),
                          title: Text(item['exam_title'] ?? 'Bài thi'),
                          subtitle: Text(
                            'Đúng: $score/$total | Ngày: ${date.day}/${date.month}/${date.year} ${date.hour}:${date.minute}',
                          ),
                          trailing: const Icon(Icons.chevron_right),
                          onTap: () async {
                            try {
                              final answers = jsonDecode(item['answers_json'] ?? '{}')
                                  as Map<String, dynamic>;
                              final userAnswers = answers.map(
                                (k, v) => MapEntry(int.parse(k), v.toString()),
                              );

                              final settings = await SettingsService.getInstance();
                              final examsDir = Directory(settings.examsPath);
                              final examFiles = examsDir
                                  .listSync(recursive: true)
                                  .whereType<File>()
                                  .where((f) => f.path.endsWith('.json'));

                              File? examFile;
                              for (var f in examFiles) {
                                try {
                                  final content = await f.readAsString();
                                  final data = jsonDecode(content);
                                  if (data['id'] == item['exam_id']) {
                                    examFile = f;
                                    break;
                                  }
                                } catch (e) {}
                              }

                              if (examFile != null && mounted) {
                                final examData = jsonDecode(
                                  await examFile.readAsString(),
                                );
                                Navigator.of(context).push(
                                  MaterialPageRoute(
                                    builder: (context) => QuizResultScreen(
                                      examData: examData,
                                      userAnswers: userAnswers,
                                    ),
                                  ),
                                );
                              } else if (mounted) {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  const SnackBar(
                                    content: Text(
                                      'Không tìm thấy file đề gốc để hiển thị chi tiết.',
                                    ),
                                  ),
                                );
                              }
                            } catch (e) {
                              if (mounted) {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  SnackBar(content: Text('Lỗi khi mở chi tiết: $e')),
                                );
                              }
                            }
                          },
                        ),
                      );
                    }).toList(),
                  ],
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
