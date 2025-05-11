from flask import Blueprint, render_template, request, redirect, url_for, session

user_bp = Blueprint("user", __name__, template_folder="templates")

# User storage (replace with database in production)
users_dict = {   
    "user1": "1234",
    "user2": "1234"
}

admins_dict = {
    "admin1": "1234",
    "admin2": "1234",
    "admin3": "1234"
}

@user_bp.route("/")
def index_redirect_to_login():
    return redirect(url_for("user.login_page"))

@user_bp.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        if username in admins_dict and admins_dict[username] == password:
            session["privilegio"] = 1
            session["user_id"] = username
            return redirect(url_for("home_page_dashboard"))
        elif username in users_dict and users_dict[username] == password:
            session["privilegio"] = 0
            session["user_id"] = username
            return redirect(url_for("home_page_dashboard"))
        else:
            return render_template("login.html", error="Credenciais inválidas")
    
    return render_template("login.html")

@user_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("user.login_page"))

@user_bp.route("/register", methods=["GET", "POST"])
def register_user_page():
    if session.get("privilegio") != 1:
        return redirect(url_for("user.login_page"))
    
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        privilege = request.form.get("privilege", "0")
        
        if not username or not password:
            return render_template("register_user.html", error="Todos os campos são obrigatórios")
        
        if username in users_dict or username in admins_dict:
            return render_template("register_user.html", error=f"Usuário {username} já existe")
        
        if privilege == "1":
            admins_dict[username] = password
        else:
            users_dict[username] = password
        
        return redirect(url_for("user.manage_user_page"))
    
    return render_template("register_user.html")

@user_bp.route("/manage")
def manage_user_page():
    if session.get("privilegio") != 1:
        return redirect(url_for("user.login_page"))
    
    # Combine both dictionaries with type information
    all_users = []
    for username, password in users_dict.items():
        all_users.append({
            'id': username,
            'username': username,
            'type': 'user',
            'password': password  # Note: In production, don't expose passwords
        })
    
    for username, password in admins_dict.items():
        all_users.append({
            'id': username,
            'username': username,
            'type': 'admin',
            'password': password  # Note: In production, don't expose passwords
        })
    
    return render_template("manage_user.html", users=all_users)

@user_bp.route("/delete/<username>", methods=["POST"])
def delete_user(username):
    if session.get("privilegio") != 1:
        return redirect(url_for("user.login_page"))
    
    if username in users_dict:
        users_dict.pop(username)
    elif username in admins_dict and username != session.get("user_id"):
        admins_dict.pop(username)
    
    return redirect(url_for("user.manage_user_page"))