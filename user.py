from flask import Blueprint, render_template, request, redirect, url_for

user = Blueprint("user", __name__, template_folder = "templates")

# TODO: MUDAR PARA DB
users = {   
    "user1" : "1234",
    "user2" : "1234"
}

admins = {
    "admin1" : "1234",
}

privilegioSession = None

@user.route("/")
def index():
    return render_template("login.html")

@user.route("/home")
def home():
    return render_template("home.html", privilegio = privilegioSession)

@user.route("/validate_credential", methods = ["POST"])
def validateCredential():
    global users
    global privilegioSession
    if request.method == "POST":
        user = request.form["user"]
        password = request.form["password"]
        if user in users and users[user] == password or user in admins and admins[user]== password:
            if user in admins:
                privilegio = 1
                privilegioSession = 1
            else:
                privilegio = 0
                privilegioSession = 0
            print(privilegioSession)    
            return render_template("home.html", privilegio = privilegio)
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
        privilegio = request.form["privilégio"]
    else:
        user = request.args.get("user", None)
        password = request.args.get("password", None)
    if privilegio == "1":
        admins[user] = password
    elif privilegio == "0":
        users[user] = password
    return render_template("manage_user.html", device = users, adm = admins)

@user.route("/manage_user")
def manageUser():
    return render_template("manage_user.html", device = users, adm = admins)

@user.route("/del_user", methods = ["GET","POST"])
def delUser():
    global users
    if request.method == "POST":
        user = request.form['user']
    else:
        user = request.args.get['user', None]
    users.pop(user)
    return render_template("manage_user.html", device = users, adm = admins)