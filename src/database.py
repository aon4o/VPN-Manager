import sqlite3

DATABASE = 'vpn_configs.db'

def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS vpn_configs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT,
                  username TEXT,
                  password TEXT,
                  qr_code_path TEXT,
                  ovpn_config_path TEXT)''')
    conn.commit()
    conn.close()

def get_vpns():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    configs = c.execute("SELECT id, name FROM vpn_configs").fetchall()
    conn.close()
    return configs

def create_vpn(data):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("INSERT INTO vpn_configs (name, username, password, qr_code_path, ovpn_config_path) VALUES (?, ?, ?, ?, ?)",
              (data['name'], data['username'], data['password'], data['qr_code_path'], data['ovpn_config_path']))
    conn.commit()
    conn.close()

def delete_vpn(vpn_id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("DELETE FROM vpn_configs WHERE id = ?", (vpn_id,))
    conn.commit()
    conn.close()

def get_vpn(vpn_id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT name, username, password, qr_code_path, ovpn_config_path FROM vpn_configs WHERE id = ?", (vpn_id,))
    vpn = c.fetchone()
    conn.close()

    return vpn
