import 'dart:convert';
import 'package:http/http.dart' as http;

class DashboardService {
  Future<Map<String, dynamic>> getDashboard(String token) async {
    final response = await http.get(
      Uri.parse('http://192.168.100.7:4500/api/dashboard'),
      headers: {'Authorization': 'Bearer $token'},
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to load dashboard');
    }
  }
}


// {
//   "status": "success",
//   "data": {
//     "up_next": {
//       "task_id": "t2",
//       "title": "Upcoming task",
//       "status": "pending",
//       "display_status": "pending",
//       "priority": "high",
//       "day": "Thursday",
//       "time": "3:00 PM",
//       "due_datetime": "2026-06-05T10:00:00.000Z",
//       "is_learning_task": false,
//       "learning_goal_id": null
//     },
//     "daily_progress": {
//       "date": "2026-06-05",
//       "timezone": "Asia/Karachi",
//       "completed_tasks": 1,
//       "total_tasks": 2,
//       "completion_percentage": 50
//     },
//     "learning": [
//       {
//         "learning_goal_id": "g1",
//         "title": "Python roadmap",
//         "roadmap_key": "functions",
//         "status": "active",
//         "progress_percent": 30,
//         "next_topic": {
//           "topic_id": "rt1",
//           "title": "Functions intro",
//           "status": "pending",
//           "day": "Thursday",
//           "time": "7:00 PM",
//           "scheduled_datetime": "2026-06-05T14:00:00.000Z"
//         }
//       }
//     ],
//     "today_schedule": [
//       { "task_id": "t1", "title": "Completed task", "status": "complete", "display_status": "complete", "...": "..." },
//       { "task_id": "t2", "title": "Upcoming task", "status": "pending", "display_status": "pending", "...": "..." }
//     ]
//   }
// }