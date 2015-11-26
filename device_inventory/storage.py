import paramiko


def copy_file_to_server(localpath, remotepath, username, password, server):
    """
    Any other exception will be passed through.
    
    :raises AuthenticationException: if authentication failed
    :raises SSHException: if there was any other error connecting or
        establishing an SSH session
    :raises socket.error: if a socket error occurred while connecting
    """
    print("Connecting to server...")
    # FIXME run os.path.isdir(remotepath) via SSH?
    assert not remotepath.endswith("/"), "SFTP needs a full filename path (not a folder)"
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(server, username=username, password=password, timeout=30)
    
    sftp = ssh.open_sftp()
    sftp.put(localpath, remotepath)
    sftp.close()
    ssh.close()
