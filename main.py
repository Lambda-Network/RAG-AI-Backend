# Lambda Studios
# C: 2025-03-20
# M: 2025-03-31 (Patrick Patten)
# Backend Main File
from flask import Flask, request, jsonify
from ragflow_sdk import RAGFlow

app = Flask(__name__)


@app.route('/ping', methods=['GET'])
def ping():
    """
    Ping endpoint to check if the server is running.
    :return:
    """
    return jsonify({"message": "Server is running!"}), 200

if __name__ == "__main__":
    app.run(debug=True)