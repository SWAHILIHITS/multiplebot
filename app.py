import socket

def check_udp_port(ip_address: str, port: int, timeout: int = 3):
    """
    Sends a test packet to a UDP port to check if it is reachable.
    """
    print(f"Testing connection to {ip_address} on UDP port {port}...")
    
    # Create a UDP socket (SOCK_DGRAM indicates UDP)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    
    try:
        # Send a dummy byte to the target
        sock.sendto(b'\x00', (ip_address, port))
        
        # Try to receive data back
        data, addr = sock.recvfrom(1024)
        print("Success! Port is open and responsive.")
    except socket.timeout:
        print("Timeout: The port might be blocked by a firewall, or the device ignored the empty packet.")
    except Exception as e:
        print(f"Network error occurred: {e}")
    finally:
        # Always clean up and close the socket
        sock.close()

if __name__ == "__main__":
    # Test your Ruijie device IP and the standard SNMP port
    check_udp_port("192.168.0.46", 161)
abc=2
