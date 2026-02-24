// SPDX-License-Identifier: MIT
// The "pragma" tells the system which version of the Solidity language to use.
pragma solidity ^0.8.0;

// Think of a "contract" as an unbreakable, automated rulebook and database stored on the blockchain.
contract SecureLogAccess {
    
    // Stores the Ethereum wallet address of the "Admin" (the person who deployed this contract).
    address public owner;

    // A "struct" is like a blueprint. Here we define what information makes up a "File".
    struct FileRecord {
        string cid;       // The unique IPFS fingerprint (like a digital barcode) to find the file.
        string fileName;  // The human-readable name of the file (e.g., "SecretPlan.pdf").
        bool exists;      // A simple True/False switch to check if this file ID actually exists.
    }

    // "Mappings" are like digital filing cabinets or Excel spreadsheets.
    // 1. This cabinet links a File ID (a number) to its FileRecord (the blueprint above).
    mapping (uint => FileRecord) private files;
    
    // 2. This cabinet is for security. It links a File ID -> to a User's Wallet Address -> to a True/False permission.
    // Example: File 101 -> Wallet 0xABC... -> True (Allowed to view)
    mapping (uint => mapping (address => bool)) private authorizedUsers;

    // "Events" are permanent, un-erasable ink stamps on the blockchain. They act as our Audit Trail.
    
    // Event 1: Triggered when someone opens the main container (like a ZIP file or a standalone PDF).
    event FileAccessed(uint indexed fileId, string fileName, address indexed user, uint timestamp);
    
    // Event 2: Triggered when someone clicks a specific document INSIDE a ZIP container.
    event SubFileAccessed(uint indexed fileId, string subFileName, address indexed user, uint timestamp);

    // Event 3: Triggered when the Admin grants a new user access to a file.
    event AccessGranted(uint indexed fileId, address indexed user);

    // Event 4: Triggered when admin rights are handed over to someone else.
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);

    // The "constructor" runs exactly ONE time in history: the exact second you click "Deploy".
    constructor() {
        // 'msg.sender' means "the person pushing the button right now". 
        // We set the creator of the contract to be the permanent 'owner' (Admin).
        owner = msg.sender;
    }

    // A "modifier" acts like a bouncer at the door of a VIP club.
    modifier onlyOwner() {
        // It checks: "Is the person trying to do this the exact same person listed as the owner?"
        require(msg.sender == owner, "Only Owner");
        _; // If yes, let them inside to run the rest of the function.
    }

    // ADMIN FUNCTION: Uploads the file's metadata to the blockchain.
    // The "onlyOwner" tag means ONLY the Admin can run this.
    function addFile(uint _id, string memory _cid, string memory _name) public onlyOwner {
        // Save the file details into the 'files' filing cabinet.
        files[_id] = FileRecord(_cid, _name, true);
        // Automatically give the Admin permission to view the file they just uploaded.
        authorizedUsers[_id][owner] = true;
    }

    // ADMIN FUNCTION: Grants permission to a specific user.
    function authorizeUser(uint _id, address _user) public onlyOwner {
        // First check: Does this file actually exist?
        require(files[_id].exists, "File Not Found");
        
        // Flip the switch in the 'authorizedUsers' cabinet to True for this specific person.
        authorizedUsers[_id][_user] = true;
        
        // Stamp the blockchain to prove this access was granted.
        emit AccessGranted(_id, _user);
    }

    // USER FUNCTION: The main action. A user asks to view a file.
    function accessFile(uint _id) public returns (string memory) {
        // Check 1: Does the file exist?
        require(files[_id].exists, "File Not Found");
        
        // Check 2: Does the person calling this function (msg.sender) have permission?
        require(authorizedUsers[_id][msg.sender], "Not Authorized");
        
        // Stamp the blockchain to permanently log that this exact user accessed this exact file right now.
        emit FileAccessed(_id, files[_id].fileName, msg.sender, block.timestamp);
        
        // If all checks pass, hand the user the secret IPFS fingerprint (CID) so they can download the file.
        return files[_id].cid; 
    }

    // USER FUNCTION: The granular tracker. Used when a user clicks a specific file inside a ZIP archive.
    function logSubFile(uint _id, string memory _subName) public {
        // Same security checks as above.
        require(files[_id].exists, "File Not Found");
        require(authorizedUsers[_id][msg.sender], "Not Authorized");
        
        // Emit the highly specific granular log (e.g., "User viewed 'Financials.docx' inside File 101").
        emit SubFileAccessed(_id, _subName, msg.sender, block.timestamp);
    }

    // ADMIN FUNCTION: Hand over the keys to the castle.
    function transferOwnership(address _newOwner) public onlyOwner {
        // Make sure we aren't transferring ownership to nobody (the zero address).
        require(_newOwner != address(0), "Invalid Address");
        
        // Stamp the blockchain to log the transfer.
        emit OwnershipTransferred(owner, _newOwner);
        
        // Change the master admin to the new address.
        owner = _newOwner; 
    }
}
