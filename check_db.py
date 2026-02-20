import sqlite3

con = sqlite3.connect("app.db")

print("Tabelas:", con.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall())
print("EPIs:", con.execute("SELECT COUNT(*) FROM epis;").fetchone())
print("Perigos:", con.execute("SELECT COUNT(*) FROM perigos;").fetchone())
