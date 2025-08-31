# Fish Game Writeup

## Challenge Overview

**Category:** Web/Game Hacking  
**Flag:** `kaspersky{g1v3_m4n_4_f1sh1ng_r0d_h3_w0u1d_b3_f4d}`

This challenge is a Godot-based fish game where players control a fish and tries to get a high score.

---

## Step 1: Game Analysis and Reverse Engineering

### Initial Setup

First, we need to understand the game and extract its source code:

1. **Download and run the game** to understand basic mechanics
2. **Install GDRETools** from: https://github.com/GDRETools/gdsdecomp
3. **Extract game files** using GDRETools to reveal the complete source code

### Analysis

After decompilation, the important files are:

```
score.gd / score.tscn  # Score submission system
registry.gd            # Server URLs and configuration
player.gd / player.tscn # Player controller and token handling
enemy.gd / enemy.tscn  # Enemy AI and score calculation
```

---

## Step 2: Understanding Game Mechanics

Analyzing `enemy.gd`:

```gdscript
func _on_body_entered(body: Node2D) -> void :
    if body is Player:
        var x = 0
        for xx in body.get_children():
            if xx is Enemy:
                x += 1
        Registry.asd = x * 123  # Score stored as (fish_count * 123)
        get_tree().change_scene_to_file("res://lose.tscn")
```

The score is calculated as `number_of_fish_caught × 123`, this is noted for future use. 

---

## Step 3: Network Communication Analysis

### Identifying Server Endpoints

From `registry.gd`:
```gdscript
var base_url = "https://fishgame.task.sasc.tf"
```

From `player.gd` and `score.gd`, we find these endpoints:
- `GET /get_token` - Get authentication token
- `POST /set_score` - Submit score to leaderboard
- `GET /get_prize/{token}` - Get reward/flag

### Token System

From `player.gd`:
```gdscript
func _ready() -> void :
    $HTTPRequest.request_completed.connect(_on_request_completed)
    $HTTPRequest.request(get_token)  # Request fresh token on startup
    Registry.player = self

func _on_request_completed(result, response_code, headers, body):
    if response_code != 200:
        return
    var json = JSON.parse_string(body.get_string_from_utf8())
    Registry.token = json["token"]  # Store token for later use
```

The game requests a fresh token each time it starts, and stores it for later use when interacting with the various API endpoints.

---

## Step 4: Understanfing how the scoring system actually works

### Score Verification System

`score.gd` contains the score verification function.

```gdscript
func calculate(st: String) -> String:
    var x = 0
    for i in range(len(st)):
        x += st.unicode_at(i)  # Add ASCII value of each character
        x *= 2                 # Multiply by 2
        x %= 2 ** 64          # Modulo 2^64
    return "%x" % x           # Return as hexadecimal
```
This is understood as the verification function as it is later called during score submission to create the JSON:

From `score.gd`:
```gdscript
func _on_send_pressed() -> void :
    # ... validation checks ...
    var data_json = JSON.stringify({
        "token": Registry.token, 
        "username": $Control/VBoxContainer/TextEdit.text, 
        "score": Registry.asd / 123,           # Displayed score
        "verify": calculate(Registry.token + "_" + str(Registry.asd))  # Verification hash
    })
```

The `calculate` function is called here as a part of `verify` in the form of a hash function. This is used to ensure the score is not easily tampered with just directly changing the score value, but the hash function is also visible, allowing us to compute the hash value of any score.

---

## Step 5: Testing the API Endpoints

### Manual API Testing

Let's test each endpoint manually:

```bash
# 1. Get a token
curl -s "https://fishgame.task.sasc.tf/get_token"
# Response: {"token":"fe714afd515bea2bff8dd30cafc2d441"}
# Note: The token is different each time, this is just a placeholder for demonstration

# 2. Check current leaderboard
curl -s "https://fishgame.task.sasc.tf/get_scores"
# Shows current high scores

# 3. Test prize endpoint (without valid score)
curl -s "https://fishgame.task.sasc.tf/get_prize/fe714afd515bea2bff8dd30cafc2d441"
# Returns a message stating a score above 5000 is required to get the prize.
```

From testing, we discover that we need a very high score to get the flag, which would be very hard to get from actually playing the game (from experience the most i could get was 10, before i tried to figure another way out)

---

## Step 6: Implementing the Exploit

### Recreate the Hash Function

First, we implement the verification hash in Python:

```python
def calculate_hash(input_string):
    """
    Python implementation of the GDScript calculate() function
    """
    x = 0
    for char in input_string:
        x += ord(char)    # ASCII value
        x *= 2           # Multiply by 2
        x %= (2 ** 64)   # Modulo 2^64
    return format(x, 'x')  # Return as hex
```

### Calculate Valid Verification

```python
# Example calculation
token = "fe714afd515bea2bff8dd30cafc2d441"
score = 100000  # High score we want
asd_value = score * 123  # Convert to internal representation

# Create verification string exactly as the game does
verify_string = f"{token}_{asd_value}"
verify_hash = calculate_hash(verify_string)

print(f"Score: {score}")
print(f"ASD Value: {asd_value}")
print(f"Verify String: {verify_string}")
print(f"Verify Hash: {verify_hash}")
```

### Submit the Forged Score

```python
payload = {
    "token": token,
    "username": "user",
    "score": score,        # The display score
    "verify": verify_hash  # Our calculated verification
}

response = requests.post(
    "https://fishgame.task.sasc.tf/set_score",
    headers={"Content-Type": "application/json"},
    json=payload
)

print(f"Status: {response.status_code}")
print(f"Response: {response.text}")
```

---

## Step 7: Getting the Flag

### Request the Prize

After successfully submitting a high score:

```python
prize_response = requests.get(f"https://fishgame.task.sasc.tf/get_prize/{token}")

if prize_response.status_code == 200:
    data = prize_response.json()
    prize = data.get("prize", "No prize found")
    print(f"Prize: {prize}")
    
    if "kaspersky{" in prize:
        print(f"FLAG FOUND: {prize}")
```

The server returns: `kaspersky{g1v3_m4n_4_f1sh1ng_r0d_h3_w0u1d_b3_f4d}`

## Step 8: Complete Exploit

#### The python script is located at: **[soln.py](soln.py)**

---

Initially i did it without a script by:

```bash
# 1. Get token
curl -s "https://fishgame.task.sasc.tf/get_token"

# 2. Calculate hash in Python
python3 -c "
token = 'YOUR_TOKEN_HERE'
score = 100000
asd = score * 123
verify_str = f'{token}_{asd}'
x = 0
for c in verify_str:
    x += ord(c)
    x *= 2
    x %= (2**64)
print(f'Hash: {format(x, \"x\")}')
"

# 3. Submit score
curl -X POST "https://fishgame.task.sasc.tf/set_score" \
  -H "Content-Type: application/json" \
  -d '{
    "token": "YOUR_TOKEN",
    "username": "user", 
    "score": 100000,
    "verify": "YOUR_HASH"
  }'

# 4. Get flag
curl -s "https://fishgame.task.sasc.tf/get_prize/YOUR_TOKEN"
```

---
