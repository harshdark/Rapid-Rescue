import requests

def send_fcm_notification(token, title, body):
    headers = {
        'Authorization': 'key=YOUR_SERVER_KEY',
        'Content-Type': 'application/json',
    }
    payload = {
        'to': token,
        'notification': {'title': title, 'body': body}
    }
    requests.post('https://fcm.googleapis.com/fcm/send', headers=headers, json=payload)