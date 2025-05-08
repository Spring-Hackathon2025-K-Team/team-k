from flask import abort
import pymysql
from util.DB import DB


# 初期起動時にコネクションプールを作成し接続を確立
db_pool = DB.init_db_pool()


# ユーザークラス
# ユーザーを追加する
class User:
    @classmethod
    def create(cls, uid, name, email, password, is_admin): # ユーザーを作成するメソッド
        conn = db_pool.get_conn()   # コネクションプールからコネクションを取得
        try:    # コネクションを取得
            with conn.cursor() as cur:  # カーソルを取得
                role = "admin" if is_admin else "user"  # ユーザーの立場を設定
                sql = "INSERT INTO users (uid, user_name, email, password, role) VALUES (%s, %s, %s, %s, %s);"    # SQL文を定義
                cur.execute(sql, (uid, name, email, password, role)) # SQL文を実行
                conn.commit() # 変更を確定して保存する
        except pymysql.Error as e:  # エラーが発生した場合
            print(f'エラーが発生しています：{e}')
            abort(500)  # 500エラーを返す
        finally:
            db_pool.release(conn)   # コネクションをプールに戻す

    # ユーザーを取得するメソッド
    @classmethod
    def find_by_email(cls, email):  # メールアドレスからユーザーを取得するメソッド
        conn = db_pool.get_conn()   # コネクションプールからコネクションを取得
        try:    # コネクションを取得
                with conn.cursor() as cur:  # カーソルを取得
                    sql = "SELECT * FROM users WHERE email=%s;"
                    cur.execute(sql, (email,))  # SQL文を実行
                    user = cur.fetchone()   # 1件取得
                return user # 取得したユーザーを返す
        except pymysql.Error as e:  # エラーが発生した場合
            print(f'エラーが発生しています：{e}')
            abort(500)
        finally:
            db_pool.release(conn)


# チャンネルクラス
# チャンネルを追加する
class Channel:
    @classmethod
    def create(cls, uid, new_channel_name, new_channel_description):
        conn = db_pool.get_conn()
        try:
            with conn.cursor() as cur:
                sql = "INSERT INTO channels (uid, name, abstract) VALUES (%s, %s, %s);" # チャンネルを作成するSQL文
                cur.execute(sql, (uid, new_channel_name, new_channel_description,))
                conn.commit()
        except pymysql.Error as e:
            print(f'エラーが発生しています：{e}')
            abort(500)
        finally:
            db_pool.release(conn)

    # 全てのチャンネルを取得する
    @classmethod
    def get_all(cls):
        conn = db_pool.get_conn()
        try:
            with conn.cursor() as cur:  # カーソルを取得
                sql = "SELECT * FROM channels;" # 全チャンネルを取得するSQL文
                cur.execute(sql)            # SQL文を実行
                channels = cur.fetchall()   # 全チャンネルを取得
                return channels # 取得したチャンネルを返す
        except pymysql.Error as e:
            print(f'エラーが発生しています：{e}')
            abort(500)
        finally:
            db_pool.release(conn)

    # 1つのチャンネルを取得する
    @classmethod
    def find_by_cid(cls, cid):
        conn = db_pool.get_conn()
        try:
            with conn.cursor() as cur:  # カーソルを取得
                sql = "SELECT * FROM channels WHERE id=%s;" # チャンネルIDからチャンネルを取得するSQL文
                cur.execute(sql, (cid,)) # SQL文を実行   
                channel = cur.fetchone() # 1件取得
                return channel  # 取得したチャンネルを返す
        except pymysql.Error as e:
            print(f'エラーが発生しています：{e}')
            abort(500)
        finally:
            db_pool.release(conn)

    # チャンネル名からチャンネルを取得する
    @classmethod
    def find_by_name(cls, channel_name):
        conn = db_pool.get_conn()
        try:
            with conn.cursor() as cur:
                sql = "SELECT * FROM channels WHERE name=%s;"   # チャンネル名からチャンネルを取得するSQL文
                cur.execute(sql, (channel_name,))   # SQL文を実行
                channel = cur.fetchone()         # 1件取得
                return channel  # 取得したチャンネルを返す
        except pymysql.Error as e:
            print(f'エラーが発生しています：{e}')
            abort(500)
        finally:
            db_pool.release(conn)

    # チャンネルの更新
    @classmethod
    def update(cls, uid, new_channel_name, new_channel_description, cid):
        conn = db_pool.get_conn()
        try:
            with conn.cursor() as cur:
                sql = "UPDATE channels SET uid=%s, name=%s, abstract=%s WHERE id=%s;"  # チャンネルの作成者、チャンネル名、チャンネルの説明を更新する
                cur.execute(sql, (uid, new_channel_name, new_channel_description, cid,))
                conn.commit()
        except pymysql.Error as e:
            print(f'エラーが発生しています：{e}')
            abort(500)
        finally:
            db_pool.release(conn)

    # チャンネルの削除
    @classmethod
    def delete(cls, cid):
        conn = db_pool.get_conn()
        try:
            with conn.cursor() as cur:
                sql = "DELETE FROM channels WHERE id=%s;"   # チャンネルIDからチャンネルを削除するSQL文
                cur.execute(sql, (cid,))
                conn.commit()
        except pymysql.Error as e:
            print(f'エラーが発生しています：{e}')
            abort(500)
        finally:
            db_pool.release(conn)


# メッセージクラス
# メッセージを追加する
class Message:
    @classmethod
    def create(cls, uid, cid, message):
        conn = db_pool.get_conn()
        try:
            with conn.cursor() as cur:
                sql = "INSERT INTO messages(uid, cid, message) VALUES(%s, %s, %s)"  # メッセージを作成するSQL文
                cur.execute(sql, (uid, cid, message,))
                conn.commit()
        except pymysql.Error as e:
            print(f'エラーが発生しています：{e}')
            abort(500)
        finally:
            db_pool.release(conn)

    # 全てのメッセージを取得するメソッド
    @classmethod
    def get_all(cls, cid):
        conn = db_pool.get_conn()
        try:
            with conn.cursor() as cur:
                sql = """
                    SELECT id, u.uid, user_name, message 
                    FROM messages AS m 
                    INNER JOIN users AS u ON m.uid = u.uid 
                    WHERE cid = %s 
                    ORDER BY id ASC;
                """ # チャンネルIDから全メッセージを取得するSQL文
                cur.execute(sql, (cid,))
                messages = cur.fetchall()
                return messages
        except pymysql.Error as e:
            print(f'エラーが発生しています：{e}')
            abort(500)
        finally:
            db_pool.release(conn)

    # メッセージIDからメッセージを取得するメソッド
    @classmethod
    def delete(cls, message_id):
        conn = db_pool.get_conn()
        try:
            with conn.cursor() as cur:
                sql = "DELETE FROM messages WHERE id=%s;"   # メッセージIDからメッセージを削除するSQL文
                cur.execute(sql, (message_id,))
                conn.commit()
        except pymysql.Error as e:
            print(f'エラーが発生しています：{e}')
            abort(500)
        finally:
            db_pool.release(conn)