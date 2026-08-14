import 'package:shared_models/shared_models.dart';
import 'package:test/test.dart';

void main() {
  group('ClassRoom', () {
    test('round-trips the list payload from the API', () {
      final room = ClassRoom.fromJson(const {
        'id': 'c0000000-0000-4000-8000-000000000001',
        'owner_id': 'u0000000-0000-4000-8000-000000000001',
        'name': 'Media Literacy 101',
        'description': 'First period',
        'invite_code': 'ANNEX234',
        'role': 'teacher',
        'created_at': '2026-08-13T09:00:00Z',
      });

      expect(room.id, 'c0000000-0000-4000-8000-000000000001');
      expect(room.name, 'Media Literacy 101');
      expect(room.inviteCode, 'ANNEX234');
      expect(room.role, 'teacher');
      expect(room.isTeacher, isTrue);
      expect(room.createdAt, DateTime.parse('2026-08-13T09:00:00Z'));
      expect(room.members, isEmpty);
      expect(room.assignments, isEmpty);

      final decoded = ClassRoom.fromJson(room.toJson());
      expect(decoded.name, room.name);
      expect(decoded.role, room.role);
      expect(decoded.toJson()['invite_code'], room.toJson()['invite_code']);
    });

    test('round-trips the detail payload with members and assignments', () {
      final room = ClassRoom.fromJson(const {
        'id': 'c0000000-0000-4000-8000-000000000001',
        'owner_id': 'u0000000-0000-4000-8000-000000000001',
        'name': 'Media Literacy 101',
        'description': '',
        'invite_code': 'ANNEX234',
        'role': 'student',
        'created_at': '2026-08-13T09:00:00Z',
        'members': [
          {
            'user_id': 'u0000000-0000-4000-8000-000000000001',
            'role': 'teacher',
            'display_name': 'Ms. Alvarez',
            'joined_at': '2026-08-13T09:00:00Z',
          },
          {
            'user_id': 'u0000000-0000-4000-8000-000000000002',
            'role': 'student',
            'display_name': 'Student One',
            'joined_at': '2026-08-13T10:00:00Z',
          },
        ],
        'assignments': [
          {
            'id': 'a0000000-0000-4000-8000-000000000001',
            'class_id': 'c0000000-0000-4000-8000-000000000001',
            'lesson_id': 'f0f0f0f0-0000-4000-8000-000000000001',
            'lesson_slug': 'spotting-misinformation',
            'lesson_title': 'Spotting Misinformation',
            'due_at': '2026-08-20T00:00:00Z',
            'created_at': '2026-08-13T11:00:00Z',
            'completed_count': 1,
            'member_count': 2,
          },
        ],
      });

      expect(room.isTeacher, isFalse);
      expect(room.members, hasLength(2));
      expect(room.members.first.isTeacher, isTrue);
      expect(room.members.first.displayName, 'Ms. Alvarez');
      expect(room.assignments, hasLength(1));
      expect(room.assignments.first.lessonTitle, 'Spotting Misinformation');
      expect(room.assignments.first.completedCount, 1);
      expect(room.assignments.first.memberCount, 2);
      expect(
          room.assignments.first.dueAt, DateTime.parse('2026-08-20T00:00:00Z'));

      final decoded = ClassRoom.fromJson(room.toJson());
      expect(decoded.members.length, room.members.length);
      expect(
          decoded.assignments.first.toJson(), room.assignments.first.toJson());
      expect(decoded.toJson(), room.toJson());
    });

    test('rejects a class without an id, owner, or name', () {
      expect(
          () => ClassRoom.fromJson(const {'name': 'x'}), throwsFormatException);
      expect(
        () => ClassRoom.fromJson(const {'id': 'x', 'name': 'x'}),
        throwsFormatException,
      );
      expect(
        () => ClassRoom.fromJson(const {'id': 'x', 'owner_id': 'o'}),
        throwsFormatException,
      );
    });
  });

  group('AssignmentProgress', () {
    test('round-trips the progress payload', () {
      final progress = AssignmentProgress.fromJson(const {
        'assignment': {
          'id': 'a0000000-0000-4000-8000-000000000001',
          'class_id': 'c0000000-0000-4000-8000-000000000001',
          'lesson_id': 'f0f0f0f0-0000-4000-8000-000000000001',
          'lesson_slug': 'spotting-misinformation',
          'lesson_title': 'Spotting Misinformation',
          'due_at': null,
          'created_at': '2026-08-13T11:00:00Z',
          'completed_count': 1,
          'member_count': 2,
        },
        'students': [
          {
            'user_id': 'u0000000-0000-4000-8000-000000000002',
            'display_name': 'Student One',
            'completed': true,
            'completed_at': '2026-08-14T08:00:00Z',
          },
          {
            'user_id': 'u0000000-0000-4000-8000-000000000003',
            'display_name': 'Student Two',
            'completed': false,
            'completed_at': null,
          },
        ],
      });

      expect(progress.assignment.lessonSlug, 'spotting-misinformation');
      expect(progress.students, hasLength(2));
      expect(progress.students.first.completed, isTrue);
      expect(
        progress.students.first.completedAt,
        DateTime.parse('2026-08-14T08:00:00Z'),
      );
      expect(progress.students.last.completed, isFalse);

      final decoded = AssignmentProgress.fromJson(progress.toJson());
      expect(decoded.students.length, progress.students.length);
      expect(decoded.toJson(), progress.toJson());
    });

    test('rejects progress without an assignment', () {
      expect(
        () => AssignmentProgress.fromJson(const {'students': []}),
        throwsFormatException,
      );
    });
  });

  group('ClassMember', () {
    test('round-trips the join payload', () {
      final member = ClassMember.fromJson(const {
        'user_id': 'u0000000-0000-4000-8000-000000000002',
        'role': 'student',
        'display_name': 'Student One',
        'joined_at': '2026-08-13T10:00:00Z',
      });

      expect(member.isTeacher, isFalse);
      expect(member.displayName, 'Student One');
      expect(member.joinedAt, DateTime.parse('2026-08-13T10:00:00Z'));

      final decoded = ClassMember.fromJson(member.toJson());
      expect(decoded.userId, member.userId);
      expect(decoded.toJson(), member.toJson());
    });

    test('rejects a member without a user_id', () {
      expect(() => ClassMember.fromJson(const {}), throwsFormatException);
    });
  });
}
