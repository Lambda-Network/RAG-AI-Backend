# Lambda Studios
# C: 2025-03-20
# M: 2025-04-02 (Patrick Patten)
# Backend Main File
from venv import logger
from flask import Flask, request, jsonify
import requests
import os
from dotenv import load_dotenv
import uuid
import asyncio
import time
import threading

# Load environment variables from .env file
load_dotenv()
# Initialize env variables
status = os.getenv("STATUS")
base_url = os.getenv("BASE_URL")
api_key = os.getenv("API_KEY")
assistant_id = os.getenv("ASSISTANT_ID")
delete_delay_minutes = int(os.getenv("DELETE_DELAY"))
folder = "retrieved-files"

app = Flask(__name__)

async def async_delete_files_loop():
    while True:
        if dev_mode: print("Running deletion loop")
        current_time = time.time()
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            if os.path.isfile(file_path):
                # Delete file if it is older than the set delay.
                if current_time - os.path.getmtime(file_path) > delete_delay_minutes * 60:
                    try:
                        os.remove(file_path)
                        if dev_mode: print(f"Deleted file: {file_path}")
                    except Exception as e:
                        print(f"Error deleting file {file_path}: {e}")
        # Wait 60 seconds before next check.
        await asyncio.sleep(60)

def start_deletion_loop():
    asyncio.run(async_delete_files_loop())



def does_assistant_exist():
    endpoint = f"{base_url}/api/v1/chats/"
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    params = {
        "id": assistant_id
    }
    response = requests.get(endpoint, headers=headers, params=params)
    response.raise_for_status()
    data = response.json()
    if data.get("code") == 0:
        return True
    else:
        print("Could not find assistant with ID:", assistant_id)
        return False


def generate_small_uuid():
    # Generate a full UUID (hex string) and slice the first 8 characters
    return uuid.uuid4().hex[:8]

@app.route('/ping', methods=['GET'])
def ping():
    """
    Ping endpoint to check if the backend server is running.
    :return:
    """
    return jsonify({"message": "Server is running!"}), 200


@app.route('/search', methods=['POST'])
def search():
    if not request.is_json:
        return jsonify({"error": "Request must be application/json"}), 400

    data = request.get_json()
    search_query = data.get('query')
    if not search_query:
        return jsonify({"error": "Missing query prompt"}), 400

    endpoint = f"{base_url}/api/v1/chats/{assistant_id}/sessions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    params = {
        "name": str(generate_small_uuid()),
    }
    response = requests.post(endpoint, headers=headers, json=params)
    data = response.json()
    if data.get("code") != 0:
        return jsonify({"error": "Failed to create session"}), 500
    session_id = data.get("data").get("id")


    print("Session ID:", session_id)

    endpoint = f"{base_url}/api/v1/chats/{assistant_id}/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    params = {
        "question": str(search_query),
        "stream": False,
        "session_id": session_id,
    }
    response = requests.post(endpoint, headers=headers, json=params)
    data = response.json()
    if data.get("code") != 0:
        return jsonify({"error": "Failed to ask question"}), 500
    answer = data["data"]["answer"]

    # Ensure the folder exists
    download_folder = "retrieved-files"
    os.makedirs(download_folder, exist_ok=True)

    # Get referenced document details
    referenced_chunks = data["data"]["reference"]["chunks"]
    referenced_docs = data["data"]["reference"]["doc_aggs"]

    downloaded_file_paths = []
    files_to_download = min(len(referenced_chunks), len(referenced_docs))

    for i in range(files_to_download):
        dataset_id = referenced_chunks[i]["dataset_id"]
        document_id = referenced_docs[i]["doc_id"]
        doc_name = referenced_docs[i]["doc_name"]
        _, ext = os.path.splitext(doc_name)
        if not ext:
            ext = ".html"  # Fallback to HTML if no extension found

        file_endpoint = f"{base_url}/api/v1/datasets/{dataset_id}/documents/{document_id}"
        file_headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        file_params = {
            "dataset_id": [dataset_id],
            "documents_id": [document_id]
        }

        file_resp = requests.get(file_endpoint, headers=file_headers, json=file_params, stream=True)
        if file_resp.status_code == 200:
            # Generate a new UUID for the file name
            file_uuid = uuid.uuid4().hex
            file_path = os.path.join(download_folder, f"{file_uuid}{ext}")
            with open(file_path, "wb") as f:
                for chunk in file_resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            downloaded_file_paths.append(os.path.abspath(file_path))
        else:
            print(f"Failed to download file for document {document_id}")

    # Create a list of file names (not full paths)
    downloaded_file_names = [os.path.basename(path) for path in downloaded_file_paths]

    endpoint = f"{base_url}/api/v1/chats/{assistant_id}/sessions/"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    params = {
        "ids": [session_id]
    }

    response = requests.delete(endpoint, headers=headers, json=params)
    data = response.json()
    if data.get("code") != 0:
        logger.error(f"Unable to delete session with ID {session_id}. Response: {data}")
    return jsonify({"answer": str(answer), "files": downloaded_file_names}), 200



def check_env_variables():
    """
    Check if the required environment variables are set.
    :return:
    """
    required_vars = ["STATUS", "BASE_URL", "API_KEY", "ASSISTANT_ID"]
    for var in required_vars:
        if os.getenv(var) is None:
            raise ValueError(f"Environment variable {var} is not set.")
    if os.getenv("STATUS") not in ["development", "production"]:
        raise ValueError("Invalid STATUS. Please set it to 'development' or 'production'.")
    if os.getenv("BASE_URL") == "https://<YOUR_BASE_URL>:9380":
        raise ValueError("BASE_URL is still default value.")
    if os.getenv("API_KEY") == "<YOUR_API_KEY>":
        raise ValueError("API_KEY is still default value.")
    if os.getenv("ASSISTANT_ID") == "<YOUR_ASSISTANT_ID>":
        raise ValueError("ASSISTANT_ID is still default value.")
    if does_assistant_exist() is False:
        raise ValueError("Assistant with the given ID does not exist.")


if __name__ == "__main__":
    # Check if required environment variables are set
    try:
        check_env_variables()
    except ValueError as e:
        print(f"Error: {e}")
        exit(1)
    # Get Dev Mode
    dev_mode = True
    if status == "development":
        dev_mode = True
    elif status == "production":
        dev_mode = False
    deletion_thread = threading.Thread(target=start_deletion_loop, daemon=True)
    deletion_thread.start()
    app.run(debug=dev_mode)