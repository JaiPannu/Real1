import serial
import time
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.system_program import TransferParams, transfer
from solana.rpc.api import Client
from solana.transaction import Transaction
from solders.instruction import Instruction
import qrcode
import json
import csv
from datetime import datetime
import os
import requests

# ================= CONFIGURATION =================
ARDUINO_PORT = "COM3"  # CHANGE THIS to your Arduino Port
BAUD_RATE = 9600
WALLET_PATH = "hackathon-wallet.json" # Path to the file you generated in Phase 1
RUN_ID = 0 # Incremental Run ID for each submission
FLASK_SERVER = "http://127.0.0.1:5000"  # Flask leaderboard server URL
ROBOT_ID = "UTRA-BIATHLON-01"  # Identifier for this robot

# Solana Setup (Devnet)
client = Client("https://api.devnet.solana.com")

# Load Keypair
with open(WALLET_PATH, 'r') as f:
    key_data = json.load(f)
sender = Keypair.from_bytes(key_data)

print(f"✅ Bridge Loaded. Wallet: {sender.pubkey()}")
print(f"📡 Listening on {ARDUINO_PORT}...")

if not os.path.exists("runs.csv"):
    with open("runs.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "score", "duration_ms", "tx_signature"])


def log_run(score, duration, signature):
    with open("runs.csv", "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().isoformat(),
            score,
            duration,
            signature
        ])
    
    # Send to Flask leaderboard
    try:
        response = requests.post(
            f"{FLASK_SERVER}/api/submit_run",
            json={
                'score': score,
                'duration': duration,
                'signature': signature,
                'robot_id': ROBOT_ID
            },
            timeout=5
        )
        if response.status_code == 201:
            print("       📊 Sent to leaderboard!")
        else:
            print(f"       ⚠️  Leaderboard response: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("       ⚠️  Flask server not running. Continuing without leaderboard update...")
    except Exception as e:
        print(f"       ⚠️  Could not reach leaderboard: {e}")

def send_to_blockchain(score, duration, ser):
    print(f"\n[EVENT] Robot finished! Score: {score}, Time: {duration}ms")
    print("       Minting Proof of Run...")

    # We use the "Memo" program to attach text to a transaction
    # This writes the score permanently onto the chain
    memo_program_id = Pubkey.from_string("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcQb")
    global RUN_ID; RUN_ID += 1

    memo_text = (
        f"UTRA HACKS 2026 | {ROBOT_ID} | RUN {RUN_ID} | "
        f"SCORE: {score} | TIME: {duration}ms"
    ).encode("utf-8")

    # Create Transaction Instruction
    memo_ix = Instruction(
        program_id=memo_program_id,
        accounts=[],
        data=memo_text
    )

    # Build the Transaction
    # We send 0 SOL to ourselves just to carry the memo
    txn = Transaction().add(memo_ix)
    
    # Send and Confirm
    try:
        result = client.send_transaction(txn, sender)
        signature = result.value
        
        print("       ✅ SUCCESS! Transaction Confirmed.")
        print(f"       Signature: {signature}")

        # Acknowledge to Arduino
        ser.write(b"SOLANA_ACK\n")

        # Log the run
        log_run(score, duration, signature)
        
        # Generate QR Code for Judges
        explorer_url = f"https://explorer.solana.com/tx/{signature}?cluster=devnet"
        qr = qrcode.QRCode()
        qr.add_data(explorer_url)
        qr.print_ascii()
        print(f"\n🔗 VERIFY HERE: {explorer_url}")
        
    except Exception as e:
        print(f"       ❌ ERROR: {e}")

# Main Listener Loop
ser = serial.Serial(ARDUINO_PORT, BAUD_RATE)
while True:
    if ser.in_waiting > 0:
        line = ser.readline().decode('utf-8').strip()
        
        if line.startswith("SOLANA_RECORD:"):
            # Parse the data: "SOLANA_RECORD:50:45000"
            parts = line.split(":")
            score = int(parts[1])
            time_ms = int(parts[2])
            
            send_to_blockchain(score, time_ms)