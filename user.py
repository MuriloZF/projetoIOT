from flask import Blueprint, render_template, request, redirect, url_for, session

user_bp = Blueprint("user", __name__, template_folder="templates")

# TODO: Replace with database in future
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
    """Redirect root URL to login page"""
    return redirect(url_for("user.login_page"))

@user_bp.route("/login", methods=["GET", "POST"])
def login_page():
    """Handle user login"""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        if username in admins_dict and admins_dict[username] == password:
            session["privilegio"] = 1
            session["user_id"] = username
            print(f"Admin login successful: {username}, privilegio: {session.get('privilegio')}")
            return redirect(url_for("home_page_dashboard"))
        elif username in users_dict and users_dict[username] == password:
            session["privilegio"] = 0
            session["user_id"] = username
            print(f"User login successful: {username}, privilegio: {session.get('privilegio')}")
            return redirect(url_for("home_page_dashboard"))
        else:
            print(f"Login failed for username: {username}")
            return render_template("login.html", error="Credenciais inválidas")
    
    return render_template("login.html")

@user_bp.route("/logout")
def logout():
    """Handle user logout"""
    session.pop("user_id", None)
    session.pop("privilegio", None)
    print("User logged out.")
    return redirect(url_for("user.login_page"))
    
@user_bp.route("/register", methods=["GET", "POST"])
def register_user_page():
    """Handle user registration (admin only)"""
    if session.get("privilegio") != 1:
        if "user_id" in session:
            return redirect(url_for("home_page_dashboard")) 
        return redirect(url_for("user.login_page"))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        privilegio = request.form.get("privilegio")

        # Validate inputs
        if not username or not password or privilegio is None:
            return render_template("register_user.html", 
                                error="Todos os campos são obrigatórios.",
                                users=users_dict, 
                                admins=admins_dict)

        # Check if user already exists
        if username in users_dict or username in admins_dict:
            return render_template("register_user.html", 
                                error=f"Usuário {username} já existe.",
                                users=users_dict, 
                                admins=admins_dict)

        try:
            privilegio = int(privilegio)
            if privilegio == 1:
                admins_dict[username] = password
                print(f"New admin registered: {username}")
            elif privilegio == 0:
                users_dict[username] = password
                print(f"New user registered: {username}")
            else:
                return render_template("register_user.html", 
                                    error="Privilégio inválido.",
                                    users=users_dict, 
                                    admins=admins_dict)
            
            return redirect(url_for("user.manage_user_page"))
        
        except ValueError:
            return render_template("register_user.html", 
                                error="Privilégio inválido.",
                                users=users_dict, 
                                admins=admins_dict)
    
    # GET request - show registration form
    return render_template("register_user.html", 
                         users=users_dict, 
                         admins=admins_dict)

@user_bp.route("/manage")
def manage_user_page():
    """Display user management page (admin only)"""
    if session.get("privilegio") != 1:
        if "user_id" in session:
            return redirect(url_for("home_page_dashboard")) 
        return redirect(url_for("user.login_page"))
        
    return render_template("manage_user.html", 
                         users=dict(users_dict), 
                         admins=dict(admins_dict))

@user_bp.route("/delete/<username_to_delete>", methods=["POST"])
def delete_user_action(username_to_delete):
    """Handle user deletion (admin only)"""
    if session.get("privilegio") != 1:
        return redirect(url_for("user.login_page"))

    if username_to_delete in users_dict:
        users_dict.pop(username_to_delete)
        print(f"User deleted: {username_to_delete}")
    elif username_to_delete in admins_dict:
        if session.get("user_id") == username_to_delete:
            print(f"Admin attempted to delete self: {username_to_delete}")
            # Optionally: Add error message that admin can't delete themselves
        else:
            admins_dict.pop(username_to_delete)
            print(f"Admin deleted: {username_to_delete}")    
    else:
        print(f"Attempted to delete non-existent user: {username_to_delete}")

    return redirect(url_for("user.manage_user_page"))