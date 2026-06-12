# -*- coding: utf-8 -*-



class SchemaMixin:

    def create_tables(self):
        c = self.conn.cursor()
        c.execute(
            """CREATE TABLE IF NOT EXISTS meetings
                     (id INTEGER PRIMARY KEY, title TEXT, date TEXT, notes TEXT)"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS agenda
                     (id INTEGER PRIMARY KEY, meeting_id INTEGER, description TEXT, is_resolved INTEGER)"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS agenda_points
                     (id INTEGER PRIMARY KEY, meeting_id INTEGER, title TEXT)"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS agenda_items
                     (id INTEGER PRIMARY KEY, point_id INTEGER, description TEXT, is_resolved INTEGER,
                      owner TEXT, due_date TEXT, due_date_reason TEXT, priority TEXT DEFAULT 'Normální',
                      copied_from_item_id INTEGER)"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS meeting_orders
                     (id INTEGER PRIMARY KEY, meeting_id INTEGER, description TEXT, owner TEXT,
                      due_date TEXT, is_resolved INTEGER, created_at TEXT, completed_at TEXT,
                      priority TEXT DEFAULT 'Normální', copied_from_order_id INTEGER)"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS meeting_requirements
                     (id INTEGER PRIMARY KEY, meeting_id INTEGER, description TEXT, owner TEXT,
                      due_date TEXT, is_resolved INTEGER, created_at TEXT, completed_at TEXT,
                      priority TEXT DEFAULT 'Normální', requirement_status TEXT DEFAULT 'Nový',
                      linked_problem_id INTEGER, copied_from_requirement_id INTEGER)"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS meeting_general_info
                     (id INTEGER PRIMARY KEY, meeting_id INTEGER, info_text TEXT, created_at TEXT,
                      is_invalid INTEGER, invalidated_at TEXT)"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS change_history
                     (id INTEGER PRIMARY KEY, record_type TEXT, record_id INTEGER, meeting_id INTEGER,
                      field_name TEXT, old_value TEXT, new_value TEXT, changed_at TEXT, changed_by TEXT)"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS people
                     (id INTEGER PRIMARY KEY, name TEXT UNIQUE, normalized_name TEXT, is_active INTEGER DEFAULT 1)"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS item_comments
                     (id INTEGER PRIMARY KEY, record_type TEXT, record_id INTEGER, meeting_id INTEGER,
                      comment_text TEXT, created_at TEXT, created_by TEXT)"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS app_launchers
                     (id INTEGER PRIMARY KEY, name TEXT NOT NULL, target_path TEXT NOT NULL,
                      arguments TEXT DEFAULT '', sort_order INTEGER DEFAULT 0, is_active INTEGER DEFAULT 1)"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS corrective_actions
                     (id INTEGER PRIMARY KEY, meeting_id INTEGER, problem_title TEXT NOT NULL,
                      problem_description TEXT, root_cause TEXT, corrective_action TEXT NOT NULL,
                      owner TEXT, due_date TEXT, status TEXT DEFAULT 'Nový',
                      priority TEXT DEFAULT 'Normální', created_at TEXT, completed_at TEXT,
                      source_requirement_id INTEGER)"""
        )
        self.commit_database()
        self.ensure_meeting_columns()
        self.ensure_general_info_columns()
        self.ensure_agenda_item_columns()
        self.ensure_meeting_order_columns()
        self.ensure_meeting_requirement_columns()
        self.ensure_app_launcher_columns()
        self.ensure_corrective_action_columns()

        c.execute("CREATE INDEX IF NOT EXISTS idx_meetings_date ON meetings(date)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_agenda_meeting_id ON agenda(meeting_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_agenda_points_meeting_id ON agenda_points(meeting_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_agenda_items_point_id ON agenda_items(point_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_agenda_items_owner ON agenda_items(owner)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_agenda_items_due_date ON agenda_items(due_date)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_meeting_orders_meeting_id ON meeting_orders(meeting_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_meeting_orders_owner ON meeting_orders(owner)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_meeting_orders_due_date ON meeting_orders(due_date)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_meeting_orders_copied_from ON meeting_orders(copied_from_order_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_meeting_requirements_meeting_id ON meeting_requirements(meeting_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_meeting_requirements_owner ON meeting_requirements(owner)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_meeting_requirements_due_date ON meeting_requirements(due_date)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_meeting_requirements_linked_problem ON meeting_requirements(linked_problem_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_meeting_requirements_copied_from ON meeting_requirements(copied_from_requirement_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_meeting_general_info_meeting_id ON meeting_general_info(meeting_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_meeting_general_info_created_at ON meeting_general_info(created_at)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_change_history_record ON change_history(record_type, record_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_change_history_meeting_id ON change_history(meeting_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_people_name ON people(name)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_item_comments_record ON item_comments(record_type, record_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_app_launchers_order ON app_launchers(sort_order, name)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_corrective_actions_meeting_id ON corrective_actions(meeting_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_corrective_actions_owner ON corrective_actions(owner)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_corrective_actions_due_date ON corrective_actions(due_date)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_corrective_actions_status ON corrective_actions(status)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_corrective_actions_source_requirement ON corrective_actions(source_requirement_id)")
        self.commit_database()
        self.ensure_default_app_launchers()
        self.migrate_general_info_column()
        self.migrate_legacy_agenda()


    def ensure_app_launcher_columns(self):
        c = self.conn.cursor()
        c.execute("PRAGMA table_info(app_launchers)")
        columns = {row[1] for row in c.fetchall()}
        if "arguments" not in columns:
            c.execute("ALTER TABLE app_launchers ADD COLUMN arguments TEXT DEFAULT ''")
        if "sort_order" not in columns:
            c.execute("ALTER TABLE app_launchers ADD COLUMN sort_order INTEGER DEFAULT 0")
        if "is_active" not in columns:
            c.execute("ALTER TABLE app_launchers ADD COLUMN is_active INTEGER DEFAULT 1")
        self.commit_database()


    def ensure_default_app_launchers(self):
        c = self.conn.cursor()
        default_launchers = (
            ("Porady", "__PORADY__", -100),
            ("Požadavky", "__REQUIREMENTS__", -90),
            ("Problémy a nápravná opatření", "__PROBLEMS__", -80),
            ("Vyhodnocení kvality", "__QUALITY__", -70),
        )
        for name, target_path, sort_order in default_launchers:
            c.execute("SELECT id FROM app_launchers WHERE target_path=?", (target_path,))
            row = c.fetchone()
            if row:
                c.execute(
                    """UPDATE app_launchers
                       SET name=?, sort_order=?, is_active=1
                       WHERE id=?""",
                    (name, sort_order, row[0]),
                )
                continue
            c.execute(
                """INSERT INTO app_launchers (name, target_path, arguments, sort_order, is_active)
                   VALUES (?, ?, '', ?, 1)""",
                (name, target_path, sort_order),
            )
        self.commit_database()


    def ensure_corrective_action_columns(self):
        c = self.conn.cursor()
        c.execute("PRAGMA table_info(corrective_actions)")
        columns = {row[1] for row in c.fetchall()}
        if "meeting_id" not in columns:
            c.execute("ALTER TABLE corrective_actions ADD COLUMN meeting_id INTEGER")
        if "problem_description" not in columns:
            c.execute("ALTER TABLE corrective_actions ADD COLUMN problem_description TEXT")
        if "root_cause" not in columns:
            c.execute("ALTER TABLE corrective_actions ADD COLUMN root_cause TEXT")
        if "owner" not in columns:
            c.execute("ALTER TABLE corrective_actions ADD COLUMN owner TEXT")
        if "due_date" not in columns:
            c.execute("ALTER TABLE corrective_actions ADD COLUMN due_date TEXT")
        if "status" not in columns:
            c.execute("ALTER TABLE corrective_actions ADD COLUMN status TEXT DEFAULT 'Nový'")
        if "priority" not in columns:
            c.execute("ALTER TABLE corrective_actions ADD COLUMN priority TEXT DEFAULT 'Normální'")
        if "created_at" not in columns:
            c.execute("ALTER TABLE corrective_actions ADD COLUMN created_at TEXT")
        if "completed_at" not in columns:
            c.execute("ALTER TABLE corrective_actions ADD COLUMN completed_at TEXT")
        if "source_requirement_id" not in columns:
            c.execute("ALTER TABLE corrective_actions ADD COLUMN source_requirement_id INTEGER")
        self.commit_database()


    def ensure_agenda_item_columns(self):
        c = self.conn.cursor()
        c.execute("PRAGMA table_info(agenda_items)")
        columns = {row[1] for row in c.fetchall()}
        if "owner" not in columns:
            c.execute("ALTER TABLE agenda_items ADD COLUMN owner TEXT")
        if "due_date" not in columns:
            c.execute("ALTER TABLE agenda_items ADD COLUMN due_date TEXT")
        if "due_date_reason" not in columns:
            c.execute("ALTER TABLE agenda_items ADD COLUMN due_date_reason TEXT")
        if "priority" not in columns:
            c.execute("ALTER TABLE agenda_items ADD COLUMN priority TEXT DEFAULT 'Normální'")
        if "copied_from_item_id" not in columns:
            c.execute("ALTER TABLE agenda_items ADD COLUMN copied_from_item_id INTEGER")
        self.backfill_copied_task_links()
        c.execute("CREATE INDEX IF NOT EXISTS idx_agenda_items_copied_from ON agenda_items(copied_from_item_id)")
        self.commit_database()


    def backfill_copied_task_links(self):
        c = self.conn.cursor()
        c.execute(
            """SELECT child.id, MAX(parent.id)
               FROM agenda_items AS child
               JOIN agenda_points AS child_point ON child_point.id = child.point_id
               JOIN meetings AS child_meeting ON child_meeting.id = child_point.meeting_id
               JOIN agenda_points AS parent_point ON parent_point.title = child_point.title
               JOIN meetings AS parent_meeting ON parent_meeting.id = parent_point.meeting_id
               JOIN agenda_items AS parent ON parent.point_id = parent_point.id
               WHERE child.copied_from_item_id IS NULL
                 AND parent.id <> child.id
                 AND COALESCE(parent.is_resolved, 0)=0
                 AND COALESCE(child.is_resolved, 0)=0
                 AND COALESCE(parent.description, '') = COALESCE(child.description, '')
                 AND COALESCE(parent.owner, '') = COALESCE(child.owner, '')
                 AND COALESCE(parent.due_date, '') = COALESCE(child.due_date, '')
                 AND COALESCE(parent.due_date_reason, '') = COALESCE(child.due_date_reason, '')
                 AND NOT EXISTS (
                     SELECT 1
                     FROM agenda_items AS existing_child
                     JOIN agenda_points AS existing_point ON existing_point.id = existing_child.point_id
                     WHERE existing_child.copied_from_item_id = parent.id
                       AND existing_point.meeting_id = child_meeting.id
                 )
                 AND (
                     parent_meeting.date < child_meeting.date
                     OR (parent_meeting.date = child_meeting.date AND parent_meeting.id < child_meeting.id)
                 )
               GROUP BY child.id"""
        )
        links = c.fetchall()
        for child_id, parent_id in links:
            c.execute(
                "UPDATE agenda_items SET copied_from_item_id=? WHERE id=?",
                (parent_id, child_id),
            )


    def ensure_meeting_order_columns(self):
        c = self.conn.cursor()
        c.execute("PRAGMA table_info(meeting_orders)")
        columns = {row[1] for row in c.fetchall()}
        if "created_at" not in columns:
            c.execute("ALTER TABLE meeting_orders ADD COLUMN created_at TEXT")
        if "completed_at" not in columns:
            c.execute("ALTER TABLE meeting_orders ADD COLUMN completed_at TEXT")
        if "priority" not in columns:
            c.execute("ALTER TABLE meeting_orders ADD COLUMN priority TEXT DEFAULT 'Normální'")
        if "copied_from_order_id" not in columns:
            c.execute("ALTER TABLE meeting_orders ADD COLUMN copied_from_order_id INTEGER")
            self.backfill_copied_order_links()
        self.commit_database()


    def ensure_meeting_requirement_columns(self):
        c = self.conn.cursor()
        c.execute("PRAGMA table_info(meeting_requirements)")
        columns = {row[1] for row in c.fetchall()}
        if "created_at" not in columns:
            c.execute("ALTER TABLE meeting_requirements ADD COLUMN created_at TEXT")
        if "completed_at" not in columns:
            c.execute("ALTER TABLE meeting_requirements ADD COLUMN completed_at TEXT")
        if "priority" not in columns:
            c.execute("ALTER TABLE meeting_requirements ADD COLUMN priority TEXT DEFAULT 'Normální'")
        if "requirement_status" not in columns:
            c.execute("ALTER TABLE meeting_requirements ADD COLUMN requirement_status TEXT DEFAULT 'Nový'")
        if "linked_problem_id" not in columns:
            c.execute("ALTER TABLE meeting_requirements ADD COLUMN linked_problem_id INTEGER")
        if "copied_from_requirement_id" not in columns:
            c.execute("ALTER TABLE meeting_requirements ADD COLUMN copied_from_requirement_id INTEGER")
            self.backfill_copied_requirement_links()
        self.commit_database()


    def backfill_copied_order_links(self):
        self.backfill_copied_record_links(
            table_name="meeting_orders",
            copied_column="copied_from_order_id",
            extra_match_sql="AND COALESCE(parent.priority, 'Normální') = COALESCE(child.priority, 'Normální')",
        )


    def backfill_copied_requirement_links(self):
        self.backfill_copied_record_links(
            table_name="meeting_requirements",
            copied_column="copied_from_requirement_id",
            extra_match_sql=(
                "AND COALESCE(parent.priority, 'Normální') = COALESCE(child.priority, 'Normální') "
                "AND COALESCE(parent.requirement_status, 'Nový') = COALESCE(child.requirement_status, 'Nový')"
            ),
        )


    def backfill_copied_record_links(self, table_name, copied_column, extra_match_sql=""):
        c = self.conn.cursor()
        c.execute(
            f"""SELECT child.id, MAX(parent.id)
                FROM {table_name} AS child
                JOIN meetings AS child_meeting ON child_meeting.id = child.meeting_id
                JOIN {table_name} AS parent
                  ON parent.id <> child.id
                 AND COALESCE(parent.is_resolved, 0)=0
                 AND COALESCE(child.is_resolved, 0)=0
                 AND COALESCE(parent.description, '') = COALESCE(child.description, '')
                 AND COALESCE(parent.owner, '') = COALESCE(child.owner, '')
                 AND COALESCE(parent.due_date, '') = COALESCE(child.due_date, '')
                 AND COALESCE(parent.created_at, '') = COALESCE(child.created_at, '')
                 {extra_match_sql}
                JOIN meetings AS parent_meeting ON parent_meeting.id = parent.meeting_id
                WHERE child.{copied_column} IS NULL
                  AND (
                      parent_meeting.date < child_meeting.date
                      OR (parent_meeting.date = child_meeting.date AND parent_meeting.id < child_meeting.id)
                  )
                GROUP BY child.id"""
        )
        for child_id, parent_id in c.fetchall():
            c.execute(
                f"UPDATE {table_name} SET {copied_column}=? WHERE id=?",
                (parent_id, child_id),
            )


    def ensure_meeting_columns(self):
        c = self.conn.cursor()
        c.execute("PRAGMA table_info(meetings)")
        columns = {row[1] for row in c.fetchall()}
        if "general_info" not in columns:
            c.execute("ALTER TABLE meetings ADD COLUMN general_info TEXT")
        if "archived" not in columns:
            c.execute("ALTER TABLE meetings ADD COLUMN archived INTEGER DEFAULT 0")
        self.commit_database()


    def ensure_general_info_columns(self):
        c = self.conn.cursor()
        c.execute("PRAGMA table_info(meeting_general_info)")
        columns = {row[1] for row in c.fetchall()}
        if "created_at" not in columns:
            c.execute("ALTER TABLE meeting_general_info ADD COLUMN created_at TEXT")
        if "is_invalid" not in columns:
            c.execute("ALTER TABLE meeting_general_info ADD COLUMN is_invalid INTEGER DEFAULT 0")
        if "invalidated_at" not in columns:
            c.execute("ALTER TABLE meeting_general_info ADD COLUMN invalidated_at TEXT")
        self.commit_database()


    def migrate_general_info_column(self):
        c = self.conn.cursor()
        c.execute(
            """SELECT id, general_info FROM meetings
               WHERE general_info IS NOT NULL AND TRIM(general_info) <> ''"""
        )
        rows = c.fetchall()
        for meeting_id, general_info in rows:
            c.execute("SELECT COUNT(*) FROM meeting_general_info WHERE meeting_id=?", (meeting_id,))
            if c.fetchone()[0] == 0:
                c.execute(
                    """INSERT INTO meeting_general_info
                       (meeting_id, info_text, created_at, is_invalid, invalidated_at)
                       VALUES (?, ?, datetime('now', 'localtime'), 0, '')""",
                    (meeting_id, general_info),
                )
        if rows:
            c.execute("UPDATE meetings SET general_info='' WHERE general_info IS NOT NULL AND TRIM(general_info) <> ''")
        self.commit_database()


    def migrate_legacy_agenda(self):
        c = self.conn.cursor()
        c.execute("SELECT COUNT(*) FROM agenda")
        legacy_count = c.fetchone()[0]
        if legacy_count == 0:
            return

        c.execute("SELECT DISTINCT meeting_id FROM agenda")
        meeting_ids = [row[0] for row in c.fetchall()]
        for meeting_id in meeting_ids:
            c.execute("SELECT COUNT(*) FROM agenda_points WHERE meeting_id=?", (meeting_id,))
            if c.fetchone()[0] > 0:
                continue

            c.execute("INSERT INTO agenda_points (meeting_id, title) VALUES (?, ?)", (meeting_id, "Původní body"))
            point_id = c.lastrowid
            c.execute("SELECT description, is_resolved FROM agenda WHERE meeting_id=? ORDER BY id", (meeting_id,))
            for description, is_resolved in c.fetchall():
                c.execute(
                    "INSERT INTO agenda_items (point_id, description, is_resolved) VALUES (?, ?, ?)",
                    (point_id, description, is_resolved),
                )

        self.commit_database()

