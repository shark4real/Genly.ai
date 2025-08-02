import os
import requests
import csv
import io
import base64
from jinja2 import Template
from jinja2 import Template, StrictUndefined
from jinja2.exceptions import UndefinedError
from io import TextIOWrapper
from dotenv import load_dotenv
from django.shortcuts import render, redirect
from django.contrib import messages
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from base64 import urlsafe_b64encode
from urllib.parse import quote

# Allow OAuth2 over http (not recommended for production)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/gmail.send']
CLIENT_SECRETS_FILE = os.path.join(os.path.dirname(__file__), '../client_secret.json')


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

            # If it's a single email, open Gmail compose
            if send_option == 'single':
                gmail_url = f"https://mail.google.com/mail/?view=cm&fs=1&su={quote(subject)}&body={quote(body)}"
                return redirect(gmail_url)

            # Save draft in session and redirect for authentication
            if 'credentials' not in request.session:
                request.session['draft'] = {
                    'subject': subject,
                    'body': body,
                    'tone': tone,
                    'context': context,
                    'send_option': send_option,
                }
                return redirect('authorize_gmail')

            # Otherwise show bulk email editor
            return render(request, 'home.html', {
                'subject': subject,
                'body': body,
                'context': context,
                'tone': tone,
                'send_option': send_option,
                'preview_mode': True,
                'is_authenticated': True
            })

        except Exception as e:
            messages.error(request, f"Unexpected error: {str(e)}")

    return render(request, 'home.html', {
        'is_authenticated': 'credentials' in request.session
    })


def authorize_gmail(request):
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri='http://localhost:8000/oauth2callback/'
    )
    auth_url, state = flow.authorization_url(prompt='consent')
    request.session['state'] = state
    return redirect(auth_url)


def oauth2callback(request):
    state = request.session.get('state')

    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        state=state,
        redirect_uri='http://localhost:8000/oauth2callback/'
    )

    flow.fetch_token(authorization_response=request.build_absolute_uri())
    credentials = flow.credentials

    request.session['credentials'] = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

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

    return redirect('/')


def create_message_raw(sender, to, subject, message_html):
    message = MIMEMultipart('alternative')
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject

    # Optional plain version for fallback
    plain_text = message_html.replace('<br>', '\n').replace('&nbsp;', ' ')
    message.attach(MIMEText(plain_text, 'plain'))
    message.attach(MIMEText(message_html, 'html'))

    return base64.urlsafe_b64encode(message.as_bytes()).decode()

def send_bulk_email(request):
    if request.method != 'POST':
        return redirect('home')

    # Check Gmail login
    if 'credentials' not in request.session:
        messages.error(request, "Please log in with Gmail first.")
        return redirect('authorize_gmail')

    # Load Gmail API credentials
    credentials = Credentials(**request.session['credentials'])
    service = build('gmail', 'v1', credentials=credentials)
    print("Gmail credentials loaded:", credentials)
    print("Is valid:", credentials.valid)
    print("Expired:", credentials.expired)

    subject = request.POST.get('subject')
    body_template_str = request.POST.get('body')
    csv_file = request.FILES.get('csv_file')

    if not csv_file:
        messages.error(request, "CSV file is required.")
        return redirect('home')

    try:
        decoded_csv = csv_file.read().decode('utf-8-sig')  # handles BOM
        reader = csv.DictReader(io.StringIO(decoded_csv))
        rows = list(reader)
    except Exception as e:
        messages.error(request, f"Failed to read CSV: {str(e)}")
        return redirect('home')

    if not rows:
        messages.error(request, "CSV is empty or missing headers.")
        return redirect('home')

    # Compile Jinja template
    try:
        body_template = Template(body_template_str, undefined=StrictUndefined)
    except Exception as e:
        messages.error(request, f"Invalid body template: {e}")
        return redirect('home')

    success_count = 0
    failure_count = 0

    for index, row in enumerate(rows):
        try:
            # Normalize keys (strip + lowercase)
            row = {k.strip().lower(): v.strip() for k, v in row.items()}
            to_email = row.get('email')

            if not to_email:
                print(f"Row {index+1} skipped — missing 'email'")
                continue

            # Render subject and body with row data
            personalized_body = body_template.render(row)
            
            personalized_html = body_template.render(row).replace('\n', '<br>')

            raw_message = create_message_raw(
                sender="me",
                to=to_email,
                subject=subject,
                message_html=personalized_html
            )
            
            service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()

            print(f"✅ Email sent to {to_email}")
            success_count += 1

        except UndefinedError as ue:
            print(f"⚠️ Placeholder error in row {index+1}: {ue}")
            failure_count += 1
        except Exception as e:
            print(f"❌ Failed to send to {row.get('email', 'Unknown')}: {e}")
            failure_count += 1

    messages.success(request, f"{success_count} emails sent successfully. {failure_count} failed.")
    return redirect('home')

def credentials_to_dict(credentials):
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }
