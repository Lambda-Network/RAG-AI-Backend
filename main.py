# Lambda Studios
# C: 2025-03-20
# M: 2025-03-31 (Patrick Patten)
# Backend Main File
from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route('/test', methods=['GET'])
def test():
    """
    Test endpoint to check if the server is running.
    :return:
    """
    return jsonify({"message": "Hello, this is a test endpoint!"})

if __name__ == "__main__":
    app.run(debug=True)