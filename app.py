from flask import Flask, render_template, request, redirect, session
from flask import url_for
from authlib.integrations.flask_client import OAuth
from werkzeug.utils import secure_filename
from rag import ask_pdf
from datetime import timedelta
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "ragproject"

app.permanent_session_lifetime = timedelta(days=30)

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs("database", exist_ok=True)
os.makedirs("uploads", exist_ok=True)

oauth = OAuth(app)

google = oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"}
)

conn = sqlite3.connect("database/users.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT,
email TEXT UNIQUE,
password TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS conversations(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER,
title TEXT,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS chats(
id INTEGER PRIMARY KEY AUTOINCREMENT,
conversation_id INTEGER,
user_id INTEGER,
question TEXT,
answer TEXT,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()
conn.close()

@app.route("/")
def home():
    return render_template("login.html")
# ---------------- Register ----------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect("database/users.db")
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO users(name,email,password) VALUES(?,?,?)",
            (name, email, password)
        )

        conn.commit()
        conn.close()

        return redirect("/")
    return render_template("register.html")


 # ---------------- Login ----------------

@app.route("/login", methods=["POST"])
def login():

    email = request.form["email"]
    password = request.form["password"]

    conn = sqlite3.connect("database/users.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE email=? AND password=?",
        (email, password)
    )

    user = cursor.fetchone()

    conn.close()

    if user:

        session.permanent = True
        session["user_id"] = user[0]
        session["user"] = user[1]
        session["conversation_id"] = None

        return redirect("/dashboard")

    return "Invalid Login"


# ---------------- Google Login ----------------

@app.route("/google_login")
def google_login():

    return google.authorize_redirect(
         "https://rag-project-1mz4.onrender.com/google_callback"
    )


@app.route("/google_callback")
def google_callback():

    token = google.authorize_access_token()
    info = token["userinfo"]

    name = info["name"]
    email = info["email"]

    conn = sqlite3.connect("database/users.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE email=?",
        (email,)
    )

    user = cursor.fetchone()

    if user:

        session["picture"] = info["picture"]
        session.permanent = True
        session["user_id"] = user[0]
        session["user"] = user[1]
        session["conversation_id"] = None

    else:

        cursor.execute(
            "INSERT INTO users(name,email,password) VALUES(?,?,?)",
            (name,email,"")
        )

        conn.commit()

        session["user_id"] = cursor.lastrowid
        session["user"] = name
        session["conversation_id"] = None

    conn.close()

    return redirect("/dashboard")


# ---------------- Dashboard ----------------

@app.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect("/")

    pdfs = os.listdir("uploads")

    conn = sqlite3.connect("database/users.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id,title
    FROM conversations
    WHERE user_id=?
    ORDER BY id DESC
    """,
    (session["user_id"],))

    conversations = cursor.fetchall()

    history = []

    if session.get("conversation_id"):

        cursor.execute("""
        SELECT question,answer
        FROM chats
        WHERE conversation_id=?
        ORDER BY id ASC
        """,
        (session["conversation_id"],))

        history = cursor.fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        username=session["user"],
        pdfs=pdfs,
        history=history,
        conversations=conversations
    )
# ---------------- Upload ----------------

@app.route("/upload", methods=["POST"])
def upload():

    files = request.files.getlist("pdf")

    for file in files:

        if file.filename != "":

            filename = secure_filename(file.filename)

            file.save(
                os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    filename
                )
            )

    return redirect("/dashboard")


# ---------------- Ask ----------------

@app.route("/ask", methods=["POST"])
def ask():

    if "user" not in session:
        return redirect("/")

    question = request.form["question"]

    conn = sqlite3.connect("database/users.db")
    cursor = conn.cursor()

    # Active conversation lekapothe create cheyyi
    if session.get("conversation_id") is None:

        cursor.execute("""
        INSERT INTO conversations(user_id,title)
        VALUES(?,?)
        """,
        (
            session["user_id"],
            question[:30]
        ))

        conn.commit()

        session["conversation_id"] = cursor.lastrowid

    answer = ask_pdf(question)

    cursor.execute("""
    INSERT INTO chats(
    conversation_id,
    user_id,
    question,
    answer
    )
    VALUES(?,?,?,?)
    """,
    (
        session["conversation_id"],
        session["user_id"],
        question,
        answer
    ))

    conn.commit()
    conn.close()

    return redirect("/dashboard")


# ---------------- New Chat ----------------

@app.route("/new_chat")
def new_chat():

    if "user" not in session:
        return redirect("/")

    # Blank chat open avvali
    session["conversation_id"] = None

    return redirect("/dashboard")


# ---------------- Open Chat ----------------

@app.route("/chat/<int:id>")
def open_chat(id):

    if "user" not in session:
        return redirect("/")

    session["conversation_id"] = id

    return redirect("/dashboard")

#---------------delete------------------------

@app.route("/delete_pdf/<filename>")
def delete_pdf(filename):

    if "user" not in session:
        return redirect("/")

    path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

    if os.path.exists(path):
        os.remove(path)

    return redirect("/dashboard")

#-------------------delete history--------

@app.route("/delete_history")
def delete_history():

    if "user" not in session:
        return redirect("/")

    conn = sqlite3.connect("database/users.db")
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM chats WHERE user_id=?",
        (session["user_id"],)
    )

    cursor.execute(
        "DELETE FROM conversations WHERE user_id=?",
        (session["user_id"],)
    )

    conn.commit()
    conn.close()

    session["conversation_id"] = None

    return redirect("/dashboard")
#--------------delete chat---------------
@app.route("/delete_chat/<int:id>")
def delete_chat(id):

    if "user" not in session:
        return redirect("/")

    conn = sqlite3.connect("database/users.db")
    cursor = conn.cursor()

    # Delete messages
    cursor.execute(
        "DELETE FROM chats WHERE conversation_id=?",
        (id,)
    )

    # Delete conversation
    cursor.execute(
        "DELETE FROM conversations WHERE id=?",
        (id,)
    )

    conn.commit()
    conn.close()

    if session.get("conversation_id") == id:
        session["conversation_id"] = None

    return redirect("/dashboard")


# ---------------- Logout ----------------

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# ---------------- Run ----------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)