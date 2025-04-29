from flask import Blueprint, render_template, request, redirect, url_for

user = Blueprint("user", __name__, template_folder = "templates")

# TODO: MUDAR PARA DB
users = {   
    "user1" : "1234",
    "user2" : "1234"
}

@user.route("/")
def index():
    return render_template("login.html")

@user.route("/validate_credential", methods = ["POST"])
def validateCredential():
    global users
    if request.method == "POST":
        user = request.form["user"]
        password = request.form["password"]
        if user in users and users[user] == password:
            return render_template("home.html")
        else:
            return render_template("errors/401.html")
    else:
        return render_template("login.html")
    

@user.route("/register_user")
def registerUser():
    return render_template("register_user.html")    

@user.route("/create_user", methods = ["POST"])
def createUser():
    global users
    if request.method == "POST":
        user = request.form["user"]
        password = request.form["password"]
    else:
        user = request.args.get("user", None)
        password = request.args.get("passowrd", None)
    users[user] = password
    return "<h1> Usuário adicionado </h1>"
        