from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models.user.user import User
from models.db import db
from functools import wraps

user_bp = Blueprint("user", __name__, template_folder="templates")

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
    all_users = User.query.filter_by(role="user").all()
    user_data = []
    for user in all_users:
            user_data.append({
                'id' : user.id,
                'username': user.username,
                'role': user.role
            })
    
    all_admins = User.query.filter_by(role="admin").all()
    admin_data = []
    for admin in all_admins:
        admin_data.append({
            'id' : admin.id,
            'username' : admin.username,
            'role' : admin.role
        })
    
    all_history = User.query.filter_by(role="history").all()
    history_data = []
    for history in all_history:
        history_data.append({
            'id': history.id,
            'username' : history.username,
            'role' : history.role
        })

    all_users = history_data + user_data + admin_data
    return render_template("manage_user.html", users=all_users)

@admin_required
@user_bp.route("/delete/<username>", methods=["POST"])
def delete_user(username):
    user = User.query.filter_by(username=username).first() 
    if username == session.get("user_id"):
        flash("Você não pode remover a si mesmo", "error")
    elif user:
        db.session.delete(user)
        db.session.commit()
        flash(f"Usuário: {user.username} foi removido com sucesso.", "success")
    
    return redirect(url_for("user.manage_user_page"))

@admin_required
@user_bp.route("/edit/<username>", methods=["GET", "POST"])
def edit_user_page(username):
    user = User.query.filter_by(username=username).first()    
    if request.method == "POST":
        new_username = request.form.get("username")
        new_password = request.form.get("password")
        new_privilege = request.form.get("privilege", "0")
        
        if new_username:
            current_user = User.query.filter_by(username=new_username).first()
            if current_user and current_user.username != username:
                error_message = f"Usuário {new_username} já existe. Tente outro nome."
                return render_template("edit_user.html", user=user, error=error_message)
        user.username = new_username
       
        if new_password:
            user.password = new_password
       
        if new_privilege:
            if new_privilege == "1":
                user.role = "admin"
            elif new_privilege == "2":
                user.role = "history"
            else:
                user.role = "user"
        db.session.commit()

        # Update session if editing own account
        if username == session.get("user_id"):
            session["user_id"] = new_username
        
        return redirect(url_for("user.manage_user_page"))
    
    # GET request - show edit form
    return render_template("edit_user.html", user=user)