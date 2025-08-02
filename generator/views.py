import os
import requests
import csv
from io import TextIOWrapper
from dotenv import load_dotenv
from django.shortcuts import render, redirect
from django.core.mail import EmailMessage
from django.contrib import messages
from urllib.parse import quote

load_dotenv()


def parse_subject_and_body(text):
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
        try:
            tone = request.POST.get('tone', '')
            context = request.POST.get('context', '')
            send_option = request.POST.get('send_option', 'single')

            prompt = f"Write a {tone} email about the following situation:\n{context}"
            api_key = os.getenv("API_KEY")

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": "mistralai/mistral-7b-instruct",
                "messages": [{"role": "user", "content": prompt}]
            }

            api_url = "https://openrouter.ai/api/v1/chat/completions"
            response = requests.post(api_url, headers=headers, json=payload)
            response.raise_for_status()

            email_content = response.json()['choices'][0]['message']['content']
            subject, body = parse_subject_and_body(email_content)

            if send_option == 'single':
                # Redirect to Gmail compose
                gmail_url = f"https://mail.google.com/mail/?view=cm&fs=1&su={quote(subject)}&body={quote(body)}"
                return redirect(gmail_url)

            # Else just show preview
            return render(request, 'home.html', {
                'subject': subject,
                'body': body,
                'context': context,
                'tone': tone,
                'send_option': send_option,
                'preview_mode': True
            })

        except requests.exceptions.RequestException:
            messages.error(request, "API error occurred.")
        except Exception as e:
            messages.error(request, f"Unexpected error occurred: {str(e)}")

    return render(request, 'home.html')


def send_bulk_email(request):
    if request.method == 'POST':
        try:
            subject = request.POST.get('subject', '')
            body = request.POST.get('body', '')
            csv_file = request.FILES.get('csv_file')

            if not csv_file:
                messages.error(request, "Please upload a CSV file.")
                return redirect('/generator/')

            decoded_file = TextIOWrapper(csv_file, encoding='utf-8')
            reader = csv.DictReader(decoded_file)

            for row in reader:
                recipient_email = row.get('email')
                if not recipient_email:
                    continue

                personalized_body = body
                for key, value in row.items():
                    personalized_body = personalized_body.replace(f"{{{{{key}}}}}", value)

                email = EmailMessage(subject=subject, body=personalized_body, to=[recipient_email])
                email.send()

            messages.success(request, "Bulk emails sent successfully!")

        except Exception as e:
            print("Error sending bulk:", e)
            messages.error(request, "Failed to send emails.")

    return redirect('/generator/')
