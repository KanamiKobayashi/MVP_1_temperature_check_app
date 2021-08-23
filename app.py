#app.py
#MVP12_3_3参照
import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, g, flash, session
import pandas as pd
import sqlite3
from datetime import datetime
import db # 自作モジュール
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config.from_object(__name__)
 
app.config.update(dict(
    DATABASE=os.path.join(app.root_path, './db/db.sqlite3'),
    SECRET_KEY='foo-baa',
))

def connect_db(): # get_db()中で使用する
    """ データベースに接続します """
    con = sqlite3.connect(app.config['DATABASE'])
    con.row_factory = sqlite3.Row
    return con

def get_db():
    """ connectionを取得します """
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db

today = (datetime.now().strftime('%a %d %B'))

@app.route("/", methods=["GET","POST"])
def main():
    if request.method == "GET":
        return render_template("index.html",#変更したい箇所auth/register.html
                                today=today)

    if request.method == "POST":

        name = request.form.get("name")
        gakunen = request.form.get("gakunen")
        temp = request.form.get("temp")

        # SQLデータベース
        con = get_db()
        pk = db.insert(con, name, gakunen, temp)
        results = db.select_all(con)

        # https://blog.imind.jp/entry/2019/12/28/115641
        df = pd.read_sql('select name, gakunen, temp from results', con=con)
        filepath = "./csv/" + datetime.now().strftime("%Y%m%d%H%M%S_data") + ".csv"
        df.to_csv(filepath, index=False)
        #csvは送信を押した数だけ作成されていく、上書き更新は可能か？
       
        return render_template("submit.html",
                                #"index.html", 
                                #results=results,
                                #message="データを追加しました",
                                message_after_submit="ご連絡ありがとうございました")
                                #today=today)

# 終了したとき db 接続を close する
@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()

#登録registerの部分
@app.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':#入力データの検証を開始
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        error = None

        if not username:
            error = 'Username is required.'
        elif not password:
            error = 'Password is required.'
        elif db.execute(
            'SELECT id FROM user WHERE username = ?', (username,)
        ).fetchone() is not None:
            error = f"User {username} is already registered."

        print(error)
        if error is None: # ユーザ名とパスワードが入力され、既存ユーザ出ない場合、下記でユーザをデータベースにinsert(登録)
            db.execute(
                'INSERT INTO user (username, password) VALUES (?, ?)',
                (username, generate_password_hash(password)) 
            )
            db.commit()
            return redirect(url_for('login'))#そのあとログイン画面へ('！！！ここにはhtmlの名前ではなく、routeのdefの名前を書く')
            print("Register success.")

        flash(error)

    return render_template('auth/register.html') #ユーザが最初にページを訪れた場合 or エラーで再度画面を表示する場合

#ログイン
@app.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        error = None
        user = db.execute(
            'SELECT * FROM user WHERE username = ?', (username,)
        ).fetchone()

        if user is None:
            error = 'Incorrect username.'
        elif not check_password_hash(user['password'], password):
            error = 'Incorrect password.'

        if error is None:# 何もエラーがなかった場合（ユーザーネーム、パスワードがDBで確認された場合）
            session.clear()
            session['user_id'] = user['id']#56のsqliteデータベースから取得した情報idをsession['user_id']に代入
            return redirect(url_for('main'))
            print("login success.")

        flash(error)

    return render_template('auth/login.html')

#リクエスト毎にユーザがログイン状態か否かを判定するメソッドを作成
@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute(
            'SELECT * FROM user WHERE id = ?', (user_id,)
        ).fetchone()

#ログアウト
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main'))

#他のviewでの認証の要求
def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('login'))

        return view(**kwargs)

    return wrapped_view


###




if __name__ == '__main__':
    app.run(debug=True,  host='0.0.0.0', port=1005) # ポートの変更