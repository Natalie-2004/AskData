import sqlite3
import os

def init_database():
    os.makedirs('schema', exist_ok=True)

    # connect to the SQLite database (it will be created if it doesn't exist)
    db_path = 'data/askdata.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
    create table if not exists users (
        user_id integer primary key,
        user_name text not null,
        age integer
    )
    ''')

    cursor.execute('''
    create table if not exists trade_summary (
        user_id integer,
        total_trade_count integer,
        interest_rate real,
        foreign key(user_id) references users(user_id)
    )
    ''')

    # delete existing data
    cursor.execute('delete from trade_summary')
    cursor.execute('delete from users')

    # insert mock data into tables
    mock_users = [
        (10001, 'zhangsan', 28),
        (10002, 'lisi', 35),
        (10003, 'wangwu', 24),
        (10004, 'zhaoliu', 42)
    ]
    cursor.executemany('insert into users (user_id, user_name, age) values (?, ?, ?)', mock_users)

    mock_trades = [
        (10001, 152, 3.85),
        (10002, 56000, 4.58),
        (10003, 12, 2.35),
        (10004, 102430, 3.12)
    ]
    cursor.executemany('insert into trade_summary (user_id, total_trade_count, interest_rate) values (?, ?, ?)', mock_trades)

    # save changes and close connection
    conn.commit()
    conn.close()

    print(f"Database initialized successfully! File saved at: {db_path}")
    print("Mock data inserted successfully.")

if __name__ == '__main__':
    init_database()