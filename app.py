from flask import Flask, render_template, request
from user import user

app = Flask("__name__")

app.register_blueprint(user, url_prefix = "/")

@app.route("/home")
def home():
    return render_template("home.html")

if __name__ == "__main__":
    app.run(host = "127.0.0.1", port = 8081, debug = True)