import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import '../services/database_service.dart';

class AnalyticsScreen extends StatefulWidget {
  const AnalyticsScreen({super.key});

  @override
  State<AnalyticsScreen> createState() => _AnalyticsScreenState();
}

class _AnalyticsScreenState extends State<AnalyticsScreen> {
  bool _isLoading = true;
  Map<String, dynamic> _globalStats = {};
  List<Map<String, dynamic>> _folderStats = [];
  List<Map<String, dynamic>> _weakExams = [];

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() => _isLoading = true);
    final db = await DatabaseService.getInstance();
    final global = await db.getGlobalStats();
    final folders = await db.getStatsByFolder();
    final weak = await db.getWeakExams();

    setState(() {
      _globalStats = global;
      _folderStats = folders;
      _weakExams = weak;
      _isLoading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) return const Center(child: CircularProgressIndicator());

    if (_globalStats['total_attempts'] == 0) {
      return const Center(child: Text('Chưa có dữ liệu để phân tích. Hãy hoàn thành ít nhất một bài thi!'));
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(32.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Phân tích học tập', style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 24),

          // Overview Cards
          Row(
            children: [
              _buildStatCard('Tổng bài thi', _globalStats['total_attempts'].toString(), Icons.assignment),
              const SizedBox(width: 16),
              _buildStatCard('Tỷ lệ đúng', '${((_globalStats['total_correct'] / _globalStats['total_questions']) * 100).toStringAsFixed(1)}%', Icons.check_circle),
              const SizedBox(width: 16),
              _buildStatCard('Thời gian học', '${(_globalStats['total_time'] / 60).toStringAsFixed(0)} phút', Icons.timer),
            ],
          ),

          const SizedBox(height: 32),

          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Subject distribution chart
              Expanded(
                flex: 1,
                child: _buildSectionCard(
                  'Phân bổ theo môn học',
                  SizedBox(
                    height: 300,
                    child: PieChart(
                      PieChartData(
                        sections: _folderStats.map((f) {
                          return PieChartSectionData(
                            value: (f['attempts'] as int).toDouble(),
                            title: f['subject'],
                            radius: 100,
                            titleStyle: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white),
                          );
                        }).toList(),
                      ),
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 32),
              // Performance by subject
              Expanded(
                flex: 1,
                child: _buildSectionCard(
                  'Hiệu suất theo môn',
                  Column(
                    children: _folderStats.map((f) {
                      final percent = f['avg_percent'] as double;
                      return Padding(
                        padding: const EdgeInsets.symmetric(vertical: 8.0),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Text(f['subject']),
                                Text('${percent.toStringAsFixed(1)}%'),
                              ],
                            ),
                            const SizedBox(height: 4),
                            LinearProgressIndicator(
                              value: percent / 100,
                              backgroundColor: Colors.grey.withOpacity(0.2),
                              color: percent > 70 ? Colors.green : (percent > 40 ? Colors.orange : Colors.red),
                            ),
                          ],
                        ),
                      );
                    }).toList(),
                  ),
                ),
              ),
            ],
          ),

          const SizedBox(height: 32),

          // Weak areas
          if (_weakExams.isNotEmpty)
            _buildSectionCard(
              '⚠️ Các đề thi cần cải thiện',
              ListView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: _weakExams.length,
                itemBuilder: (context, index) {
                  final exam = _weakExams[index];
                  return ListTile(
                    leading: const Icon(Icons.warning, color: Colors.orange),
                    title: Text(exam['exam_title']),
                    subtitle: Text('Môn: ${exam['folder'] ?? 'Khác'}'),
                    trailing: Text('${((exam['avg_rate'] as double) * 100).toStringAsFixed(1)}%'),
                  );
                },
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildStatCard(String title, String value, IconData icon) {
    return Expanded(
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            children: [
              Icon(icon, size: 32, color: Theme.of(context).colorScheme.primary),
              const SizedBox(height: 8),
              Text(value, style: Theme.of(context).textTheme.headlineMedium),
              Text(title, style: Theme.of(context).textTheme.bodySmall),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildSectionCard(String title, Widget child) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 24),
            child,
          ],
        ),
      ),
    );
  }
}
