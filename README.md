# File Upload and Download Server

This program is a simple file upload and download server implemented in Python. It provides a basic HTTP server that allows users to upload files, download files, and perform various file operations such as listing files, retrieving file information, updating files, and deleting files.

Please note that this program uses only the `socket` package in Python and does not rely on any other HTTP-specific packages or frameworks. It is implemented from scratch to demonstrate the underlying principles of HTTP communication and file handling.

## Prerequisites

- Python 3.10.7

## Usage

To use the file upload and download server, follow these steps:

1. Set up the server:
   - Make sure you have Python 3.x installed on your system.
   - Copy the code provided into a Python file (e.g., `server.py`).
   - Save the file.

2. Customize server settings (optional):
   - The program includes a few configurable parameters at the beginning of the code:
     - `STATIC_FOLDER`: The folder where static files (e.g., HTML, CSS, JavaScript) are stored.
     - `UPLOAD_FOLDER`: The folder where uploaded files will be stored.
     - `TOKEN`: A secret token used for authentication.
   - Modify these parameters according to your desired setup.

3. Run the server:
   - Open a terminal or command prompt.
   - Navigate to the directory where you saved the Python file.
   - Execute the following command to run the server: `python server.py`
   - The server will start running and display the URL where it is accessible ( e.g., [`http://localhost:8000`](http://localhost:8000) ).

4. Interact with the server:
   - Open a web browser and navigate to the server's URL.
   - You can perform the following actions:

     - **Upload a File**:
       - Click on the file upload button or a designated area on the webpage to select a file from your computer.
       - After selecting the file, it will be uploaded to the server's `UPLOAD_FOLDER`.
       - If a file with the same name already exists, an error will be displayed.

     - **Download a File**:
       - Click on the file download link or button to download a file from the server.
       - The file will be downloaded to your computer.

     - **List Files**:
       - Access the `/file-list` URL to get a list of uploaded files.
       - The server will respond with a JSON object containing file information, such as file name, URL, and size.

     - **Update a File**:
       - Send a `PUT` request to the server with the updated file content.
       - The file content will be replaced with the new content in the server's `UPLOAD_FOLDER`.
       - If the file does not exist, an error will be displayed.

     - **Delete a File**:
       - Send a `DELETE` request to the server with the file name or path.
       - The file will be deleted from the server's `UPLOAD_FOLDER`.
       - If the file does not exist, an error will be displayed.

## Customization

You can customize the server according to your requirements. Here are a few aspects you might consider modifying:

- **File Storage Locations**:
  - The `STATIC_FOLDER` variable determines the folder where static files (e.g., HTML, CSS, JavaScript) are stored. You can change this to point to your desired folder.
  - The `UPLOAD_FOLDER` variable determines the folder where uploaded files will be stored. Modify this to specify your desired upload location.

- **Authentication**:
  - The server includes a simple authentication mechanism using a token. The `TOKEN` variable stores the secret token used for authentication. Change this to a secure value for

 your application.

- **Additional Functionality**:
  - If you want to add more functionality or extend the server's capabilities, you can modify the code accordingly. The existing code provides a foundation for file upload, download, listing, updating, and deletion. You can build upon this foundation to suit your needs.

## Troubleshooting

If you encounter any issues or errors while running the server, please keep the following points in mind:

- Ensure that you have the necessary permissions to read/write files in the specified `STATIC_FOLDER` and `UPLOAD_FOLDER`.
- Check if any required Python modules are missing. If so, you can install them using the `pip` package manager.
- Make sure that the specified host and port are not already in use by another application on your system.

If you have any questions or need further assistance, please let us know.
