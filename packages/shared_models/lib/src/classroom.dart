/// Educator domain models (Phase 17/20).
///
/// Shapes mirror the backend classes contract: `GET /classes` returns the
/// caller's classes with their membership role, `GET /classes/{id}` adds
/// the member roster and assignments, `POST /classes/{id}/join` answers a
/// membership row, and the progress endpoints return per-assignment,
/// per-student completion.
library;

/// One membership row: a user with a role inside a class.
class ClassMember {
  const ClassMember({
    required this.userId,
    this.role = 'student',
    this.displayName,
    this.joinedAt,
  });

  final String userId;

  /// `teacher` | `student`.
  final String role;

  /// The member's profile display name, when known.
  final String? displayName;

  /// When the member joined.
  final DateTime? joinedAt;

  /// Whether this member teaches the class.
  bool get isTeacher => role == 'teacher';

  factory ClassMember.fromJson(Map<String, dynamic> json) {
    final userId = json['user_id'];
    if (userId is! String || userId.isEmpty) {
      throw const FormatException('ClassMember requires a user_id');
    }
    final joinedAt = json['joined_at'];
    return ClassMember(
      userId: userId,
      role: json['role'] as String? ?? 'student',
      displayName: json['display_name'] as String?,
      joinedAt: joinedAt == null ? null : DateTime.parse(joinedAt as String),
    );
  }

  Map<String, dynamic> toJson() => {
        'user_id': userId,
        'role': role,
        'display_name': displayName,
        'joined_at': joinedAt?.toIso8601String(),
      };
}

/// A lesson assigned to a class, with completion statistics.
class Assignment {
  const Assignment({
    required this.id,
    required this.classId,
    required this.lessonId,
    this.lessonSlug = '',
    this.lessonTitle = '',
    this.dueAt,
    this.createdAt,
    this.completedCount = 0,
    this.memberCount = 0,
  });

  final String id;
  final String classId;
  final String lessonId;

  /// The assigned lesson's stable slug (title fallback).
  final String lessonSlug;

  /// The assigned lesson's localized title.
  final String lessonTitle;

  /// Optional deadline.
  final DateTime? dueAt;

  final DateTime? createdAt;

  /// Number of members who completed the lesson.
  final int completedCount;

  /// Total members in the class.
  final int memberCount;

  factory Assignment.fromJson(Map<String, dynamic> json) {
    final id = json['id'];
    final classId = json['class_id'];
    final lessonId = json['lesson_id'];
    if (id is! String || id.isEmpty) {
      throw const FormatException('Assignment requires an id');
    }
    if (classId is! String || classId.isEmpty) {
      throw const FormatException('Assignment requires a class_id');
    }
    if (lessonId is! String || lessonId.isEmpty) {
      throw const FormatException('Assignment requires a lesson_id');
    }
    final dueAt = json['due_at'];
    final createdAt = json['created_at'];
    return Assignment(
      id: id,
      classId: classId,
      lessonId: lessonId,
      lessonSlug: json['lesson_slug'] as String? ?? '',
      lessonTitle: json['lesson_title'] as String? ?? '',
      dueAt: dueAt == null ? null : DateTime.parse(dueAt as String),
      createdAt: createdAt == null ? null : DateTime.parse(createdAt as String),
      completedCount: (json['completed_count'] as num?)?.toInt() ?? 0,
      memberCount: (json['member_count'] as num?)?.toInt() ?? 0,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'class_id': classId,
        'lesson_id': lessonId,
        'lesson_slug': lessonSlug,
        'lesson_title': lessonTitle,
        'due_at': dueAt?.toIso8601String(),
        'created_at': createdAt?.toIso8601String(),
        'completed_count': completedCount,
        'member_count': memberCount,
      };
}

/// One student's completion state for one assignment.
class StudentProgress {
  const StudentProgress({
    required this.userId,
    this.displayName,
    this.completed = false,
    this.completedAt,
  });

  final String userId;
  final String? displayName;
  final bool completed;
  final DateTime? completedAt;

