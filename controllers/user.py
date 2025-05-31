from flask import Blueprint, render_template, request, redirect, url_for, session
from models.user.user import User
from models.db import db
from functools import wraps

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

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Acesso não autorizado", "error")
            return redirect(url_for("user.login_page"))
        return f(*args, **kwargs)
    return decorated_function

@user_bp.route("/")
def index_redirect_to_login():
    return redirect(url_for("user.login_page"))

@user_bp.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        user = User.query.filter_by(username=username, password=password).first()

        if user:
            print(f"Usuário logado: {user.username}, role: {user.role}")
            session["user_id"] = user.username
            session["role"] = user.role
            return redirect(url_for("home_page_dashboard"))
        else:
            return render_template("login.html", error="Credenciais inválidas")
    
    return render_template("login.html")

@user_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("user.login_page"))

@admin_required
@user_bp.route("/register", methods=["GET", "POST"])
def register_user_page():
    
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        new_user = User(username=username, password=password, role="user")
        db.session.add(new_user)
        db.session.commit()
        
        return redirect(url_for("user.manage_user_page"))
    
    return render_template("register_user.html")

@admin_required
@user_bp.route("/manage")
def manage_user_page():
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

@admin_required
@user_bp.route("/delete/<username>", methods=["POST"])
def delete_user(username): 
    if username == session.get("user_id"):
        flash("Você não pode remover a si mesmo", "error")
    elif username in users_dict:
        users_dict.pop(username)
    elif username in admins_dict:
        admins_dict.pop(username)
    
    return redirect(url_for("user.manage_user_page"))

@admin_required
@user_bp.route("/edit/<username>", methods=["GET", "POST"])
def edit_user_page(username):    
    if request.method == "POST":
        new_username = request.form.get("username")
        new_password = request.form.get("password")
        new_privilege = request.form.get("privilege", "0")
        
        if not new_username or not new_password:
            return render_template("edit_user.html", 
                                user={"username": username, "type": "admin" if username in admins_dict else "user"}, 
                                error="Todos os campos são obrigatórios")
        
        # Check if username is being changed to one that already exists (excluding current user)
        if (new_username != username and 
            (new_username in users_dict or new_username in admins_dict)):
            return render_template("edit_user.html", 
                                user={"username": username, "type": "admin" if username in admins_dict else "user"}, 
                                error=f"Usuário {new_username} já existe")
        
        # Remove from old dictionary
        if username in users_dict:
            users_dict.pop(username)
        elif username in admins_dict:
            admins_dict.pop(username)
        
        # Add to new dictionary based on privilege
        if new_privilege == "1":
            admins_dict[new_username] = new_password
        else:
            users_dict[new_username] = new_password
        
        # Update session if editing own account
        if username == session.get("user_id"):
            session["user_id"] = new_username
        
        return redirect(url_for("user.manage_user_page"))
    
    # GET request - show edit form
    user_type = "admin" if username in admins_dict else "user"
    return render_template("edit_user.html", 
                         user={"username": username, "type": user_type})