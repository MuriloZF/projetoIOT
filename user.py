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
            return "<h1> Usuário ou senha inválidos! </h1>"
    else:
        return render_template("login.html")