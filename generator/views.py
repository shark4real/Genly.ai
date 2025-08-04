import os
import requests
import csv
import io
import base64
from django.http import HttpResponseRedirect
from django.utils.http import urlencode
from jinja2 import Template, StrictUndefined
from jinja2.exceptions import UndefinedError
from dotenv import load_dotenv
from django.shortcuts import render, redirect
from django.contrib import messages
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from django.urls import reverse
from urllib.parse import quote
import json

# Allow OAuth2 over http (not recommended for production)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/gmail.send']
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS_JSON"))

def credentials_to_dict(credentials):
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

def landing_page(request):
    if 'credentials' in request.session:
        return redirect('home')
    return render(request, 'landing.html')

def home(request):
    if 'credentials' not in request.session:
        return redirect('landing')
    return render(request, 'home.html', {
        'is_authenticated': True
    })

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

def is_mobile(request):
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    return 'mobile' in user_agent or 'android' in user_agent or 'iphone' in user_agent

def generate_email(request):
    if 'credentials' not in request.session:
        return redirect('authorize_gmail')

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
                gmail_url = f"https://mail.google.com/mail/?view=cm&fs=1&su={quote(subject)}&body={quote(body)}"
                if is_mobile(request):
                    # Use mailto on mobile for better compatibility
                    mailto_url = f"mailto:?{urlencode({'subject': subject, 'body': body})}"
                    return HttpResponseRedirect(mailto_url)
                else:
                    return redirect(gmail_url)

            # Save data in session for bulk preview
            request.session['bulk_data'] = {
                'subject': subject,
                'body': body,
                'context': context,
                'tone': tone,
                'send_option': send_option
            }
            return redirect('bulk_preview')

        except Exception as e:
            messages.error(request, f"Unexpected error: {str(e)}")

    return render(request, 'home.html', {
        'is_authenticated': 'credentials' in request.session
    })

def bulk_preview(request):
    data = request.session.pop('bulk_data', None)
    if not data:
        return redirect('home')

    return render(request, 'home.html', {
        **data,
        'preview_mode': True,
        'is_authenticated': True
    })


def bulk_preview(request):
    data = request.session.pop('bulk_data', None)
    if not data:
        return redirect('home')

    return render(request, 'home.html', {
        **data,
        'preview_mode': True,
        'is_authenticated': True
    })



def authorize_gmail(request):
    creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS_JSON"))
    flow = Flow.from_client_config(
        creds_dict,
        scopes=SCOPES,
        redirect_uri='https://genly-ai.onrender.com/oauth2callback/'
    )
    auth_url, state = flow.authorization_url(prompt='consent')
    request.session['state'] = state
    return redirect(auth_url)


def oauth2callback(request):
    state = request.session.get('state')
    creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS_JSON"))
    flow = Flow.from_client_config(
        creds_dict,
        scopes=SCOPES,
        state=state,
        redirect_uri='https://genly-ai.onrender.com/oauth2callback/'
    )

    flow.fetch_token(authorization_response=request.build_absolute_uri())
    credentials = flow.credentials

    request.session['credentials'] = credentials_to_dict(credentials)

    if 'draft' in request.session:
        draft = request.session.pop('draft')
        return render(request, 'home.html', {
            'subject': draft['subject'],
            'body': draft['body'],
            'context': draft['context'],
            'tone': draft['tone'],
            'send_option': draft['send_option'],
            'preview_mode': True,
            'is_authenticated': True
        })

    return redirect('home')

def create_message_raw(sender, to, subject, message_html, attachments=None):
    message = MIMEMultipart('mixed')
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject

    # Only attach HTML content — remove plain text duplication
    html_part = MIMEText(message_html, 'html')
    message.attach(html_part)

    # Attach files if any
    if attachments:
        for file in attachments:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(file.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename="{file.name}"')
            message.attach(part)

    return base64.urlsafe_b64encode(message.as_bytes()).decode()


def send_bulk_email(request):
    print("🔥 Bulk email function triggered")
    if request.method != 'POST':
        return redirect('home')

    if 'credentials' not in request.session:
        messages.error(request, "Please log in with Gmail first.")
        return redirect('authorize_gmail')

    credentials = Credentials(**request.session['credentials'])
    service = build('gmail', 'v1', credentials=credentials)

    subject = request.POST.get('subject')
    body_template_str = request.POST.get('body')
    csv_file = request.FILES.get('csv_file')
    attachments = request.FILES.getlist('attachments')

    if not csv_file:
        messages.error(request, "CSV file is required.")
        return redirect('home')

    try:
        decoded_csv = csv_file.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(decoded_csv))
        rows = list(reader)
    except Exception as e:
        messages.error(request, f"Failed to read CSV: {str(e)}")
        return redirect('home')

    if not rows:
        messages.error(request, "CSV is empty or missing headers.")
        return redirect('home')

    try:
        body_template = Template(body_template_str, undefined=StrictUndefined)
    except Exception as e:
        messages.error(request, f"Invalid body template: {e}")
        return redirect('home')

    success_count = 0
    failure_count = 0

    for index, row in enumerate(rows):
        try:
            row = {k.strip().lower(): v.strip() for k, v in row.items()}
            to_email = row.get('email')

            if not to_email:
                print(f"Row {index+1} skipped — missing 'email'")
                continue

            personalized_html = body_template.render(row).replace('\n', '<br>')

            raw_message = create_message_raw(
                sender="me",
                to=to_email,
                subject=subject,
                message_html=personalized_html,
                attachments=attachments
            )

            service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()

            #print(f"✅ Email sent to {to_email}")
            success_count += 1

        except UndefinedError as ue:
            print(f"⚠️ Placeholder error in row {index+1}: {ue}")
            failure_count += 1
        except Exception as e:
            print(f"❌ Failed to send to {row.get('email', 'Unknown')}: {e}")
            failure_count += 1

    messages.success(request, f"{success_count} emails sent successfully. {failure_count} failed.")
    return redirect(f"{reverse('home')}?sent=1")
