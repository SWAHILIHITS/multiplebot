import requests
import json
import uuid

API_URL = "https://zenoapi.com/api/payments/mobile_money_tanzania"
# Replace with your actual API Key
API_KEY = "Ca_mt_lI-RMjVDI3N0BSJGYC_FHIhOL6i2eIYA6PavLU36rLUfbKoUtmG5wsF69Z_S2NGiXmUhJWmRVmQKpwxw"

payload = {
    "order_id": str(uuid.uuid4()),    # MANDATORY: Must be a unique UUID
    "buyer_name": "Hassan mohamed",        # MANDATORY
    "buyer_email": "hramamogamed@gmail.com", # MANDATORY
    "buyer_phone": "0624667219",      # MANDATORY: 10 digits starting with 0
    "amount": 10000,                  # MANDATORY: Number, not string
    #"webhook_url": "https://yourdomain.com" # Recommended
}

headers = {
    "Content-Type": "application/json",
    "x-api-key": API_KEY
}

try:
    response = requests.post(API_URL, headers=headers, json=payload)
    
    # If it's still 400, this will print the server's specific error message
    if response.status_code != 200:
        print(f"Error {response.status_code}: {response.text}")
    else:
        print("Success:", response.json())

except requests.exceptions.RequestException as e:
    print(f"Connection failed: {e}")
