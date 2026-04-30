import 'package:flutter/material.dart';
import '../widgets/path_selector.dart';
import '../widgets/log_console.dart';
import '../services/backend_service.dart';

class GradingScreen extends StatefulWidget {
  const GradingScreen({super.key});

  @override
  State<GradingScreen> createState() => _GradingScreenState();
}

class _GradingScreenState extends State<GradingScreen> {
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
          Text('Chấm bài tự động', style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 32),
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
          Row(
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
                          const SizedBox(height: 16),
                          if (_scoreResult!['report'] != null)
                            TextButton.icon(
                              onPressed: () {}, // TODO: Mở file báo cáo
                              icon: const Icon(Icons.open_in_new),
                              label: const Text('Xem báo cáo chi tiết'),
                            ),
                        ],
                      ),
                    ),
                  ),
                ),
              ],
            ],
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
