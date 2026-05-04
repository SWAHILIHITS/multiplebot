from bot  import Bot0
from info import filters
import requests,json
from utils import User
from plugins.database import db
@Bot0.on_message( filters.command('/hakiki_order'))
async def bpayoder(client, message):
    botusername=await client.get_me()
    nyva=botusername.username  
    nyva=str(nyva)
    status= await db.is_admin_exist(message.from_user.id,nyva)
    if not status:
        return
    gd = await db.get_db_status(message.from_user.id,nyva)        
    API_KEY =gd["zeno_api"]
    filter={"rbt":f"{message.from_user.id}#d#pay"}
    gdt=User.find(filter)
    total_c = await Media.count_documents(filter)
    gd2 = await gdt.to_list(length=int(total_c))
    for order in gd2:
        ORDER_ID = order.id.split("#d#")[1]
        API_URL = f"https://zenoapi.com/api/payments/order-status?order_id={ORDER_ID}"

        # Request headers
        headers = {
            "x-api-key": API_KEY
        }

        try:
            # Send GET request
            response = requests.get(API_URL, headers=headers)
            response.raise_for_status()

            # Parse JSON response
            data = response.json()

            # Check if the response was successful
            if data.get("resultcode") == "000":
                order_info = data.get("data", [])[0]  # First result in the list

                result = {
                    "status": "success",
                    "order_id": order_info.get("order_id"),
                    "payment_status": order_info.get("payment_status"),
                    "amount": order_info.get("amount"),
                    "channel": order_info.get("channel"),
                    "reference": order_info.get("reference"),
                    "msisdn": order_info.get("msisdn"),
                    "message": data.get("message")
                }
             else:
                 result = {
                     "status": "error",
                     "message": data.get("message", "Unable to fetch order status")
                 }

        except requests.exceptions.HTTPError as http_err:
            result = {"status": "error", "message": f"HTTP error: {http_err}"}
        except requests.exceptions.ConnectionError:
            result = {"status": "error", "message": "Connection error."}
        except requests.exceptions.Timeout:
            result = {"status": "error", "message": "Request timed out."}
        except requests.exceptions.RequestException as err:
            result = {"status": "error", "message": f"Request error: {err}"}

        # Print final result
        print(json.dumps(result, indent=4))
        await client.send_message(chat_id=message.from_user.id, text=f'{json.dumps(result, indent=4)}')
            
