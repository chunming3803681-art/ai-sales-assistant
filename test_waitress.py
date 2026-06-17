from flask import Flask
app = Flask(__name__)

@app.route("/")
def home():
    return "OK - Waitress Works!"

if __name__ == "__main__":
    from waitress import serve
    print("Starting Waitress on http://127.0.0.1:9000 ...")
    serve(app, host="127.0.0.1", port=9000)