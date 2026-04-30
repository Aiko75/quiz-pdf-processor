import 'package:flutter/material.dart';

class QuizResultScreen extends StatelessWidget {
  final Map<String, dynamic> examData;
  final Map<int, String> userAnswers;

  const QuizResultScreen({
    super.key,
    required this.examData,
    required this.userAnswers,
  });

  @override
  Widget build(BuildContext context) {
    final List<dynamic> questions = examData['questions'] ?? [];
    int correctCount = 0;
    int wrongCount = 0;
    int unansweredCount = 0;

    for (var q in questions) {
      final qId = q['id'];
      final correct = q['correct_answer'];
      final selected = userAnswers[qId];

      if (selected == null) {
        unansweredCount++;
      } else if (selected == correct) {
        correctCount++;
      } else {
        wrongCount++;
      }
    }

    final score = questions.isEmpty ? 0.0 : (correctCount / questions.length) * 10;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Kết quả Bài thi'),
        leading: IconButton(
          icon: const Icon(Icons.close),
          onPressed: () => Navigator.of(context).pop(), // Return to ExamListScreen
        ),
      ),
      body: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Left Sidebar: Score Summary
          Container(
            width: 300,
            color: Theme.of(context).colorScheme.surfaceContainerLow,
            padding: const EdgeInsets.all(24.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text('TỔNG ĐIỂM', style: Theme.of(context).textTheme.titleMedium, textAlign: TextAlign.center),
                const SizedBox(height: 16),
                Text(
                  '${score.toStringAsFixed(2)} / 10',
                  style: Theme.of(context).textTheme.displayMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: score >= 5 ? Colors.green : Colors.red,
                  ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 32),
                _buildStatRow('Số câu đúng', correctCount, Colors.green),
                const SizedBox(height: 12),
                _buildStatRow('Số câu sai', wrongCount, Colors.red),
                const SizedBox(height: 12),
                _buildStatRow('Chưa làm', unansweredCount, Colors.orange),
                const SizedBox(height: 12),
                _buildStatRow('Tổng số câu', questions.length, Colors.blue),
                const Spacer(),
                FilledButton.icon(
                  onPressed: () => Navigator.of(context).pop(),
                  icon: const Icon(Icons.arrow_back),
                  label: const Text('Quay lại danh sách'),
                )
              ],
            ),
          ),
          
          // Main Content: Detailed Review
          Expanded(
            child: ListView.separated(
              padding: const EdgeInsets.all(32.0),
              itemCount: questions.length,
              separatorBuilder: (_, __) => const Divider(height: 64),
              itemBuilder: (context, index) {
                final q = questions[index];
                final qId = q['id'];
                final correct = q['correct_answer'];
                final selected = userAnswers[qId];
                final isCorrect = selected == correct;
                final isUnanswered = selected == null;

                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        if (isCorrect)
                          const Icon(Icons.check_circle, color: Colors.green)
                        else if (isUnanswered)
                          const Icon(Icons.remove_circle, color: Colors.orange)
                        else
                          const Icon(Icons.cancel, color: Colors.red),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            'Câu ${index + 1}: ${q['question']}',
                            style: Theme.of(context).textTheme.titleLarge,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    ...((q['options'] as Map<String, dynamic>? ?? {}).entries.map((entry) {
                      final label = entry.key;
                      final text = entry.value;
                      
                      Color? bgColor;
                      Color? borderColor = Theme.of(context).dividerColor;
                      
                      if (label == correct) {
                        bgColor = Colors.green.withOpacity(0.2);
                        borderColor = Colors.green;
                      } else if (label == selected && !isCorrect) {
                        bgColor = Colors.red.withOpacity(0.2);
                        borderColor = Colors.red;
                      }
                      
                      return Padding(
                        padding: const EdgeInsets.only(bottom: 8.0, left: 32.0),
                        child: Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            border: Border.all(color: borderColor),
                            borderRadius: BorderRadius.circular(8),
                            color: bgColor,
                          ),
                          child: Row(
                            children: [
                              Text(
                                '$label.',
                                style: TextStyle(
                                  fontWeight: FontWeight.bold,
                                  color: (label == correct || label == selected) ? borderColor : null,
                                ),
                              ),
                              const SizedBox(width: 8),
                              Expanded(child: Text(text)),
                              if (label == correct)
                                const Icon(Icons.check, color: Colors.green, size: 16)
                              else if (label == selected && !isCorrect)
                                const Icon(Icons.close, color: Colors.red, size: 16)
                            ],
                          ),
                        ),
                      );
                    }).toList()),
                  ],
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatRow(String label, int count, Color color) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: const TextStyle(fontSize: 16)),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
          decoration: BoxDecoration(
            color: color.withOpacity(0.2),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Text(
            count.toString(),
            style: TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 16),
          ),
        )
      ],
    );
  }
}
