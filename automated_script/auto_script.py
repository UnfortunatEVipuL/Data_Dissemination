# Import core Python modules for timing, command-line execution, and file path management
import time
import subprocess
import os

# Import the Watchdog library to monitor the operating system for file creation events
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Import the Web3 library to interact with the Ethereum Virtual Machine (EVM) via JSON-RPC
from web3 import Web3

# ==========================================
# 1. SYSTEM CONFIGURATION
# ==========================================
# The exact absolute path to your local Kubo IPFS executable.
# Python uses this to trigger command-line operations (like 'ipfs add') automatically.
IPFS_EXE = r"C:\Users\vipul\Downloads\IPFS_Node\kubo\ipfs.exe"

# The designated local directory that acts as the "Dropzone" for incoming telemetry payloads.
# The script will actively monitor this folder for any new files.
FOLDER_TO_WATCH = r"C:\Users\vipul\Downloads\IPFS_Dropzone"

# ==========================================
# 2. BLOCKCHAIN CONFIGURATION
# ==========================================
# The RPC URL for the local Ganache EVM network.
GANACHE_URL = "http://127.0.0.1:7545" 

# The address where the Satellite Data Vault Smart Contract is deployed on Ganache.
CONTRACT_ADDRESS = "0xd5ABC9CB7411dfaA6985AeE2a0fAE76bbA4b9325"

# The cryptographic identity of the system administrator.
# This must match Account #1 in Ganache (the deployer of the contract).
WALLET_ADDRESS = "Wallet_Address"

# The private key corresponding to the admin wallet. 
# Used by the script to autonomously sign transactions (ECDSA signatures) without manual user input.
PRIVATE_KEY = "Your_Private_Key_here" 

# ==========================================
# 3. SMART CONTRACT JSON ABI
# ==========================================
# Python requires the strict JSON format for the Application Binary Interface (ABI).
# We only define the 'addFile' function here, as the daemon only handles the ingestion phase.
ABI = [
    {
        "inputs": [
            {"internalType": "uint256", "name": "fileId", "type": "uint256"},
            {"internalType": "string", "name": "cid", "type": "string"},
            {"internalType": "string", "name": "fileName", "type": "string"}
        ],
        "name": "addFile",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

# Initialize the Web3 connection to the Ganache node and instantiate the contract object.
w3 = Web3(Web3.HTTPProvider(GANACHE_URL))
contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=ABI)

# ==========================================
# 4. AUTONOMOUS INGESTION PIPELINE
# ==========================================
class AutonomousPipeline(FileSystemEventHandler):
    """
    This class handles the events triggered by the Watchdog observer.
    It executes the vaulting and anchoring sequence whenever a new file is detected.
    """
    def on_created(self, event):
        # Ignore directory creation, only trigger the process for actual files
        if not event.is_directory:
            file_path = event.src_path
            file_name = os.path.basename(file_path)
            
            # Wait 1 second to ensure the OS has completely finished writing the file to the folder.
            # This prevents Python from trying to upload an incomplete file.
            time.sleep(1)
            
            print(f"\n[+] NEW DOCUMENT DETECTED: {file_name}")
            print(f"[*] Encrypting to air-gapped IPFS vault...")
            
            try:
                # ---------------------------------------------------------
                # STEP 1: UPLOAD TO IPFS
                # ---------------------------------------------------------
                # Execute the IPFS CLI command as a subprocess.
                # The '-Q' (Quiet) flag ensures only the Content Identifier (CID) hash is returned.
                result = subprocess.run([IPFS_EXE, 'add', '-Q', file_path], capture_output=True, text=True, check=True)
                
                # Strip newline characters to isolate the pure CID string.
                cid = result.stdout.strip()
                print(f"[✓] Vault Secured. CID: {cid}")

                # ---------------------------------------------------------
                # STEP 2: ANCHOR TO BLOCKCHAIN
                # ---------------------------------------------------------
                print(f"[*] Constructing Smart Contract transaction...")
                
                # Generate a unique File ID using the current UNIX timestamp.
                # This guarantees a unique primary key for the ledger database automatically.
                file_id = int(time.time())
                
                print(f"\n=============================================")
                print(f"🔑 IMPORTANT - YOUR FILE ID IS: {file_id}")
                print(f"=============================================\n")
                
                # Get the current transaction count for the wallet (nonce) to prevent replay attacks.
                nonce = w3.eth.get_transaction_count(WALLET_ADDRESS)
                
                # Build the raw transaction bytecode to call addFile(uint256, string, string)
                tx = contract.functions.addFile(file_id, cid, file_name).build_transaction({
                    'chainId': 1337, # Local Ganache Chain ID
                    'gas': 3000000,  # Execution gas limit
                    'gasPrice': w3.to_wei('20', 'gwei'),
                    'nonce': nonce,
                })

                # Sign the transaction with the Admin Private Key (secp256k1 Elliptic Curve signature)
                signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)

                # Broadcast the signed transaction to the Ganache ledger.
                tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                
                # Halt execution until the EVM confirms the block has been mathematically verified (mined).
                receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
                
                print(f"[✓] BLOCKCHAIN ANCHOR SUCCESSFUL!")
                print(f"[>] Transaction Hash: {tx_hash.hex()}")
                print(f"[>] Gas Used: {receipt['gasUsed']}") # Safest way to read the receipt across all versions
                
            # Handle instances where the IPFS executable fails (e.g., daemon is offline)
            except subprocess.CalledProcessError as e:
                print(f"[!] IPFS DAEMON FAULT: Make sure 'ipfs daemon' is running.\n{e}")
            # Catch all other system or Web3 faults to prevent the daemon from crashing
            except Exception as e:
                print(f"[!] SYSTEM FAULT: \n{e}")

# ==========================================
# 5. SYSTEM INITIALIZATION & MAIN LOOP
# ==========================================
if __name__ == "__main__":
    # Ensure the dropzone folder physically exists on the OS; create it if it does not.
    if not os.path.exists(FOLDER_TO_WATCH):
        os.makedirs(FOLDER_TO_WATCH)
        
    # Verify the JSON-RPC connection to the Ethereum ledger before proceeding.
    if not w3.is_connected():
        print("[!] ERROR: Cannot connect to Ganache. Check the GANACHE_URL and ensure Ganache is running.")
        exit()

    # Initialize the event handler and bind it to the Watchdog observer.
    event_handler = AutonomousPipeline()
    observer = Observer()
    observer.schedule(event_handler, FOLDER_TO_WATCH, recursive=False)
    
    # Print the initialization status to the terminal
    print(f"==================================================")
    print(f"Connected to Ganache: {w3.is_connected()}")
    print(f"Monitoring Dropzone: {FOLDER_TO_WATCH}")
    print(f"==================================================")
    
    # Start the background monitoring thread
    observer.start()
    try:
        # Keep the radar spinning; this infinite loop keeps the main script alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        # Graceful shutdown protocol if interrupted by the user (Ctrl+C)
        print("\n[!] Shutting down Auto-Loader...")
        observer.stop()
    observer.join()
