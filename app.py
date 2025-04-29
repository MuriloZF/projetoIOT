from flask import Flask, render_template, request
from user import user

app = Flask("__name__")

app.register_blueprint(user, url_prefix = "/")

@app.route("/home")
def home():
    return render_template("home.html")

@app.errorhandler(404)
def pageNotFound(error):
    return render_template("templates/errors/404.html"), 404

@app.errorhandler(401)
def acessUnauthorized(error):
    return render_template("/templates/erros/401.html"), 401

@app.errorhandler(500)
def internalError(error):
    return render_template("/templates/errors/500.html"), 500

@app.errorhandler(503)
def serviceUnavailable(error):
    return render_template("/templates/errors/503.html"), 503

if __name__ == "__main__":
    app.run(host = "127.0.0.1", port = 8081, debug = True)