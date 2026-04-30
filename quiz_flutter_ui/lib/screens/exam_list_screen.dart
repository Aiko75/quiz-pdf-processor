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
  List<Map<String, dynamic>> _exams = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadExams();
  }

  Future<void> _loadExams() async {
    setState(() => _isLoading = true);
    try {
      final settings = await SettingsService.getInstance();
      final examsDir = Directory(settings.examsPath);
      if (!await examsDir.exists()) {
        await examsDir.create(recursive: true);
      }

      final List<Map<String, dynamic>> loadedExams = [];
      
      // Load recursive for folders support
      final files = examsDir.listSync(recursive: true).where((f) => f.path.endsWith('.json'));
      
      for (var file in files) {
        try {
          final content = await File(file.path).readAsString();
          final data = jsonDecode(content);
          
          // Get relative path from exams folder to show folder name
          final relativePath = p.relative(file.path, from: settings.examsPath);
          final folderName = p.dirname(relativePath) == '.' ? null : p.dirname(relativePath);

          loadedExams.add({
            'file_path': file.path,
            'folder': folderName,
            ...data,
          });
        } catch (e) {
          // Skip invalid JSON
        }
      }

      // Sort by created_at descending
      loadedExams.sort((a, b) => (b['created_at'] ?? '').compareTo(a['created_at'] ?? ''));

      setState(() {
        _exams = loadedExams;
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  void _deleteExam(String filePath) async {
    try {
      await File(filePath).delete();
      _loadExams();
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Không thể xóa: $e')));
    }
  }

  Future<void> _showImportDialog(BuildContext context) async {
    final pickerResult = await FilePicker.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['docx', 'pdf', 'json'],
    );
    if (pickerResult == null || pickerResult.files.isEmpty) return;
    final filePath = pickerResult.files.single.path!;
    final fileName = pickerResult.files.single.name.replaceAll(RegExp(r'\.[^.]+$'), '');

    final titleController = TextEditingController(text: fileName);
    int timeLimit = 0;

    if (!context.mounted) return;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Nhập đề trắc nghiệm'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: titleController,
              decoration: const InputDecoration(labelText: 'Tên bài thi'),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                const Text('Thời gian (phút, 0 = không giới hạn):'),
                const SizedBox(width: 8),
                SizedBox(
                  width: 60,
                  child: TextField(
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(isDense: true),
                    onChanged: (v) => timeLimit = int.tryParse(v) ?? 0,
                  ),
                )
              ],
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Hủy')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Nhập')),
        ],
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
        'input': filePath,
        'title': titleController.text,
        'time-limit': timeLimit.toString(),
      },
      onLog: (_) {},
      onResult: (res) {
        Navigator.of(context).pop();
        if (res['status'] == 'success') {
          _loadExams();
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Nhập đề thành công!')),
          );
        }
      },
      onError: (err) {
        Navigator.of(context).pop();
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Lỗi: $err')),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_exams.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.quiz_outlined, size: 64, color: Theme.of(context).colorScheme.outline),
            const SizedBox(height: 16),
            Text('Chưa có bài thi nào.', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            const Text('Hãy sang tab "Tạo đề" và chọn "Tạo bài kiểm tra trực tuyến" để bắt đầu.'),
            const SizedBox(height: 24),
            FilledButton.icon(
              onPressed: _loadExams,
              icon: const Icon(Icons.refresh),
              label: const Text('Làm mới'),
            )
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
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('Danh sách Bài thi', style: Theme.of(context).textTheme.headlineSmall),
              Row(
                children: [
                  FilledButton.tonalIcon(
                    onPressed: () => _showImportDialog(context),
                    icon: const Icon(Icons.upload_file),
                    label: const Text('Nhập đề từ file'),
                  ),
                  const SizedBox(width: 8),
                  IconButton(
                    icon: const Icon(Icons.refresh),
                    onPressed: _loadExams,
                    tooltip: 'Làm mới',
                  )
                ],
              )
            ],
          ),
          const SizedBox(height: 24),
          Expanded(
            child: GridView.builder(
              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 3,
                childAspectRatio: 1.5,
                crossAxisSpacing: 16,
                mainAxisSpacing: 16,
              ),
              itemCount: _exams.length,
              itemBuilder: (context, index) {
                final exam = _exams[index];
                final qCount = (exam['questions'] as List?)?.length ?? 0;
                final timeLimit = exam['time_limit'] ?? 0;
                
                return Card(
                  elevation: 2,
                  child: Padding(
                    padding: const EdgeInsets.all(16.0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          exam['title'] ?? 'Bài thi không tên',
                          style: Theme.of(context).textTheme.titleMedium,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                        const SizedBox(height: 8),
                        if (exam['folder'] != null)
                          Padding(
                            padding: const EdgeInsets.only(bottom: 4),
                            child: Chip(
                              label: Text(exam['folder'], style: const TextStyle(fontSize: 10)),
                              visualDensity: VisualDensity.compact,
                              padding: EdgeInsets.zero,
                              materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                            ),
                          ),
                        Text('Số câu: $qCount', style: Theme.of(context).textTheme.bodyMedium),
                        Text('Thời gian: ${timeLimit > 0 ? '$timeLimit phút' : 'Không giới hạn'}', style: Theme.of(context).textTheme.bodyMedium),
                        const Spacer(),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            FilledButton.icon(
                              onPressed: () {
                                Navigator.of(context).push(
                                  MaterialPageRoute(
                                    builder: (context) => TakingExamScreen(examData: exam),
                                  ),
                                ).then((_) => _loadExams());
                              },
                              icon: const Icon(Icons.play_arrow),
                              label: const Text('Làm bài'),
                            ),
                            IconButton(
                              onPressed: () => _deleteExam(exam['file_path']),
                              icon: const Icon(Icons.delete, color: Colors.red),
                              tooltip: 'Xóa bài thi',
                            )
                          ],
                        )
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
        ],
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
        const SnackBar(content: Text('Vui lòng chọn đầy đủ các file và thư mục output')),
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
                        icon: _isRunning ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(Icons.grading),
                        label: const Text('Bắt đầu Chấm bài'),
                        style: FilledButton.styleFrom(minimumSize: const Size(200, 50)),
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
                            Text('BẢNG ĐIỂM', style: Theme.of(context).textTheme.titleLarge),
                            const SizedBox(height: 24),
                            _buildScoreRow('Số câu đúng', '${_scoreResult!['correct']}', Colors.green),
                            _buildScoreRow('Số câu sai', '${_scoreResult!['wrong']}', Colors.red),
                            _buildScoreRow('Tổng số câu', '${_scoreResult!['total']}', Colors.blue),
                            const Divider(height: 40),
                            Text(
                              '${((_scoreResult!['correct'] / _scoreResult!['total']) * 10).toStringAsFixed(2)} / 10',
                              style: Theme.of(context).textTheme.displaySmall?.copyWith(fontWeight: FontWeight.bold),
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
          Text(value, style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18, color: color)),
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

    return Padding(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('Lịch sử làm bài', style: Theme.of(context).textTheme.headlineSmall),
              IconButton(onPressed: _loadHistory, icon: const Icon(Icons.refresh)),
            ],
          ),
          const SizedBox(height: 16),
          Expanded(
            child: ListView.builder(
              itemCount: _history.length,
              itemBuilder: (context, index) {
                final item = _history[index];
                final score = item['score_correct'] as int;
                final total = item['score_total'] as int;
                final percent = (score / total * 100).toStringAsFixed(1);
                final date = DateTime.parse(item['timestamp']);
                
                return Card(
                  margin: const EdgeInsets.only(bottom: 8),
                  child: ListTile(
                    leading: CircleAvatar(
                      backgroundColor: score / total >= 0.5 ? Colors.green : Colors.red,
                      child: Text('$percent%', style: const TextStyle(fontSize: 10, color: Colors.white)),
                    ),
                    title: Text(item['exam_title'] ?? 'Bài thi'),
                    subtitle: Text('Đúng: $score/$total | Ngày: ${date.day}/${date.month}/${date.year} ${date.hour}:${date.minute}'),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () {
                      // Future: View detail results
                    },
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
