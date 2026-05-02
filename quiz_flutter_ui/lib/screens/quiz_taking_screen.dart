import 'package:flutter/material.dart';
import 'dart:async';
import 'dart:math';
import 'dart:convert';
import 'dart:io';
import 'package:path/path.dart' as p;
import '../services/settings_service.dart';
import '../services/database_service.dart';
import 'package:flutter/services.dart';
import 'quiz_result_screen.dart';

class TakingExamScreen extends StatefulWidget {
  final Map<String, dynamic> examData;
  final bool practiceMode;

  const TakingExamScreen({
    super.key,
    required this.examData,
    this.practiceMode = false,
  });

  @override
  State<TakingExamScreen> createState() => _TakingExamScreenState();
}

class _TakingExamScreenState extends State<TakingExamScreen> {
  int _currentIndex = 0;
  final Map<int, String> _selectedAnswers = {};
  final Set<int> _flaggedQuestions = {};
  Timer? _timer;
  int _timeRemainingSeconds = 0;
  int _totalSecondsSpent = 0;
  late List<dynamic> _questions;
  bool _questionsInitialized = false;
  bool _autoAdvance = false;
  bool _shortcutsEnabled = true;
  final FocusNode _focusNode = FocusNode();

  int get _timeLimitMinutes => widget.examData['time_limit'] ?? 0;

  @override
  void initState() {
    super.initState();
    _initQuestions();
  }

