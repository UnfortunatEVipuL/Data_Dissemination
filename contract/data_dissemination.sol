// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract SecureLogAccess {
    address public owner;

    struct FileRecord {
        string cid;
        string fileName;
        bool exists;
    }

    mapping (uint => FileRecord) private files;
    mapping (uint => mapping (address => bool)) private authorizedUsers;

    // Event 1: Accessed the Main Container (ZIP/PDF)
    event FileAccessed(uint indexed fileId, string fileName, address indexed user, uint timestamp);
    
    // Accessed a file INSIDE the container
    event SubFileAccessed(uint indexed fileId, string subFileName, address indexed user, uint timestamp);

    event AccessGranted(uint indexed fileId, address indexed user);

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Only Owner");
        _;
    }

    function addFile(uint _id, string memory _cid, string memory _name) public onlyOwner {
        files[_id] = FileRecord(_cid, _name, true);
        authorizedUsers[_id][owner] = true;
    }

    function authorizeUser(uint _id, address _user) public onlyOwner {
        require(files[_id].exists, "File Not Found");
        authorizedUsers[_id][_user] = true;
        emit AccessGranted(_id, _user);
    }

    // Main Access
    function accessFile(uint _id) public returns (string memory) {
        require(files[_id].exists, "File Not Found");
        require(authorizedUsers[_id][msg.sender], "Not Authorized");
        emit FileAccessed(_id, files[_id].fileName, msg.sender, block.timestamp);
        return files[_id].cid; 
    }

    // Sub-File Logger
    function logSubFile(uint _id, string memory _subName) public {
        require(files[_id].exists, "File Not Found");
        require(authorizedUsers[_id][msg.sender], "Not Authorized");
        
        // Emit the granular log
        emit SubFileAccessed(_id, _subName, msg.sender, block.timestamp);
    }
}