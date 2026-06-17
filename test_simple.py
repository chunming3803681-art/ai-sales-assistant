from flask import Flask
app = Flask(__name__)

@app.route("/")
def home():
    return "OK"

if __name__ == "__main__":
    app.run(port=5002, debug=False, host="127.0.0.1")