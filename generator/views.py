from django.shortcuts import render, redirect
from django.contrib import messages
import requests
import os
from dotenv import load_dotenv
import urllib.parse

load_dotenv()

def parse_subject_and_body(text):
    # Naively split by the first newline
    lines = text.strip().split('\n', 1)
    subject = ""
    body = text

    if lines:
        first_line = lines[0].strip().lower()
        if first_line.startswith("subject:"):
            subject = lines[0][len("subject:"):].strip()
            body = lines[1] if len(lines) > 1 else ""
        else:
            subject = "Generated Email"
    return subject, body.strip()

def generate_email(request):
    if request.method == 'POST':
        if 'generate' in request.POST:
            tone = request.POST.get('tone', '')
            context = request.POST.get('context', '')

            prompt = f"Write a {tone} email about the following situation:\n{context}"
            api_key = os.getenv("API_KEY")

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "mistralai/mistral-7b-instruct",
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }

            api_url = "https://openrouter.ai/api/v1/chat/completions"
            response = requests.post(api_url, headers=headers, json=payload)

            if response.status_code == 200:
                full_text = response.json()["choices"][0]["message"]["content"]
                subject, body = parse_subject_and_body(full_text)

                return render(request, 'home.html', {
                    'response': full_text,
                    'subject': subject,
                    'body': body,
                    'tone': tone,
                    'context': context
                })
            else:
                error_message = f"Error: {response.status_code}\n{response.text}"
                messages.error(request, error_message)

        elif 'send' in request.POST:
            recipient = request.POST.get('recipient_email')
            subject = request.POST.get('subject', '')
            body = request.POST.get('body', '')

            # Redirect to Gmail compose URL
            gmail_url = (
                "https://mail.google.com/mail/?view=cm&fs=1&to=" +
                urllib.parse.quote(recipient) +
                "&su=" + urllib.parse.quote(subject) +
                "&body=" + urllib.parse.quote(body)
            )
            return redirect(gmail_url)

    return render(request, 'home.html')
