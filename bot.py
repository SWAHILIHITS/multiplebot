import socket
import logging

# Set up simple logging for accurate diagnostic reporting
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
appLogger = logging.getLogger("SNMPTester")

def test_local_snmp_udp_port(target_ip: str, port: int = 161, timeout: int = 3):
    """
    Tests UDP port 161 by sending a minimally valid SNMPv3 Header 
    to trigger a valid response from the router.
    
    Parameters:
        target_ip (str): The local IP address of the router (e.g., '192.168.0.46').
        port (int): The destination UDP port (default is 161 for SNMP).
        timeout (int): Seconds to wait for a packet before timing out.
    """
    appLogger.info(f"Initiating local socket test to {target_ip}:{port}...")

    # A minimal binary SNMPv3 GetRequest header to provoke a response
    # Real SNMP engines discard raw null bytes (b'\x00')
    snmpv3_discovery_packet = bytes.fromhex(
        "303a0201030410300e0201010201000400040002010004000400301d0400020100020100040004000400020100020100020100"
    )

    # Create an IPv4 (AF_INET) UDP (SOCK_DGRAM) socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)

    try:
        # Send the SNMPv3 test packet to the local target router
        sock.sendto(snmpv3_discovery_packet, (target_ip, port))
        
        # Buffer up to 1024 bytes of incoming data
        data, addr = sock.recvfrom(1024)
        
        appLogger.info(f"SUCCESS: Received {len(data)} bytes back from {addr[0]}:{addr[1]}. Port 161 is reachable!")
        return True

    except socket.timeout:
        appLogger.error("FAILURE (Timeout): No response received. Possible causes:")
        appLogger.error(" 1. The script is running outside the local 192.168.0.x network.")
        appLogger.error(" 2. A local host firewall is blocking outbound UDP on Port 161.")
        return False

    except Exception as ex:
        appLogger.error(f"FAILURE (Socket Error): {ex}")
        return False

    finally:
        # Guarantee socket closure to free system network resources
        sock.close()

if __name__ == "__main__":
    # IMPORTANT: Run this script on a machine connected to the local network (192.168.0.x)
    ROUTER_LOCAL_IP = "192.168.0.46"
    test_local_snmp_udp_port(ROUTER_LOCAL_IP)