  factory StudentProgress.fromJson(Map<String, dynamic> json) {
    final userId = json['user_id'];
    if (userId is! String || userId.isEmpty) {
      throw const FormatException('StudentProgress requires a user_id');
    }
    final completedAt = json['completed_at'];
    return StudentProgress(
      userId: userId,
      displayName: json['display_name'] as String?,
      completed: json['completed'] as bool? ?? false,
      completedAt:
          completedAt == null ? null : DateTime.parse(completedAt as String),
    );
  }

  Map<String, dynamic> toJson() => {
        'user_id': userId,
        'display_name': displayName,
        'completed': completed,
        'completed_at': completedAt?.toIso8601String(),
      };
}

/// An assignment with per-student completion, for teachers.
class AssignmentProgress {
  const AssignmentProgress(
      {required this.assignment, this.students = const []});

  final Assignment assignment;
  final List<StudentProgress> students;

  factory AssignmentProgress.fromJson(Map<String, dynamic> json) {
    final assignment = json['assignment'];
    if (assignment is! Map) {
      throw const FormatException('AssignmentProgress requires an assignment');
    }
    final students = json['students'];
    return AssignmentProgress(
      assignment: Assignment.fromJson(Map<String, dynamic>.from(assignment)),
      students: students is List
          ? students
              .map((item) => StudentProgress.fromJson(
                  Map<String, dynamic>.from(item as Map)))
              .toList()
          : const [],
    );
  }

  Map<String, dynamic> toJson() => {
        'assignment': assignment.toJson(),
        'students': students.map((student) => student.toJson()).toList(),
      };
}

/// A class aggregate with the caller's membership attached.
///
/// The list endpoint returns metadata + the caller's `role`; the detail
/// endpoint additionally carries `members` and `assignments`.
class ClassRoom {
  const ClassRoom({
    required this.id,
    required this.ownerId,
    required this.name,
    this.description = '',
    this.inviteCode = '',
    this.role,
    this.createdAt,
    this.members = const [],
    this.assignments = const [],
  });

  final String id;
  final String ownerId;
  final String name;
  final String description;

  /// The code students use to join.
  final String inviteCode;

  /// The caller's membership role (`teacher` | `student`), or null when
  /// the caller is not a member.
  final String? role;

  final DateTime? createdAt;

  /// Class members (detail payload only).
  final List<ClassMember> members;

  /// Assigned lessons with completion stats (detail payload only).
  final List<Assignment> assignments;

  /// Whether the caller teaches this class.
  bool get isTeacher => role == 'teacher';

  factory ClassRoom.fromJson(Map<String, dynamic> json) {
    final id = json['id'];
    final ownerId = json['owner_id'];
    final name = json['name'];
    if (id is! String || id.isEmpty) {
      throw const FormatException('ClassRoom requires an id');
    }
    if (ownerId is! String || ownerId.isEmpty) {
      throw const FormatException('ClassRoom requires an owner_id');
    }
    if (name is! String || name.isEmpty) {
      throw const FormatException('ClassRoom requires a name');
    }
    final createdAt = json['created_at'];
    final members = json['members'];
    final assignments = json['assignments'];
    return ClassRoom(
      id: id,
      ownerId: ownerId,
      name: name,
      description: json['description'] as String? ?? '',
      inviteCode: json['invite_code'] as String? ?? '',
      role: json['role'] as String?,
      createdAt: createdAt == null ? null : DateTime.parse(createdAt as String),
      members: members is List
          ? members
              .map((item) =>
                  ClassMember.fromJson(Map<String, dynamic>.from(item as Map)))
              .toList()
          : const [],
      assignments: assignments is List
          ? assignments
              .map((item) =>
                  Assignment.fromJson(Map<String, dynamic>.from(item as Map)))
              .toList()
          : const [],
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'owner_id': ownerId,
        'name': name,
        'description': description,
        'invite_code': inviteCode,
        'role': role,
        'created_at': createdAt?.toIso8601String(),
        'members': members.map((member) => member.toJson()).toList(),
        'assignments':
            assignments.map((assignment) => assignment.toJson()).toList(),
      };
}
