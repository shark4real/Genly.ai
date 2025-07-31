from django.shortcuts import render
from django.core.mail import EmailMessage
from django.contrib import messages
import requests
import os
from dotenv import load_dotenv

load_dotenv()

def generate_email(request):
    response_text = None

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
                response_text = response.json()["choices"][0]["message"]["content"]
            else:
                response_text = f"Error: {response.status_code}\n{response.text}"

            return render(request, 'home.html', {
                'response': response_text,
                'tone': tone,
                'context': context
            })

        elif 'send' in request.POST:
            recipient = request.POST.get('recipient_email')
            content = request.POST.get('email_content')

            try:
                email = EmailMessage(
                    subject="Generated Email",
                    body=content,
                    from_email="youremail@example.com",  # Replace with your email or setup
                    to=[recipient],
                )
                email.send(fail_silently=False)
                messages.success(request, "Email sent successfully!")
            except Exception as e:
                messages.error(request, f"Failed to send email: {str(e)}")

            return render(request, 'home.html', {
                'response': content,
                'recipient': recipient
            })

    return render(request, 'home.html')
