import 'package:flutter_test/flutter_test.dart';
import 'package:shared_features/shared_features.dart';
import 'package:shared_models/shared_models.dart';

void main() {
  test('load fetches the classes with their role', () async {
    final api = MockAnalysisApi(delay: Duration.zero);
    final controller = ClassesController(api: api);

    expect(controller.state, ClassesFlowState.idle);
    await controller.load();

    expect(controller.state, ClassesFlowState.loaded);
    expect(controller.classes, hasLength(1));
    expect(controller.classes.first.name, 'Media Literacy 101');
    expect(controller.classes.first.role, 'teacher');
    expect(controller.classes.first.isTeacher, isTrue);
  });

  test('create adds a class and selects it for the invite code', () async {
    final api = MockAnalysisApi(delay: Duration.zero);
    final controller = ClassesController(api: api);
    await controller.load();

    final ok = await controller.create('Journalism Club', 'After school');

    expect(ok, isTrue);
    expect(controller.classes, hasLength(2));
    final created = controller.selected;
    expect(created, isNotNull);
    expect(created!.name, 'Journalism Club');
    expect(created.isTeacher, isTrue);
    expect(created.inviteCode, hasLength(8));
    expect(controller.error, isNull);
  });

  test('join by invite code adds the caller to the class', () async {
    final api = MockAnalysisApi(delay: Duration.zero);
    final controller = ClassesController(api: api);
    await controller.load();
    final seeded = controller.classes.first;

    final ok = await controller.join(seeded.id, 'ANNEX234');

    expect(ok, isTrue);
    expect(controller.selected, isNotNull);
    expect(controller.selected!.id, seeded.id);
    expect(controller.error, isNull);
  });

  test('join rejects a wrong invite code', () async {
    final api = MockAnalysisApi(delay: Duration.zero);
    final controller = ClassesController(api: api);
    await controller.load();
    final seeded = controller.classes.first;

    final ok = await controller.join(seeded.id, 'WRONG234');

    expect(ok, isFalse);
    expect(controller.error, isNotNull);
    expect(controller.selected, isNull);
  });

  test('open loads the roster and assignments for a class', () async {
    final api = MockAnalysisApi(delay: Duration.zero);
    final controller = ClassesController(api: api);
    await controller.load();
    final seeded = controller.classes.first;

    await controller.open(seeded.id);
    await controller.assignLesson('spotting-misinformation');
    controller.closeDetail();
    await controller.open(seeded.id);

    final room = controller.selected;
    expect(room, isNotNull);
    expect(room!.members, hasLength(2));
    expect(room.members.first.isTeacher, isTrue);
    expect(room.assignments, hasLength(1));
    expect(room.assignments.first.lessonSlug, 'spotting-misinformation');
  });

  test('assignLesson adds an assignment and is idempotent', () async {
    final api = MockAnalysisApi(delay: Duration.zero);
    final controller = ClassesController(api: api);
    await controller.load();
    final seeded = controller.classes.first;
    await controller.open(seeded.id);

    final first = await controller.assignLesson('spotting-misinformation');
    final second = await controller.assignLesson('spotting-misinformation');

    expect(first, isTrue);
    expect(second, isTrue);
    final room = controller.selected;
    expect(room!.assignments, hasLength(1));
    expect(room.assignments.first.completedCount, 0);
    expect(room.assignments.first.memberCount, 2);
  });

  test('assignLesson rejects an unknown lesson', () async {
    final api = MockAnalysisApi(delay: Duration.zero);
    final controller = ClassesController(api: api);
    await controller.load();
    await controller.open(controller.classes.first.id);

    final ok = await controller.assignLesson('no-such-lesson');

    expect(ok, isFalse);
    expect(controller.error, isNotNull);
  });

  test('loadProgress derives per-student completion from lessons', () async {
    final api = MockAnalysisApi(delay: Duration.zero);
    final controller = ClassesController(api: api);
    await controller.load();
    await controller.open(controller.classes.first.id);
    await controller.assignLesson('spotting-misinformation');
    // Complete the lesson as the mock student would.
    await controller.loadProgress();

    expect(controller.progress, hasLength(1));
    final item = controller.progress.first;
    expect(item.students, hasLength(1));
    expect(item.students.first.completed, isFalse);
  });

  test('deleteAssignment removes the assignment and refreshes', () async {
    final api = MockAnalysisApi(delay: Duration.zero);
    final controller = ClassesController(api: api);
    await controller.load();
    await controller.open(controller.classes.first.id);
    await controller.assignLesson('spotting-misinformation');
    final assignment = controller.selected!.assignments.first;

    final ok = await controller.deleteAssignment(assignment.id);

    expect(ok, isTrue);
    expect(controller.selected!.assignments, isEmpty);
  });

  test('removeMember removes a student from the roster', () async {
    final api = MockAnalysisApi(delay: Duration.zero);
    final controller = ClassesController(api: api);
    await controller.load();
    await controller.open(controller.classes.first.id);
    final student = controller.selected!.members.firstWhere(
      (member) => !member.isTeacher,
    );

    final ok = await controller.removeMember(student.userId);

    expect(ok, isTrue);
    final members = controller.selected!.members;
    expect(members.any((m) => m.userId == student.userId), isFalse);
    expect(members, hasLength(1));
  });

  test('deleteClass removes the class and returns to the list', () async {
    final api = MockAnalysisApi(delay: Duration.zero);
    final controller = ClassesController(api: api);
    await controller.load();
    await controller.open(controller.classes.first.id);

    final ok = await controller.deleteClass();

    expect(ok, isTrue);
    expect(controller.selected, isNull);
    expect(controller.classes, isEmpty);
  });

  test('open failure records an error and keeps the list', () async {
    final api = MockAnalysisApi(delay: Duration.zero);
    final controller = ClassesController(api: api);
    await controller.load();

    await controller.open('no-such-class');

    expect(controller.error, isNotNull);
    expect(controller.selected, isNull);
    expect(controller.classes, hasLength(1));
  });

  test('load failure transitions to failed state', () async {
    final api = _ThrowingApi();
    final controller = ClassesController(api: api);

    await controller.load();

    expect(controller.state, ClassesFlowState.failed);
    expect(controller.error, isNotNull);
  });

  test('closeDetail clears the selection and progress', () async {
    final api = MockAnalysisApi(delay: Duration.zero);
    final controller = ClassesController(api: api);
    await controller.load();
    await controller.open(controller.classes.first.id);
    await controller.assignLesson('spotting-misinformation');
    await controller.loadProgress();
    expect(controller.progress, isNotEmpty);

    controller.closeDetail();

    expect(controller.selected, isNull);
    expect(controller.progress, isEmpty);
  });
}

/// An API whose classes endpoints always fail.
class _ThrowingApi extends MockAnalysisApi {
  @override
  Future<List<ClassRoom>> fetchClasses() async {
    throw const ApiException('classes.error', 'boom');
  }
}
