import os
from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/health")
def health():
    return jsonify({"status": "healthy"}), 200

@app.route("/")
def index():
    return "<h1>ERP13 Running</h1>", 200

application = app