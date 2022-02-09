import base64
import hashlib
import json
import os
import pathlib
import requests
import secrets
import threading
import urllib
import webbrowser
from time import sleep

from werkzeug.serving import make_server

import dotenv
from flask import Flask, request

app = Flask(__name__)


@app.route("/callback")
def callback():
    """
    The callback is invoked after a completed login attempt (succesful or otherwise).
    It sets global variables with the auth code or error messages, then sets the
    polling flag received_callback.
    :return:
    """
    global received_callback, code, error_message, received_state
    error_message = None
    code = None
    if 'error' in request.args:
        error_message = request.args['error'] + ': ' + request.args['error_description']
    else:
        code = request.args['code']
    received_state = request.args['state']
    received_callback = True
    return "Please return to your application now."


class ServerThread(threading.Thread):
    """
    The Flask server is done this way to allow shutting down after a single request has been received.
    """

    def __init__(self, app):
        threading.Thread.__init__(self)
        self.srv = make_server('127.0.0.1', 5000, app)
        self.ctx = app.app_context()
        self.ctx.push()

    def run(self):
        print('starting server')
        self.srv.serve_forever()

    def shutdown(self):
        self.srv.shutdown()


def auth0_url_encode(byte_data):
    """
    Safe encoding handles + and /, and also replace = with nothing
    :param byte_data:
    :return:
    """
    return base64.urlsafe_b64encode(byte_data).decode('utf-8').replace('=', '')


def generate_challenge(a_verifier):
    return auth0_url_encode(hashlib.sha256(a_verifier.encode()).digest())


env_path = pathlib.Path('.') / '.env'
dotenv.load_dotenv(dotenv_path=env_path)

verifier = auth0_url_encode(secrets.token_bytes(32))
challenge = generate_challenge(verifier)
state = auth0_url_encode(secrets.token_bytes(32))
client_id = os.getenv('AUTH0_CLIENT_ID')
tenant = os.getenv('AUTH0_TENANT')
audience = os.getenv('AUTH0_AUDIENCE')
redirect_uri = 'http://127.0.0.1:5000/callback'



# We generate a nonce (state) that is used to protect against attackers invoking the callback
base_url = 'https://%s.auth0.com/logout?' % tenant
url_parameters = {
    'redirect_uri': redirect_uri,
    'client_id': client_id,
}
url = base_url + urllib.parse.urlencode(url_parameters)

# Open the browser window to the login url
# Start the server
# Poll til the callback has been invoked
received_callback = False
webbrowser.open_new(url)
server = ServerThread(app)
server.start()
while not received_callback:
    sleep(1)
server.shutdown()

if state != received_state:
    print("Error: session replay or similar attack in progress. Please log out of all connections.")
    exit(-1)

if error_message:
    print("An error occurred:")
    print(error_message)
    exit(-1)
