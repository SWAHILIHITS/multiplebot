import requests
import json
# ZenoPay API endpoint for Mobile Money Tanzania
API_URL = "https://zenoapi.com/api/payments/mobile_money_tanzania"

# Your API Key (store securely in production)
API_KEY = "Ca_mt_lI-RMjVDI3N0BSJGYC_FHIhOL6i2eIYA6PavLU36rLUfbKoUtmG5wsF69Z_S2NGiXmUhJWmRVmQKpwxw"

# Payment order payload
payload = {
    "order_id": "movietzbot0005",  # e.g., UUI
    #"buyer_name": "Hassan Mohamedi",           # REQUIRED
    #"buyer_email":"hramamohamed@gmail.com",
    "buyer_phone": "0624667219",  # Tanzanian format: 07XXXXXXXX
    "amount": 10000,  # Amount in TZS
}
print("ZenoPay Response:")
# Request headers with API key
headers = {
    "Content-Type": "application/json",
    "x-api-key": API_KEY
}
print("tryinging")

try:
    # Send POST request
    response = requests.post(API_URL, headers=headers, json=payload)
    response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

    # Parse JSON response
    data = response.json()
    print("ZenoPay Response:")
    print(json.dumps(data, indent=4))

except requests.exceptions.HTTPError as http_err:
    print(f"[HTTP ERROR] {http_err}")
except requests.exceptions.ConnectionError:
    print("[CONNECTION ERROR] Failed to connect to ZenoPay API.")
except requests.exceptions.Timeout:
    print("[TIMEOUT ERROR] Request timed out.")
except requests.exceptions.RequestException as e:
    print(f"[REQUEST ERROR] {e}")
