import requests
import json

def calculate_hash(input_string):
    x = 0
    for char in input_string:
        x += ord(char)
        x *= 2
        x %= (2 ** 64)
    return format(x, 'x')

def main():
    base_url = "https://fishgame.task.sasc.tf"

    print("1. Getting token")
    token_response = requests.get(f"{base_url}/get_token")
    if token_response.status_code != 200:
        print(f"Failed to get token: {token_response.status_code}")
        return
    
    token_data = token_response.json()
    token = token_data["token"]
    print(f"   Token: {token}")

    print("\n2. Calculating verification hash: ")
    score = 100000
    asd_value = score * 123
    verify_string = f"{token}_{asd_value}"
    verify_hash = calculate_hash(verify_string)
    
    print(f"   Score: {score:,}")
    print(f"   Internal asd value: {asd_value}")
    print(f"   Verification string: {verify_string}")
    print(f"   Verification hash: {verify_hash}")
    
    print("\n3. Submitting score: ")
    payload = {
        "token": token,
        "username": "user",
        "score": score,
        "verify": verify_hash
    }
    
    score_response = requests.post(
        f"{base_url}/set_score",
        headers={"Content-Type": "application/json"},
        json=payload
    )
    
    print(f"   Response code: {score_response.status_code}")
    print(f"   Response: {score_response.text}")
    
    if score_response.status_code == 200:
        print("\n4. Getting prize: ")
        prize_response = requests.get(f"{base_url}/get_prize/{token}")
        print(f"   Response code: {prize_response.status_code}")
        
        if prize_response.status_code == 200:
            prize_data = prize_response.json()
            prize = prize_data.get("prize", "No prize found")
            print(f"   Prize: {prize}")
            
            if "kaspersky{" in prize:
                print(f"\nFLAG FOUND: {prize}")
            else:
                print("\nPrize received but not a flag")
        else:
            print(f"Failed to get prize: {prize_response.text}")
    else:
        print("Score submission failed")

if __name__ == "__main__":
    main()