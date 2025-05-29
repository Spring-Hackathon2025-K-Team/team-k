from flask import Flask, request, redirect, render_template, session, flash, abort, url_for
from datetime import timedelta, datetime
import hashlib
import uuid
import re           # 正規表現を使用する
import os       # osモジュールを使用する
import pytz     # 日本のタイムゾーンを使用する
from werkzeug.utils import secure_filename      # ファイル名を安全にするモジュール
from models import User, Channel, Message
from util.assets import bundle_css_files
from flask_socketio import SocketIO, join_room, leave_room  # SocketIOを使用するためのモジュール


app = Flask(__name__)

# 定数定義
EMAIL_PATTERN = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
SESSION_DAYS = 30
app.secret_key = os.getenv('SECRET_KEY', uuid.uuid4().hex)
app.permanent_session_lifetime = timedelta(days=SESSION_DAYS)

# SocketIOの初期化
socketio = SocketIO(app, cors_allowed_origins="*") 

# 静的ファイルをキャッシュする設定。開発中はコメントアウト推奨。
# app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 2678400

bundle_css_files(app)


# ルートページのリダイレクト処理
@app.route('/', methods=['GET'])
def index():
    uid = session.get('uid')
    if uid is None:
        return redirect(url_for('login_view'))
    return redirect(url_for('channels_view'))


# サインアップページの表示
@app.route('/signup', methods=['GET'])
def signup_view():
    return render_template('auth/signup.html')


# サインアップ処理
@app.route('/signup', methods=['POST'])
def signup_process():
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')
    passwordConfirmation = request.form.get('password-confirmation')
    
    # デフォルトでは管理者ではない
    is_admin = False
    
    # 管理者用のシークレットコードを取得
    admin_secret = request.form.get('admin_secret', '')
    
    # シークレットコードが正しい場合のみ管理者になる
    ADMIN_SECRET = "Admin"
    if admin_secret == ADMIN_SECRET:
        is_admin = True
    
    if name == '' or email =='' or password == '' or passwordConfirmation == '':
        flash('空のフォームがあるようです')
    elif password != passwordConfirmation:
        flash('二つのパスワードの値が違っています')
    elif re.match(EMAIL_PATTERN, email) is None:
        flash('正しいメールアドレスの形式ではありません')
    else:
        uid = uuid.uuid4()
        password = hashlib.sha256(password.encode('utf-8')).hexdigest()
        registered_user = User.find_by_email(email)

        if registered_user != None:
            flash('既に登録されているようです')
        else:
            User.create(uid, name, email, password, is_admin)  # ユーザーを作成
            UserId = str(uid)   # ユーザーIDを文字列に変換
            session['uid'] = UserId # セッションにユーザーIDを保存
            return redirect(url_for('login_view'))
    return redirect(url_for('signup_process'))


# ログインページの表示
@app.route('/login', methods=['GET'])
def login_view():
    return render_template('auth/login.html')

# ログアウト
@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('login_view'))


# ログイン処理
@app.route('/login', methods=['POST'])
def login_process():
    email = request.form.get('email')
    password = request.form.get('password')

    if email =='' or password == '':
        flash('空のフォームがあるようです')
    else:
        user = User.find_by_email(email)
        if user is None:
            flash('このユーザーは存在しません')
        else:
            hashPassword = hashlib.sha256(password.encode('utf-8')).hexdigest() # パスワードをハッシュ化
            if hashPassword != user["password"]:  # ハッシュ化したパスワードとDBのパスワードを比較
                flash('パスワードが間違っています！')
            else:
                session['uid'] = user["uid"]    # セッションにユーザーIDを保存
                return redirect(url_for('channels_view'))   # チャンネル一覧ページにリダイレクト
    return redirect(url_for('login_view'))


# 1.管理者かどうか判定する関数
def is_admin(uid):  
    user = User.find_by_uid(uid)  # ユーザーIDからユーザー情報を取得
    if user is None:
        return False  # ユーザーが存在しない場合、adminではない
    return user.get('role') == 'admin'  # ユーザーの役割がadminかどうかを判定

# 管理者かユーザーかで利用可能なチャンネルを取得する関数
def get_available_channels(uid):  
    if is_admin(uid):  # 管理者の場合
        return Channel.get_all()  # 全チャンネルを取得
    else:  # ユーザーの場合
        return Channel.find_by_uid(uid)  # ユーザーが利用可能なチャンネルのみ取得(ユーザーが作成したチャンネル)