  Future<void> _initQuestions() async {
    final settings = await SettingsService.getInstance();
    final rawQuestions = List<dynamic>.from(widget.examData['questions'] ?? []);

    // Check for auto-save first
    final saveFile = File(
      p.join(settings.workspacePath, 'current_session.json'),
    );
    Map<String, dynamic>? savedState;
    if (await saveFile.exists()) {
      try {
        savedState = jsonDecode(await saveFile.readAsString());
        if (savedState?['exam_id'] != widget.examData['id']) {
          savedState = null;
        }
      } catch (e) {
        savedState = null;
      }
    }

    if (savedState != null && mounted) {
      final resume = await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Tiếp tục bài thi?'),
          content: const Text(
            'Hệ thống tìm thấy bài thi đang làm dở của đề này. Bạn có muốn tiếp tục không?',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Làm mới'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('Tiếp tục'),
            ),
          ],
        ),
      );

      setState(() {
        _autoAdvance = settings.autoAdvanceQuiz;
        _shortcutsEnabled = settings.quizShortcutsEnabled;
      });

      if (resume == true) {
        setState(() {
          _questions = List<dynamic>.from(
            savedState?['questions'] ?? rawQuestions,
          );
          (savedState?['selected_answers'] as Map<String, dynamic>).forEach((
            k,
            v,
          ) {
            _selectedAnswers[int.parse(k)] = v;
          });
          for (var id in (savedState?['flagged_questions'] as List<dynamic>)) {
            _flaggedQuestions.add(id);
          }
          _currentIndex = savedState?['current_index'] ?? 0;
          _timeRemainingSeconds = savedState?['time_remaining'] ?? 0;
          _totalSecondsSpent = savedState?['total_spent'] ?? 0;
          _questionsInitialized = true;
        });
        _startTimer();
      } else {
        await saveFile.delete();
      }
      return;
    }

    setState(() {
      _autoAdvance = settings.autoAdvanceQuiz;
      _shortcutsEnabled = settings.quizShortcutsEnabled;
    });

    if (settings.shuffleEnabled) {
      rawQuestions.shuffle(Random());
    }
    setState(() {
      _questions = rawQuestions;
      _questionsInitialized = true;
    });

    final tl = widget.examData['time_limit'] ?? 0;
    if (tl > 0 && !widget.practiceMode) {
      _timeRemainingSeconds = tl * 60;
    }
    _startTimer();
    _focusNode.requestFocus();
  }

  void _startTimer() {
    _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      setState(() {
        _totalSecondsSpent++;
        if (_timeRemainingSeconds > 0 && !widget.practiceMode) {
          _timeRemainingSeconds--;
          if (_timeRemainingSeconds == 0) {
            _timer?.cancel();
            _submitExam();
          }
        }
      });
      _autoSave();
    });
  }

  Future<void> _autoSave() async {
    try {
      final settings = await SettingsService.getInstance();
      final saveFile = File(
        p.join(settings.workspacePath, 'current_session.json'),
      );
      final state = {
        'exam_id': widget.examData['id'],
        'questions': _questions,
        'selected_answers': _selectedAnswers.map(
          (k, v) => MapEntry(k.toString(), v),
        ),
        'flagged_questions': _flaggedQuestions.toList(),
        'current_index': _currentIndex,
        'time_remaining': _timeRemainingSeconds,
        'total_spent': _totalSecondsSpent,
        'timestamp': DateTime.now().toIso8601String(),
      };
      await saveFile.writeAsString(jsonEncode(state));
    } catch (e) {}
  }

  Future<void> _clearAutoSave() async {
    try {
      final settings = await SettingsService.getInstance();
      final saveFile = File(
        p.join(settings.workspacePath, 'current_session.json'),
      );
      if (await saveFile.exists()) await saveFile.delete();
    } catch (e) {}
  }

  @override
  void dispose() {
    _timer?.cancel();
    _focusNode.dispose();
    super.dispose();
  }

  void _submitExam() async {
    _timer?.cancel();
    await _clearAutoSave();

    int correctCount = 0;
    for (var q in _questions) {
      if (_selectedAnswers[q['id']] == q['correct_answer']) {
        correctCount++;
      }
    }

    try {
      final db = await DatabaseService.getInstance();
      await db.saveAttempt(
        examId: widget.examData['id'],
        examTitle: widget.examData['title'],
        folder: widget.examData['folder'],
        scoreCorrect: correctCount,
        scoreTotal: _questions.length,
        timeSpentSeconds: _totalSecondsSpent,
        answersJson: jsonEncode(
          _selectedAnswers.map((k, v) => MapEntry(k.toString(), v)),
        ),
      );
    } catch (e) {}

    if (mounted) {
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(
          builder: (context) => QuizResultScreen(
            examData: widget.examData,
            userAnswers: _selectedAnswers,
          ),
        ),
      );
    }
  }

  void _confirmSubmit() {
    showDialog(
      context: context,
      builder: (context) => _ConfirmSubmitDialog(
        answeredCount: _selectedAnswers.length,
        totalCount: _questions.length,
        onConfirm: () {
          Navigator.pop(context);
          _submitExam();
        },
      ),
    );
  }

  String _formatTime(int seconds) {
    int m = seconds ~/ 60;
    int s = seconds % 60;
    return '${m.toString().padLeft(2, '0')}:${s.toString().padLeft(2, '0')}';
  }

  void _selectAnswer(String label) {
    final qId = _questions[_currentIndex]['id'];
    setState(() {
      _selectedAnswers[qId] = label;
    });
    _autoSave();

    if (_autoAdvance && _currentIndex < _questions.length - 1) {
      Future.delayed(const Duration(milliseconds: 300), () {
        if (mounted) setState(() => _currentIndex++);
      });
    }
  }

  void _handleKeyEvent(KeyEvent event) {
    if (!_shortcutsEnabled || event is! KeyDownEvent) return;

    final key = event.logicalKey;

    // Navigation
    if (key == LogicalKeyboardKey.arrowLeft && _currentIndex > 0) {
      setState(() => _currentIndex--);
    } else if (key == LogicalKeyboardKey.arrowRight &&
        _currentIndex < _questions.length - 1) {
      setState(() => _currentIndex++);
    } else if (key == LogicalKeyboardKey.enter ||
        key == LogicalKeyboardKey.numpadEnter) {
      if (_currentIndex < _questions.length - 1) {
        setState(() => _currentIndex++);
      } else {
        _confirmSubmit();
      }
    }

    // Answers
    String? answerLabel;
    if (key == LogicalKeyboardKey.digit1 ||
        key == LogicalKeyboardKey.keyA ||
        key == LogicalKeyboardKey.numpad1) {
      answerLabel = 'A';
    } else if (key == LogicalKeyboardKey.digit2 ||
        key == LogicalKeyboardKey.keyB ||
        key == LogicalKeyboardKey.numpad2)
      answerLabel = 'B';
    else if (key == LogicalKeyboardKey.digit3 ||
        key == LogicalKeyboardKey.keyC ||
        key == LogicalKeyboardKey.numpad3)
      answerLabel = 'C';
    else if (key == LogicalKeyboardKey.digit4 ||
        key == LogicalKeyboardKey.keyD ||
        key == LogicalKeyboardKey.numpad4)
      answerLabel = 'D';
    else if (key == LogicalKeyboardKey.digit5 ||
        key == LogicalKeyboardKey.keyE ||
        key == LogicalKeyboardKey.numpad5)
      answerLabel = 'E';
    // Support 0-3 as requested by user if they prefer 0-indexed
    else if (key == LogicalKeyboardKey.digit0 ||
        key == LogicalKeyboardKey.numpad0)
      answerLabel = 'A';

    if (answerLabel != null) {
      _selectAnswer(answerLabel);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!_questionsInitialized || _questions.isEmpty) {
      return Scaffold(
        appBar: AppBar(title: Text(widget.examData['title'] ?? 'Bài thi')),
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    final currentQuestion = _questions[_currentIndex];

    return KeyboardListener(
      focusNode: _focusNode,
      onKeyEvent: _handleKeyEvent,
      child: Scaffold(
        appBar: AppBar(
          title: Text(widget.examData['title'] ?? 'Bài thi trực tuyến'),
          actions: [
            if (_timeLimitMinutes > 0 && !widget.practiceMode)
              Center(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16.0),
                  child: Text(
                    _formatTime(_timeRemainingSeconds),
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      color: _timeRemainingSeconds < 60 ? Colors.red : null,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ),
            Padding(
              padding: const EdgeInsets.all(8.0),
              child: FilledButton.icon(
                onPressed: _confirmSubmit,
                icon: const Icon(Icons.check_circle_outline),
                label: const Text('Nộp bài'),
                style: FilledButton.styleFrom(backgroundColor: Colors.green),
              ),
            ),
          ],
        ),
        body: Row(
          children: [
            // Left Sidebar
            Container(
              width: 300,
              color: Theme.of(context).colorScheme.surfaceContainerLow,
              child: Column(
                children: [
                  Padding(
                    padding: const EdgeInsets.all(16.0),
                    child: Text(
                      'Tiến độ: ${_selectedAnswers.length}/${_questions.length}',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                  ),
                  const Divider(),
                  Expanded(
                    child: GridView.builder(
                      padding: const EdgeInsets.all(16.0),
                      gridDelegate:
                          const SliverGridDelegateWithFixedCrossAxisCount(
                            crossAxisCount: 5,
                            mainAxisSpacing: 8,
                            crossAxisSpacing: 8,
                          ),
                      itemCount: _questions.length,
                      itemBuilder: (context, index) {
                        final qId = _questions[index]['id'];
                        final isAnswered = _selectedAnswers.containsKey(qId);
                        final isCurrent = index == _currentIndex;
                        final isFlagged = _flaggedQuestions.contains(qId);

                        return InkWell(
                          onTap: () => setState(() => _currentIndex = index),
                          child: Container(
                            decoration: BoxDecoration(
                              color: isCurrent
                                  ? Theme.of(
                                      context,
                                    ).colorScheme.primaryContainer
                                  : isAnswered
                                  ? Colors.green.withOpacity(0.2)
                                  : Theme.of(
                                      context,
                                    ).colorScheme.surfaceContainerHighest,
                              border: Border.all(
                                color: isCurrent
                                    ? Theme.of(context).colorScheme.primary
                                    : Colors.transparent,
                                width: 2,
                              ),
                              borderRadius: BorderRadius.circular(8),
                            ),
                            alignment: Alignment.center,
                            child: Stack(
                              children: [
                                Center(
                                  child: Text(
                                    '${index + 1}',
                                    style: TextStyle(
                                      fontWeight: isCurrent
                                          ? FontWeight.bold
                                          : FontWeight.normal,
                                      color: isCurrent
                                          ? Theme.of(
                                              context,
                                            ).colorScheme.onPrimaryContainer
                                          : null,
                                    ),
                                  ),
                                ),
                                if (isFlagged)
                                  const Positioned(
                                    top: 2,
                                    right: 2,
                                    child: Icon(
                                      Icons.flag,
                                      size: 12,
                                      color: Colors.orange,
                                    ),
                                  ),
                              ],
                            ),
                          ),
                        );
                      },
                    ),
                  ),
                ],
              ),
            ),

            Expanded(
              child: Padding(
                padding: const EdgeInsets.all(32.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          'Câu ${_currentIndex + 1}:',
                          style: Theme.of(context).textTheme.headlineSmall,
                        ),
                        IconButton.filledTonal(
                          onPressed: () {
                            setState(() {
                              final qId = currentQuestion['id'];
                              if (_flaggedQuestions.contains(qId)) {
                                _flaggedQuestions.remove(qId);
                              } else {
                                _flaggedQuestions.add(qId);
                              }
                            });
                            _autoSave();
                          },
                          icon: Icon(
                            _flaggedQuestions.contains(currentQuestion['id'])
                                ? Icons.flag
                                : Icons.flag_outlined,
                            color:
                                _flaggedQuestions.contains(
                                  currentQuestion['id'],
                                )
                                ? Colors.orange
                                : null,
                          ),
                          tooltip: 'Gắn cờ câu hỏi này',
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    Text(
                      currentQuestion['question'] ?? '',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 32),
                    ...((currentQuestion['options'] as Map<String, dynamic>? ??
                            {})
                        .entries
                        .map((entry) {
                          final label = entry.key;
                          final text = entry.value;
                          final isSelected =
                              _selectedAnswers[currentQuestion['id']] == label;

                          return Padding(
                            padding: const EdgeInsets.only(bottom: 12.0),
                            child: InkWell(
                              onTap: () => _selectAnswer(label),
                              borderRadius: BorderRadius.circular(12),
                              child: Container(
                                padding: const EdgeInsets.all(16),
                                decoration: BoxDecoration(
                                  border: Border.all(
                                    color: isSelected
                                        ? Theme.of(context).colorScheme.primary
                                        : Theme.of(context).dividerColor,
                                    width: isSelected ? 2 : 1,
                                  ),
                                  borderRadius: BorderRadius.circular(12),
                                  color: isSelected
                                      ? Theme.of(context)
                                            .colorScheme
                                            .primaryContainer
                                            .withOpacity(0.5)
                                      : null,
                                ),
                                child: Row(
                                  children: [
                                    Radio<String>(
                                      value: label,
                                      groupValue:
                                          _selectedAnswers[currentQuestion['id']],
                                      onChanged: (val) {
                                        if (val != null) _selectAnswer(val);
                                      },
                                    ),
                                    const SizedBox(width: 8),
                                    Expanded(
                                      child: Text(
                                        '$label. $text',
                                        style: Theme.of(
                                          context,
                                        ).textTheme.titleMedium,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          );
                        })
                        .toList()),
                    const Spacer(),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        FilledButton.tonalIcon(
                          onPressed: _currentIndex > 0
                              ? () => setState(() => _currentIndex--)
                              : null,
                          icon: const Icon(Icons.arrow_back),
                          label: const Text('Câu trước'),
                        ),
                        if (_currentIndex < _questions.length - 1)
                          FilledButton.icon(
                            onPressed: () => setState(() => _currentIndex++),
                            icon: const Icon(Icons.arrow_forward),
                            label: const Text('Câu tiếp'),
                          )
                        else
                          FilledButton.icon(
                            onPressed: _confirmSubmit,
                            icon: const Icon(Icons.check),
                            label: const Text('Nộp bài ngay'),
                            style: FilledButton.styleFrom(
                              backgroundColor: Colors.green,
                            ),
                          ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ConfirmSubmitDialog extends StatefulWidget {
  final int answeredCount;
  final int totalCount;
  final VoidCallback onConfirm;

  const _ConfirmSubmitDialog({
    required this.answeredCount,
    required this.totalCount,
    required this.onConfirm,
  });

  @override
  State<_ConfirmSubmitDialog> createState() => _ConfirmSubmitDialogState();
}

class _ConfirmSubmitDialogState extends State<_ConfirmSubmitDialog> {
  int _selectedIndex = 1; // 0 for Cancel, 1 for Submit (default)
  final FocusNode _focusNode = FocusNode();

  @override
  void initState() {
    super.initState();
    _focusNode.requestFocus();
  }

  @override
  void dispose() {
    _focusNode.dispose();
    super.dispose();
  }

  void _handleKey(KeyEvent event) {
    if (event is! KeyDownEvent) return;
    if (event.logicalKey == LogicalKeyboardKey.arrowLeft ||
        event.logicalKey == LogicalKeyboardKey.arrowRight) {
      setState(() {
        _selectedIndex = 1 - _selectedIndex;
      });
    } else if (event.logicalKey == LogicalKeyboardKey.enter ||
        event.logicalKey == LogicalKeyboardKey.numpadEnter) {
      if (_selectedIndex == 1) {
        widget.onConfirm();
      } else {
        Navigator.pop(context);
      }
    } else if (event.logicalKey == LogicalKeyboardKey.escape) {
      Navigator.pop(context);
    }
  }

  @override
  Widget build(BuildContext context) {
    return KeyboardListener(
      focusNode: _focusNode,
      onKeyEvent: _handleKey,
      child: AlertDialog(
        title: const Text('Nộp bài'),
        content: Text(
          'Bạn đã trả lời ${widget.answeredCount}/${widget.totalCount} câu. Bạn có chắc chắn muốn nộp bài?',
        ),
        actions: [
          OutlinedButton(
            onPressed: () => Navigator.pop(context),
            style: OutlinedButton.styleFrom(
              side: _selectedIndex == 0
                  ? BorderSide(
                      color: Theme.of(context).colorScheme.primary,
                      width: 2,
                    )
                  : null,
            ),
            child: const Text('Hủy'),
          ),
          FilledButton(
            onPressed: widget.onConfirm,
            style: FilledButton.styleFrom(
              backgroundColor: _selectedIndex == 1 ? Colors.green : Colors.grey,
              side: _selectedIndex == 1
                  ? const BorderSide(color: Colors.white, width: 2)
                  : null,
            ),
            child: const Text('Nộp bài'),
          ),
        ],
      ),
    );
  }
}
