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
                      owner TEXT, due_date TEXT, due_date_reason TEXT)"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS meeting_orders
                     (id INTEGER PRIMARY KEY, meeting_id INTEGER, description TEXT, owner TEXT,
                      due_date TEXT, is_resolved INTEGER, created_at TEXT, completed_at TEXT)"""
        )
        c.execute("CREATE INDEX IF NOT EXISTS idx_meetings_date ON meetings(date)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_agenda_meeting_id ON agenda(meeting_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_agenda_points_meeting_id ON agenda_points(meeting_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_agenda_items_point_id ON agenda_items(point_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_agenda_items_owner ON agenda_items(owner)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_agenda_items_due_date ON agenda_items(due_date)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_meeting_orders_meeting_id ON meeting_orders(meeting_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_meeting_orders_owner ON meeting_orders(owner)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_meeting_orders_due_date ON meeting_orders(due_date)")
        self.commit_database()
        self.ensure_agenda_item_columns()
        self.ensure_meeting_order_columns()
        self.migrate_legacy_agenda()


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
        self.commit_database()


    def ensure_meeting_order_columns(self):
        c = self.conn.cursor()
        c.execute("PRAGMA table_info(meeting_orders)")
        columns = {row[1] for row in c.fetchall()}
        if "created_at" not in columns:
            c.execute("ALTER TABLE meeting_orders ADD COLUMN created_at TEXT")
        if "completed_at" not in columns:
            c.execute("ALTER TABLE meeting_orders ADD COLUMN completed_at TEXT")
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

