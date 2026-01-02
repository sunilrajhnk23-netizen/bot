



from kiteconnect import KiteConnect

API_KEY = "2fny2gd8v1yxolco"
API_SECRET = "i42u2f82dpbxrhin0yvv980fvhevs6ao"
REQUEST_TOKEN = "qvOByG8xuPSIXQ5EKxUWZCX9ar9AvGvw"

kite = KiteConnect(api_key=API_KEY)

data = kite.generate_session(
    REQUEST_TOKEN,
    api_secret=API_SECRET
)

print("\nACCESS TOKEN:")
print(data["access_token"])