# チャンネル一覧の表示
@app.route('/channels', methods=['GET'])
def channels_view():
    uid = session.get('uid')    # セッションからユーザーIDを取得
    if uid is None:  # セッションにユーザーIDが保存されていない場合、ログインページにリダイレクト
        return redirect(url_for('login_view'))
    
    admin_status = is_admin(uid)  # 管理者かどうかを判定
    channels = get_available_channels(uid)  # 定義した関数を使用して利用可能なチャンネルを取得
    
    # 現在のチャンネルがない場合は、デフォルトでNoneとし、テンプレート側で処理
    current_channel = None
    # メッセージはデフォルトで空リストに
    messages = []
        
    return render_template(
        'channels.html', 
        channels=channels,    # 利用可能なチャンネルを表示するためにフロントに渡す
        uid=uid,
        admin_status=admin_status,  # 管理者かどうかの情報を渡す
        current_channel=current_channel,  # 現在選択中のチャンネル情報を渡す
        messages=messages,  # 空のメッセージリストを渡す
        is_admin=admin_status  # detail関数と整合性を取るため、is_adminも渡す
    )


# チャンネルの作成
@app.route('/channels', methods=['POST'])
def create_channel():
    uid = session.get('uid') # セッションからユーザーIDを取得

    if uid is None: # セッションにユーザーIDが保存されていない場合、ログインページにリダイレクト
        return redirect(url_for('login_view'))
    
    # ユーザーが管理者かどうかを確認
    admin_status = is_admin(uid)
    
    # 管理者でない場合、ユーザーが既にチャンネルを作成しているか確認
    if not admin_status:
        user_channels = Channel.find_by_uid(uid)
        if user_channels and len(user_channels) >= 1:
            error = '応募者は1つのチャンネルしか作成できません'
            return render_template('error/error.html', error_message=error)
    
    new_channel_name = request.form.get('channelTitle') # 入力されたフォームからチャンネル名を取得
    channel = Channel.find_by_name(new_channel_name)    # データベースにあるチャンネル名からチャンネルを取得
    if channel is None:     # チャンネルが存在しない場合
        new_channel_description = request.form.get('channelDescription') # 入力されたフォームからチャンネル説明を取得
        Channel.create(uid, new_channel_name, new_channel_description)  # チャンネルを作成
        
        # 新しく作成したチャンネルを探して、そのチャンネルページに移動する処理群
        new_channel = Channel.find_by_name(new_channel_name)
        if new_channel:
            return redirect(f'/channels/{new_channel["id"]}/messages') #GETリクエストで[チャンネルのチャット画面を表示して、アクセス権を確認する処理]にリダイレクト
        return redirect(url_for('channels_view'))   # 見つからない場合はチャンネル一覧ページにリダイレクト        
    else: # チャンネルが存在する場合、エラーメッセージを表示
        error = '既に同じ名前のチャンネルが存在しています'
        return render_template('error/error.html', error_message=error)


# チャンネルの更新
@app.route('/channels/update/<cid>', methods=['POST'])
def update_channel(cid):
    uid = session.get('uid')
    if uid is None:
        return redirect(url_for('login_view'))

    channel_name = request.form.get('channelTitle')
    channel_description = request.form.get('channelDescription')

    Channel.update(uid, channel_name, channel_description, cid)
    return redirect(f'/channels/{cid}/messages')


# チャンネルの削除 - 管理者と作成者のみ削除可能
@app.route('/channels/<int:cid>/delete/', methods=['POST'])
def delete_channel(cid):
    uid = session.get('uid')    # セッションからユーザーIDを取得
    if uid is None: # セッションにユーザーIDが保存されていない場合、ログインページにリダイレクト
        return redirect(url_for('login_view'))

    channel = Channel.find_by_cid(cid)  # チャンネルIDからチャンネルを取得
    admin_status = is_admin(uid)  # 管理者かどうかを判定

    # 管理者か、チャンネルの作成者のみ削除可能
    if not admin_status and channel["uid"] != uid:   
        flash('チャンネルは作成者または管理者のみ削除可能です')
    else:
        Channel.delete(cid) # チャンネルを削除
    return redirect(url_for('channels_view'))


# メッセージの投稿
@app.route('/channels/<cid>/messages', methods=['POST']) # POSTリクエストのみを受け取る
def create_message(cid): # URLからcid(チャンネルID)を取得
    uid = session.get('uid')
    if uid is None:
        return redirect(url_for('login_view'))

    message = request.form.get('message')  # フォームからメッセージを取得

    if message:
        # データベースにメッセージを保存
        Message.create(uid, cid, message)
        
        # 投稿したユーザー情報を取得
        user = User.find_by_uid(uid)
        
        # WebSocketで他のクライアントにリアルタイム通知
        jst = pytz.timezone('Asia/Tokyo')
        current_time = datetime.now(jst) # 現在の時刻を取得する公式メソッド(datetime.now)
        
        # socketio.emit('関数名', データ, room='送りたい部屋') サーバーからユーザーにデータを送信する関数
        socketio.emit('new_message', {
            'message': message,
            'user_name': user['name'],
            'formatted_time': current_time.strftime('%Y-%m-%d %H:%M'),  # 時刻あり（タイムラインのメッセージ用）
            'date_only': current_time.strftime('%Y-%m-%d')  # 日付のみ(メッセージのグループ化のキーに使用）
        }, room=f'channel_{cid}')

    return redirect(f'/channels/{cid}/messages')


