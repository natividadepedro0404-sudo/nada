import requests
import json
ci = "ci_libdweclsjyry50"
cs = "cs_kknlfy76fe2ir4nqjydf8ebee"
url = "https://api.misticpay.com/api/transactions/create"
headers = {"ci": ci, "cs": cs, "Content-Type": "application/json"}
payload = {"amount": 10.00, "payerName": "Teste", "payerDocument": "00000000000", "transactionId": "TEST_384", "description": "Teste CC Checker"}
r = requests.post(url, json=payload, headers=headers)
with open('out.json', 'w') as f:
    json.dump(r.json(), f, indent=4)
