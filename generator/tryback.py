import csv

csv_path = r"C:\Users\SHARIK\emailgen\generator\emailgen.csv"

# Define your subject and body template
subject_template = "Welcome to the team!"
body_template = """Hi {{name}},

We're excited to have you onboard. Feel free to reach out if you have questions.

Regards,  
Team"""

try:
    with open(csv_path, mode='r', encoding='utf-8-sig', newline='') as csvfile:
        reader = csv.DictReader(csvfile)

        for row in reader:
            name = row.get('Name')
            email = row.get('email')

            # Replace placeholder with actual name
            personalized_body = body_template.replace("{{name}}", name)

            print("\n------------------------------------")
            print(f"📧 To: {email}")
            print(f"📝 Subject: {subject_template}")
            print("📄 Body:\n" + personalized_body)

except FileNotFoundError:
    print("❌ CSV file not found. Please check the path.")
except Exception as e:
    print(f"❌ An error occurred: {e}")
