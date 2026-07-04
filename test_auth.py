from auth import authenticate

credentials = authenticate()

print("Authentication Successful")

print(credentials.valid)