from flask import Flask, request, redirect, render_template, session, flash, abort, url_for
from datetime import timedelta
import hashlib
import uuid
import re
import os

from models import User, Channel, Message
from util.assets import bundle_css_files


# 定数定義
EMAIL_PATTERN = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
SESSION_DAYS = 30

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', uuid.uuid4().hex)
app.permanent_session_lifetime = timedelta(days=SESSION_DAYS)

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
            return redirect(url_for('channels_view'))
    return redirect(url_for('signup_process'))


# ログインページの表示
@app.route('/login', methods=['GET'])
def login_view():
    return render_template('auth/login.html')


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


# ログアウト
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_view'))


# 1.管理者かどうか判定する関数
def is_admin(uid):  
    user = User.find_by_uid(uid)  # クラスモデルからユーザーIDを取得
    if user is None:
        return False  # セッションにユーザーIDが保存されていない場合、adminではない
    return user.get('role') == 'admin'  # ユーザーの役割がadminかどうかを判定

# 管理者かユーザーかで利用可能なチャンネルを取得する関数
def get_available_channels(uid):  
    if is_admin(uid):  # 管理者の場合
        return Channel.get_all()  # 全チャンネルを取得
    else:  # ユーザーの場合
        return Channel.find_by_uid(uid)  # 自分のチャンネルだけを取得


# チャンネル一覧の表示
@app.route('/channels', methods=['GET'])
def channels_view():
    uid = session.get('uid')    # セッションからユーザーIDを取得
    if uid is None:  # セッションにユーザーIDが保存されていない場合、ログインページにリダイレクト
        return redirect(url_for('login_view'))
    else:
        admin_status = is_admin(uid)  # 管理者かどうかを判定
        
        if admin_status:
            channels = Channel.get_all()    # 全チャンネルを取得
            channels = Channel.query.order_by(Channel.created_at.desc()).all()
        else:
            channels = Channel.find_by_uid(uid)  # 自分のチャンネルだけを取得
                
        return render_template(
            'channels.html', 
            current_channel=channels,    # 利用可能なチャンネルを表示するためにフロントに渡す
            uid=uid,
            admin_status=admin_status # 管理者かどうかの情報を渡す
        )


# チャンネルの作成
@app.route('/channels', methods=['POST'])
def create_channel():
    uid = session.get('uid') # セッションからユーザーIDを取得

    if uid is None: # セッションにユーザーIDが保存されていない場合、ログインページにリダイレクト
        return redirect(url_for('login_view'))
    
    new_channel_name = request.form.get('channelTitle') # フォームからチャンネル名を取得
    channel = Channel.find_by_name(new_channel_name)    # データベースにあるチャンネル名からチャンネルを取得
    if channel is None:     # チャンネルが存在しない場合
        new_channel_description = request.form.get('channelDescription') # フォームからチャンネル説明を取得
        Channel.create(uid, new_channel_name, new_channel_description)  # チャンネルを作成
        return redirect(url_for('channels_view'))   # チャンネル一覧ページにリダイレクト        
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
@app.route('/channels/delete/<cid>', methods=['POST'])
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

    if message: # メッセージが空でない場合
        Message.create(uid, cid, message)  # メッセージを作成

    return redirect('/channels/{cid}/messages'.format(cid = cid)) #投稿した同じチャンネルにリダイレクト


# チャンネル詳細ページの表示
@app.route('/channels/<cid>/messages', methods=['GET'])
def detail(cid):
    uid = session.get('uid')  # セッションからユーザーIDを取得
    if uid is None: # セッションにユーザーIDが保存されていない場合、ログインページにリダイレクト
        return redirect(url_for('login_view'))

    admin_status = is_admin(uid)  # 管理者かどうかを判定
    current_channel = Channel.find_by_cid(cid)  # チャンネルIDからチャンネルを取得
    messages = Message.get_all(cid) # チャンネルIDから全メッセージを取得

    # フロントに渡す
    return render_template(
        'channels.html', 
        messages=messages, 
        current_channel=current_channel, 
        uid=uid,
        is_admin=admin_status  # 管理者かどうかの情報を追加
    )


# メッセージの削除
@app.route('/channels/<cid>/messages/<message_id>', methods=['POST'])
def delete_message(cid, message_id):
    uid = session.get('uid')
    if uid is None:
        return redirect(url_for('login_view'))

    if message_id:
        Message.delete(message_id)
    return redirect('/channels/{cid}/messages'.format(cid = cid))


@app.errorhandler(404)
def page_not_found(error):
    return render_template('error/404.html'),404


@app.errorhandler(500)
def internal_server_error(error):
    return render_template('error/500.html'),500


if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True)