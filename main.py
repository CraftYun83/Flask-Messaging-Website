from flask import Flask, request, render_template, redirect
from http import HTTPStatus
from threading import Thread
import random
from flask_sse import sse
import string
from pymongo import MongoClient
from cryptography.fernet import Fernet
import time

cluster = MongoClient("<DATABASE URL>")
collection = cluster.get_database("Flask").get_collection("credentials")
logscollection = cluster.get_database("Flask").get_collection("logs")
app = Flask(__name__)
key = Fernet.generate_key()
cipher_suite = Fernet(key)
app.config["REDIS_URL"] = "redis://localhost:6379"
app.register_blueprint(sse, url_prefix='/stream')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    try:
        username = cipher_suite.decrypt(request.cookies.get('un').encode("utf-8")).decode("utf-8")
        password = cipher_suite.decrypt(request.cookies.get('pw').encode("utf-8")).decode("utf-8")

        if collection.count_documents({"username": username, "password": password}) == 0:
            return "Did you really try forge cookies????"
        elif collection.count_documents({"username": username, "password": password}) == 1:
            return redirect("/home")
    except Exception:
        return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_request():
    username = request.form['username']
    password = request.form['password']
    if collection.count_documents({"username": username}) == 0:
      response = redirect("/")
      response.set_cookie("dne", b"true")
      return response
    if collection.find_one({"username": username})["password"] == password:
        response = redirect("/home")
        response.set_cookie("li", bytes(True))
        response.set_cookie("hb", "aGFtYnVyZ2Vy".encode("utf-8"))
        response.set_cookie("ck", "Y29va2ll".encode("utf-8"))
        response.set_cookie("un", cipher_suite.encrypt(username.encode("utf-8")).decode("utf-8"))
        response.set_cookie("pw", cipher_suite.encrypt(password.encode("utf-8")).decode("utf-8"))
        return response
    else:
      response = redirect("/")
      response.set_cookie("wc", b"true")
      return response

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/register', methods=['POST'])
def register_request():
    email = request.form['email']
    username = request.form['username']
    password = request.form['password']
    if collection.count_documents({"username": username}) == 1:
      response = redirect("/")
      response.set_cookie("ae", b"true")
      return response
      
    collection.insert_one({"_id": str(''.join(random.choices(string.ascii_uppercase + string.digits + string.ascii_lowercase, k = 16))), "email": email, "username": username, "password": password})
    response = redirect("/home")
    response.set_cookie("li", bytes(True))
    response.set_cookie("hb", "aGFtYnVyZ2Vy".encode("utf-8"))
    response.set_cookie("ck", "Y29va2ll".encode("utf-8"))
    response.set_cookie("un", cipher_suite.encrypt(username.encode("utf-8")))
    response.set_cookie("pw", cipher_suite.encrypt(password.encode("utf-8")))
    return response

@app.route('/home')
def home():
    try:
        username = cipher_suite.decrypt(request.cookies.get('un').encode("utf-8")).decode("utf-8")
        password = cipher_suite.decrypt(request.cookies.get('pw').encode("utf-8")).decode("utf-8")

        if collection.count_documents({"username": username, "password": password}) == 0:
            return "Did you really try forge cookies????"
        elif collection.count_documents({"username": username, "password": password}) == 1:
            Thread(target=send_messages, args=(logscollection.find({"recipient": cipher_suite.decrypt(request.cookies.get('un').encode("utf-8")).decode("utf-8")}),)).start()
            return render_template("home.html")
    except Exception:
        response = redirect("/")
        response.set_cookie("nli", b"true")
        return response

@app.route("/logout")
def logout():
    try:
        username = cipher_suite.decrypt(request.cookies.get('un').encode("utf-8")).decode("utf-8")
        password = cipher_suite.decrypt(request.cookies.get('pw').encode("utf-8")).decode("utf-8")

        if collection.count_documents({"username": username, "password": password}) == 0:
            return "Did you really try forge cookies????"
        elif collection.count_documents({"username": username, "password": password}) == 1:
            response = redirect("/")
            response.set_cookie("wp", b"true")
            return response
    except Exception:
        response = redirect("/")
        response.set_cookie("nli", b"true")
        return response

@app.route("/delete")
def delete():
    try:
        username = cipher_suite.decrypt(request.cookies.get('un').encode("utf-8")).decode("utf-8")
        password = cipher_suite.decrypt(request.cookies.get('pw').encode("utf-8")).decode("utf-8")

        if collection.count_documents({"username": username, "password": password}) == 0:
            return "Did you really try forge cookies????"
        elif collection.count_documents({"username": username, "password": password}) == 1:
            collection.delete_one({"username": username, "password": password})
            response = redirect("/")
            response.set_cookie("wp", b"true")
            response.set_cookie("dl", b"true")
            return response
    except Exception:
        response = redirect("/")
        response.set_cookie("nli", b"true")
        return response

def alertmessage(message):
    time.sleep(1)
    with app.app_context():
        sse.publish({"message": message}, type='greeting')
    
def send_messages(posts):
    time.sleep(1)
    with app.app_context():
        message = ""
        for post in posts:
            message += f'-post <h4>From: {post["sender"]}</h4><h3>Message: {post["message"]}</h3>'
            message += "<hr>"
            sse.publish({"message": message}, type='greeting')

@app.route("/message", methods=["POST"])
def message():
        username = cipher_suite.decrypt(request.cookies.get('un').encode("utf-8")).decode("utf-8")
        message = str(request.form['message'])
        recipient = str(request.form['recipient'])
        if collection.count_documents({"username": recipient}) == 0:
            response = redirect("/home")
            Thread(target=alertmessage, args=("This user does not exist!",)).start()
            return response
        else:
            log = {
                "sender": username,
                "recipient": recipient,
                "message": message
            }
            logscollection.insert_one(log)

            Thread(target=alertmessage, args=("Succesfully sent message!",)).start()
            return redirect("/home")

app.run(host="0.0.0.0", debug=True)