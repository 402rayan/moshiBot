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
        # date idTopic idDiscordUser
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS activities
            (id INTEGER PRIMARY KEY, date TEXT, id_topic INTEGER, id_discord_user INTEGER)''')
        self.conn.commit()
        
    def create_tables(self):
        self.create_user_table()
        self.create_topic_table()
        self.create_activity_table()
        
    def insert_user(self, discord_id, discord_name):
        self.cursor.execute('INSERT INTO users (discord_id, discord_name) VALUES (?, ?)', (discord_id, discord_name))
        self.conn.commit()
        
    def getUser(self, discord_id):
        self.cursor.execute('SELECT * FROM users WHERE discord_id = ?', (discord_id,))
        return self.cursor.fetchone()
    
    def get_topic(self, topic_name):
        self.cursor.execute('SELECT * FROM topics WHERE topic_name = ?', (topic_name,))
        return self.cursor.fetchone()
    
    def insert_activity(self, date, id_topic, id_discord_user):
        self.cursor.execute('INSERT INTO activities (date, id_topic, id_discord_user) VALUES (?, ?, ?)', (date, id_topic, id_discord_user))
        self.conn.commit()
        
    
        