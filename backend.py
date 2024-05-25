import sqlite3


class Database:
    def __init__(self, db_file):
        self.conn = sqlite3.connect(db_file)
        self.cursor = self.conn.cursor()

    def create_user_table(self):
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS users
            (id INTEGER PRIMARY KEY, discord_id INTEGER, discord_name TEXT)''')
        self.conn.commit()

    def create_topic_table(self):
        # topic Id topicName
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS topics
            (id INTEGER PRIMARY KEY, topic_name TEXT)''')
        self.conn.commit()

    def create_activity_table(self):
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS activities
            (id INTEGER PRIMARY KEY, date TEXT, duree INTEGER, id_topic INTEGER, id_discord_user INTEGER)''')
        self.conn.commit()

    def create_tables(self):
        self.create_user_table()
        self.create_topic_table()
        self.create_activity_table()

    def insert_user(self, discord_id, discord_name):
        if self.getUser(discord_id) is not None:
            return
        self.cursor.execute(
            'INSERT INTO users (discord_id, discord_name) VALUES (?, ?)', (discord_id, discord_name))
        self.conn.commit()

    def getUser(self, discord_id):
        self.cursor.execute(
            'SELECT * FROM users WHERE discord_id = ?', (discord_id,))
        return self.cursor.fetchone()
    
    def insert_topic(self, topic_name):
        self.cursor.execute(
            'INSERT INTO topics (topic_name) VALUES (?)', (topic_name,))
        self.conn.commit()

    def get_topic(self, topic_name):
        self.cursor.execute(
            'SELECT * FROM topics WHERE topic_name = ?', (topic_name,))
        return self.cursor.fetchone()

    def get_topic_levenshtein(self, topic_name):
        # Get the topic by iterating 3 times over the topics
        # 1 st time is EXACT MATCH
        # 2 nd time is LEVENSHTEIN DISTANCE 1
        # 3 rd time is topic_name in topic_name
        self.cursor.execute(
            'SELECT * FROM topics WHERE topic_name = ?', (topic_name,))
        result = self.cursor.fetchone()
        if result:
            return result
        self.cursor.execute(
            'SELECT * FROM topics WHERE topic_name LIKE ?', (f'%{topic_name}%',))
        result = self.cursor.fetchone()
        if result:
            return result
        self.cursor.execute(
            'SELECT * FROM topics')
        topics = self.cursor.fetchall()
        for topic in topics:
            if topic_name in topic[1]:
                return topic
        return None
    
    def insert_activity(self, date, duree, id_topic, id_discord_user):
        self.cursor.execute(
            'INSERT INTO activities (date, duree, id_topic, id_discord_user) VALUES (?, ?, ?, ?)', (date, duree, id_topic, id_discord_user))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_activities(self, id_discord_user, date_debut):
        self.cursor.execute(
            'SELECT * FROM activities a JOIN topics t ON t.id = a.id_topic WHERE id_discord_user = ? AND date >= ?', (id_discord_user, date_debut))
        return self.cursor.fetchall()
    
    def get_activities_by_topic(self, id_discord_user, topic_id):
        self.cursor.execute(
            'SELECT * FROM activities a JOIN topics t ON t.id = a.id_topic WHERE id_discord_user = ? AND t.id = ?', (id_discord_user, topic_id))
        return self.cursor.fetchall()