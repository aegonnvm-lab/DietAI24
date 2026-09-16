import urllib.request
import json

def test_payload(filename):
    boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
    body = (
        f'--{boundary}\r\n'
        f'Content-Disposition: form-data; name="image"; filename="{filename}"\r\n'
        f'Content-Type: image/jpeg\r\n\r\n'
        f'test_image_bytes\r\n'
        f'--{boundary}--\r\n'
    ).encode('utf-8')

    req = urllib.request.Request(
        'http://localhost:8000/analyze?debug=true',
        data=body,
        headers={'Content-Type': f'multipart/form-data; boundary={boundary}'}
    )

    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode('utf-8'))

print("--- 1. Testing Live API with Omelette ---")
d1 = test_payload("omelette.jpg")
print("Status:", d1["status"])
print("Foods:", [(f["standardized_name"], f["count"], f["portion"]["estimated_grams"], f["nutrition"]["calories_kcal"]) for f in d1["foods"]])
print("Total kcal:", d1["totals"]["calories_kcal"])

print("\n--- 2. Testing Live API with Thali (Multi-Food) ---")
d2 = test_payload("thali_meal.jpg")
print("Status:", d2["status"])
print("Detected Foods Count:", len(d2["foods"]))
for f in d2["foods"]:
    print(f"  * {f['standardized_name']} (count: {f['count']}) -> {f['portion']['estimated_grams']}g, {f['nutrition']['calories_kcal']} kcal")
print("Total Meal kcal:", d2["totals"]["calories_kcal"])

print("\n--- 3. Testing Live API with Ambiguous / Unknown Food ---")
d3 = test_payload("unknown_noisy_input.jpg")
print("Status:", d3["status"])
print("Warnings:", d3["warnings"])
print("Foods:", [(f["standardized_name"], f["match_status"], f["needs_user_review"]) for f in d3["foods"]])
