import yagmail

sender = "hiteshofficial0001@gmail.com"
receiver = "hiteshyadav8580@gmail.com"
subject = "Trip Itinerary"
body = "Here's your trip from Delhi to Goa..."

# Use App Password here, not your real Gmail password
yag = yagmail.SMTP(user=sender, password="ynzu vbua lxvi nbht")
yag.send(to=receiver, subject=subject, contents=body)

print("Email sent!")
