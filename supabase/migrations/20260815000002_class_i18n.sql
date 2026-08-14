-- =====================================================================
-- ANNEX — Migration 20260815000002: classes UI translations
-- The educator chrome introduced in Phase 20 (tab title, create/join
-- labels, role names, invite-code prompts). Keys follow the typed
-- registry in packages/shared_utils (ADR-0007): en is the fallback root,
-- pt defines a subset and everything else falls back to en.
-- =====================================================================

insert into public.i18n_translations (locale_id, namespace, key, value, plural_rule, version)
select l.id, t.namespace, t.key, t.value, t.plural_rule, 1
from public.i18n_locales l,
     (values
        ('classes', 'title', 'Classes', 'none'),
        ('classes', 'create', 'Create class', 'none'),
        ('classes', 'join', 'Join class', 'none'),
        ('classes', 'invite_code', 'Invite code', 'none'),
        ('classes', 'name', 'Class name', 'none'),
        ('classes', 'description', 'Description', 'none'),
        ('classes', 'members', 'Members', 'none'),
        ('classes', 'assignments', 'Assignments', 'none'),
        ('classes', 'assign_lesson', 'Assign lesson', 'none'),
        ('classes', 'progress', 'Progress', 'none'),
        ('classes', 'role_teacher', 'Teacher', 'none'),
        ('classes', 'role_student', 'Student', 'none'),
        ('classes', 'empty', 'No classes yet. Create one or join with a code.', 'none'),
        ('classes', 'error', 'Could not load classes.', 'none'),
        ('classes', 'completed_count', '{completed}/{total} completed', 'other'),
        ('classes', 'delete_class', 'Delete class', 'none'),
        ('classes', 'remove_member', 'Remove member', 'none'),
        ('classes', 'remove_assignment', 'Remove assignment', 'none'),
        ('classes', 'students', 'Students', 'none'),
        ('classes', 'no_assignments', 'No lessons assigned yet.', 'none'),
        ('classes', 'no_members', 'No students have joined yet.', 'none'),
        ('classes', 'due', 'Due {date}', 'other'),
        ('classes', 'class_id', 'Class ID', 'none'),
        ('classes', 'join_hint', 'Enter the class ID and invite code from your teacher.', 'none'),
        ('classes', 'create_success', 'Class created. Share the invite code with your students.', 'none')
     ) as t (namespace, key, value, plural_rule)
where l.code = 'en'
on conflict (locale_id, namespace, key) do nothing;

insert into public.i18n_translations (locale_id, namespace, key, value, plural_rule, version)
select l.id, t.namespace, t.key, t.value, t.plural_rule, 1
from public.i18n_locales l,
     (values
        ('classes', 'title', 'Turmas', 'none'),
        ('classes', 'create', 'Criar turma', 'none'),
        ('classes', 'join', 'Entrar na turma', 'none'),
        ('classes', 'invite_code', 'Código de convite', 'none'),
        ('classes', 'members', 'Membros', 'none'),
        ('classes', 'assignments', 'Tarefas', 'none'),
        ('classes', 'assign_lesson', 'Atribuir lição', 'none'),
        ('classes', 'progress', 'Progresso', 'none'),
        ('classes', 'role_teacher', 'Professor(a)', 'none'),
        ('classes', 'role_student', 'Aluno(a)', 'none'),
        ('classes', 'empty', 'Nenhuma turma ainda. Crie uma ou entre com um código.', 'none'),
        ('classes', 'error', 'Não foi possível carregar as turmas.', 'none'),
        ('classes', 'completed_count', '{completed}/{total} concluídos', 'other'),
        ('classes', 'delete_class', 'Excluir turma', 'none'),
        ('classes', 'remove_member', 'Remover membro', 'none'),
        ('classes', 'remove_assignment', 'Remover tarefa', 'none'),
        ('classes', 'students', 'Alunos', 'none'),
        ('classes', 'no_assignments', 'Nenhuma lição atribuída ainda.', 'none'),
        ('classes', 'no_members', 'Nenhum aluno entrou ainda.', 'none'),
        ('classes', 'due', 'Vence em {date}', 'other'),
        ('classes', 'class_id', 'ID da turma', 'none'),
        ('classes', 'join_hint', 'Digite o ID da turma e o código de convite do seu professor.', 'none'),
        ('classes', 'create_success', 'Turma criada. Compartilhe o código de convite com seus alunos.', 'none')
     ) as t (namespace, key, value, plural_rule)
where l.code = 'pt'
on conflict (locale_id, namespace, key) do nothing;