# チャンネルのチャット画面を表示して、アクセス権を確認する処理
@app.route('/channels/<cid>/messages', methods=['GET'])
def detail(cid):
    uid = session.get('uid')  # セッションからユーザーIDを取得
    if uid is None: # セッションにユーザーIDが保存されていない場合、ログインページにリダイレクト
        return redirect(url_for('login_view'))

    admin_status = is_admin(uid)  # 管理者かどうかを判定
    current_channel = Channel.find_by_cid(cid)  # チャンネルIDからチャンネルを取得
    
    # ユーザーがアクセスできるチャンネルか確認
    channels = get_available_channels(uid)
    channel_ids = [ch['id'] for ch in channels]
    
    if int(cid) not in channel_ids and not admin_status:
        flash('このチャンネルにアクセスする権限がありません')
        return redirect(url_for('channels_view'))
    
    messages = Message.get_all(cid) # チャンネルIDから全メッセージを取得
    
    # メッセージを日付ごとにグループ化
    grouped_messages = {}
    jst = pytz.timezone('Asia/Tokyo')  # 日本のタイムゾーンを指定   
    for message in messages:
        # created_atをdatetimeに変換し、jstタイムゾーンに変換
        if isinstance(message['created_at'], str):
            # 文字列の場合はdatetimeに変換
            message_date = datetime.strptime(message['created_at'], '%Y-%m-%d %H:%M')
        else:
            # datetimeオブジェクトの場合はそのまま使用
            message_date = message['created_at']
        # タイムゾーンをJSTに設定
        message_date = message_date.replace(tzinfo=pytz.utc).astimezone(jst)
        
        # 日付のみを取得してグループ化のキーに使用
        date_key = message_date.strftime('%Y-%m-%d')
        
        # メッセージに日本時間の表示用フォーマットを追加
        message['formatted_time'] = message_date.strftime('%Y-%m-%d %H:%M')#各メッセージの辞書に新しいキー(formatted_time)を追加
        message['date_only'] = date_key # 各メッセージの辞書に新しいキー(date_only)を追加
        if date_key not in grouped_messages: # 新しい日付のキーがない場合は空のリストを作成=日付ごとのメッセージを入れる容器を作成
            grouped_messages[date_key] = [] 
        
        grouped_messages[date_key].append(message)  # メッセージを日付ごとのリストに追加

    # フロントに渡す
    return render_template(
        'channels.html', 
        channels=channels,  # チャンネル一覧
        messages=messages,  # 現在のチャンネルのメッセージ一覧
        grouped_messages=grouped_messages,  # 日付ごとにグループ化されたメッセージ
        current_channel=current_channel,  # 現在のチャンネル情報
        uid=uid,
        admin_status=admin_status,
        is_admin=admin_status  # 後方互換性のため残すが修正必要
    )

# メッセージの削除
@app.route('/channels/<cid>/messages/<message_id>', methods=['POST'])
def delete_message(cid, message_id):
    uid = session.get('uid')
    if uid is None:
        return redirect(url_for('login_view'))

    if message_id:
        Message.delete(message_id)
        # メッセージを削除した後、WebSocketで他のクライアントに通知
        # socketio.emit('イベント名', データ, room='送りたい部屋') サーバーからクライアントにデータを送信する関数
        socketio.emit('message_deleted', {
            'message_id': message_id
        }, room=f'channel_{cid}')
    return redirect(f'/channels/{cid}/messages')


# WebSocketイベントハンドラー
# サーバーに誰かがリアルタイム通信でつながったことを確認するためのイベント
@socketio.on('connect')
def on_connect():
    print('回線が接続されました') #接続されたらコンソールに表示

@socketio.on('disconnect')
def on_disconnect():
    print('回線が切断されました') #切断されたらコンソールに表示

@socketio.on('join_channel') #フロントからのエンドポイント
def on_join_channel(data): #フロントから受け取ったデータを引数(data)に入れる
    channel_id = data['channel_id'] # チャンネルIDを取得
    join_room(f'channel_{channel_id}') #join_room関数を使用して、チャンネルIDに基づいてそのIDの部屋に入る
    print(f'ユーザーがchannel {channel_id} に入りました') #コンソールに表示

@socketio.on('leave_channel') # チャンネルから離れる
def on_leave_channel(data):
    channel_id = data['channel_id']
    leave_room(f'channel_{channel_id}')
    print(f'ユーザーがchannel {channel_id} を出ました')


# エラーハンドラー
@app.errorhandler(404)
def page_not_found(error):
    return render_template('error/404.html'), 404

@app.errorhandler(500)
def internal_server_error(error):
    return render_template('error/500.html'), 500

if __name__ == '__main__':
    # SocketIOでアプリを起動
    socketio.run(app, host="0.0.0.0", debug=True, allow_unsafe_werkzeug=True)
