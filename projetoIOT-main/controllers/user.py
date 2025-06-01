from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user 
from models.models import db, User

user_bp = Blueprint("user", __name__, template_folder="../templates")

@user_bp.route("/")
def index_redirect_to_login():
    if current_user.is_authenticated:
        return redirect(url_for("home_page_dashboard"))
    return redirect(url_for("user.login_page"))

@user_bp.route("/login", methods=["GET", "POST"])
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for("home_page_dashboard"))
        
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        remember = True if request.form.get("remember") else False
        
        user = User.query.filter_by(username=username).first()
        
        if not user or not user.check_password(password):
            flash("Credenciais inválidas. Verifique seu usuário e senha.", "error")
            return redirect(url_for("user.login_page"))
            
        login_user(user, remember=remember)
        flash("Login realizado com sucesso!", "success")
        
        next_page = request.args.get("next")
        if not next_page or not next_page.startswith("/") or next_page == url_for("user.login_page"):
             next_page = url_for("home_page_dashboard")
        return redirect(next_page)

    return render_template("login.html")

@user_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logout realizado com sucesso.", "info")
    return redirect(url_for("user.login_page"))

# Modified: Allow logged-in admins to access this page to register others
@user_bp.route("/register", methods=["GET", "POST"])
def register_user_page():
    # If user is logged in but NOT admin, redirect them away
    if current_user.is_authenticated and not current_user.is_admin:
        flash("Você já está logado. Administradores podem registrar novos usuários aqui.", "info")
        return redirect(url_for("home_page_dashboard"))
    
    # If it's an admin accessing the page, they can proceed
    # If it's an unauthenticated user, they can proceed

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        
        # Check if privilege field exists (only shown to admins)
        privilege = "0" # Default to non-admin
        if current_user.is_authenticated and current_user.is_admin:
            privilege = request.form.get("privilegio", "0")
        
        is_new_user_admin = (privilege == "1")

        if not username or not password or not confirm_password:
            flash("Todos os campos são obrigatórios", "error")
            return render_template("register_user.html", error="Todos os campos são obrigatórios", username=username) 
            
        if password != confirm_password:
            flash("As senhas não coincidem.", "error")
            return render_template("register_user.html", error="As senhas não coincidem.", username=username)

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash(f"Usuário {username} já existe", "error")
            return render_template("register_user.html", error=f"Usuário {username} já existe", username=username)
        
        # Create new user with appropriate admin status
        new_user = User(username=username, is_admin=is_new_user_admin)
        new_user.set_password(password)
        
        try:
            db.session.add(new_user)
            db.session.commit()
            # Different flash message depending on who registered
            if current_user.is_authenticated and current_user.is_admin:
                 flash(f"Usuário {username} ({'Admin' if is_new_user_admin else 'Usuário'}) registrado com sucesso!", "success")
                 return redirect(url_for("user.manage_user_page")) # Redirect admin to manage page
            else:
                 flash(f"Usuário {username} registrado com sucesso! Faça o login.", "success")
                 return redirect(url_for("user.login_page")) # Redirect public user to login
        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao registrar usuário: {e}", "error")
            return render_template("register_user.html", error=f"Erro ao registrar usuário: {e}", username=username)

    # GET request - Pass admin status to template
    is_admin_viewing = current_user.is_authenticated and current_user.is_admin
    return render_template("register_user.html", is_admin_viewing=is_admin_viewing)

# --- Admin User Management Routes --- (No changes needed below for this fix)

@user_bp.route("/manage")
@login_required
def manage_user_page():
    if not current_user.is_admin:
        flash("Acesso não autorizado.", "error")
        return redirect(url_for("home_page_dashboard"))
    
    all_users = User.query.all()
    return render_template("manage_user.html", users=all_users)

@user_bp.route("/delete/<int:user_id>", methods=["POST"])
@login_required
def delete_user(user_id):
    if not current_user.is_admin:
        flash("Acesso não autorizado.", "error")
        return redirect(url_for("user.manage_user_page")) 
    
    user_to_delete = User.query.get(user_id)
    
    if not user_to_delete:
        flash("Usuário não encontrado.", "error")
        return redirect(url_for("user.manage_user_page"))

    if user_to_delete.id == current_user.id:
        flash("Você não pode remover a si mesmo.", "error")
        return redirect(url_for("user.manage_user_page"))
    
    try:
        db.session.delete(user_to_delete)
        db.session.commit()
        flash(f"Usuário {user_to_delete.username} removido com sucesso.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao remover usuário: {e}", "error")
        
    return redirect(url_for("user.manage_user_page"))

@user_bp.route("/edit/<int:user_id>", methods=["GET", "POST"])
@login_required
def edit_user_page(user_id):
    if not current_user.is_admin:
        flash("Acesso não autorizado.", "error")
        return redirect(url_for("home_page_dashboard"))
        
    user_to_edit = User.query.get_or_404(user_id) 
    
    if request.method == "POST":
        new_username = request.form.get("username")
        new_password = request.form.get("password")
        new_privilege = request.form.get("privilegio", "0")
        
        if not new_username:
            flash("Nome de usuário é obrigatório.", "error")
            return render_template("edit_user.html", user=user_to_edit, error="Nome de usuário é obrigatório.") 

        if new_username != user_to_edit.username:
            existing_user = User.query.filter(User.username == new_username, User.id != user_id).first()
            if existing_user:
                flash(f"Nome de usuário {new_username} já está em uso.", "error")
                return render_template("edit_user.html", user=user_to_edit, error=f"Nome de usuário {new_username} já está em uso.")
        
        user_to_edit.username = new_username
        user_to_edit.is_admin = (new_privilege == "1")
        
        if new_password:
            user_to_edit.set_password(new_password)
            
        try:
            db.session.commit()
            flash(f"Usuário {user_to_edit.username} atualizado com sucesso!", "success")
            return redirect(url_for("user.manage_user_page"))
        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao atualizar usuário: {e}", "error")
            return render_template("edit_user.html", user=user_to_edit, error=f"Erro ao atualizar usuário: {e}")

    return render_template("edit_user.html", user=user_to_edit)

