-- =====================================================================
-- ANNEX — Migration 20260813000001: educator tools
-- Classes, membership, and lesson assignments (Phase 17). A class is
-- owned by one user (its creator becomes a 'teacher' member); any user
-- can create a class and invite others with the generated invite code.
-- Assignments link a published lesson to a class; completion progress
-- is derived by joining class members against lesson_progress (Phase 15),
-- so no duplicate progress store exists.
-- =====================================================================

-- A class: metadata plus a short unique invite code for joining.
create table if not exists public.classes (
    id uuid primary key default gen_random_uuid(),
    owner_id uuid not null references public.users (id) on delete cascade,
    name text not null check (char_length(name) between 1 and 120),
    description text not null default '',
    invite_code text not null unique
        check (invite_code ~ '^[A-Z0-9]{8}$'),
    created_at timestamptz not null default now()
);

create index if not exists idx_classes_owner on public.classes (owner_id);

-- Membership: the owner is inserted as a 'teacher' member on creation;
-- everyone else joins as a 'student'. One row per (class, user).
create table if not exists public.class_members (
    class_id uuid not null references public.classes (id) on delete cascade,
    user_id uuid not null references public.users (id) on delete cascade,
    role text not null default 'student'
        check (role in ('teacher', 'student')),
    joined_at timestamptz not null default now(),
    primary key (class_id, user_id)
);

create index if not exists idx_class_members_user on public.class_members (user_id);

-- Assignments: a published lesson assigned to a class. One assignment
-- per (class, lesson) keeps progress reports unambiguous — re-assigning
-- the same lesson is idempotent.
create table if not exists public.assignments (
    id uuid primary key default gen_random_uuid(),
    class_id uuid not null references public.classes (id) on delete cascade,
    lesson_id uuid not null references public.lessons (id) on delete cascade,
    assigned_by uuid not null references public.users (id) on delete cascade,
    due_at timestamptz,
    created_at timestamptz not null default now(),
    unique (class_id, lesson_id)
);

create index if not exists idx_assignments_class on public.assignments (class_id);

-- --- row-level security ------------------------------------------------
-- Defense-in-depth (ADR-0004): the owner manages everything, members
-- read shared class data, and the service role bypasses RLS for the
-- backend's own writes.

alter table public.classes enable row level security;
alter table public.class_members enable row level security;
alter table public.assignments enable row level security;

-- classes: owner manages; members read.
create policy "classes_select_member" on public.classes
    for select using (
        auth.uid() = owner_id
        or exists (
            select 1 from public.class_members m
            where m.class_id = id and m.user_id = auth.uid()
        )
    );
create policy "classes_insert_own" on public.classes
    for insert with check (auth.uid() = owner_id);
create policy "classes_update_owner" on public.classes
    for update using (auth.uid() = owner_id);
create policy "classes_delete_owner" on public.classes
    for delete using (auth.uid() = owner_id);

-- class_members: members read; the owner manages; joining inserts own row.
create policy "class_members_select_member" on public.class_members
    for select using (
        auth.uid() = user_id
        or exists (
            select 1 from public.classes c
            where c.id = class_id and c.owner_id = auth.uid()
        )
    );
create policy "class_members_insert_join" on public.class_members
    for insert with check (
        auth.uid() = user_id
        or exists (
            select 1 from public.classes c
            where c.id = class_id and c.owner_id = auth.uid()
        )
    );
create policy "class_members_update_owner" on public.class_members
    for update using (
        exists (
            select 1 from public.classes c
            where c.id = class_id and c.owner_id = auth.uid()
        )
    );
create policy "class_members_delete_owner" on public.class_members
    for delete using (
        exists (
            select 1 from public.classes c
            where c.id = class_id and c.owner_id = auth.uid()
        )
    );

-- assignments: members read; the owner (teacher) manages.
create policy "assignments_select_member" on public.assignments
    for select using (
        exists (
            select 1 from public.class_members m
            where m.class_id = class_id and m.user_id = auth.uid()
        )
    );
create policy "assignments_insert_owner" on public.assignments
    for insert with check (
        exists (
            select 1 from public.classes c
            where c.id = class_id and c.owner_id = auth.uid()
        )
    );
create policy "assignments_update_owner" on public.assignments
    for update using (
        exists (
            select 1 from public.classes c
            where c.id = class_id and c.owner_id = auth.uid()
        )
    );
create policy "assignments_delete_owner" on public.assignments
    for delete using (
        exists (
            select 1 from public.classes c
            where c.id = class_id and c.owner_id = auth.uid()
        )
    );
