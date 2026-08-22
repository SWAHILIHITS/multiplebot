from pysnmp.hlapi import *
import logging

# Set up a basic logger to mimic your app's logging style
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
appLogger = logging.getLogger('appLogger')

def test_snmp_v3_connection():
    # Define the target IP from your device identifier list
    target_ip = '192.168.0.46'
    
    # We will query the standard SNMP sysDescr OID as a test
    oid = ObjectIdentity('SNMPv2-MIB', 'sysDescr', 0)

    try:
        iterator = getCmd(
            SnmpEngine(),
            UsmUserData(
                'Luv2laf.',                           # User Name
                authKey='Luv2laf.',                   # Auth Password
                privKey='Luv2laf.',                   # Encrypted Password
                authProtocol=usmHMACSHAAuthProtocol,  # Auth Protocol: SHA
                privProtocol=usmAesCfb128Protocol     # Encryption Protocol: AES
            ),
            UdpTransportTarget((target_ip, 161), timeout=2.0, retries=2), # Added explicit timeout
            ContextData(),
            ObjectType(oid)
        )

        errorIndication, errorStatus, errorIndex, varBinds = next(iterator)

        if errorIndication:
            # This is where your timeout error is currently being caught
            appLogger.error(f"SNMP Interface 1 Error: {errorIndication}")
        elif errorStatus:
            appLogger.error('%s at %s' % (errorStatus.prettyPrint(),
                                errorIndex and varBinds[int(errorIndex) - 1][0] or '?'))
        else:
            for varBind in varBinds:
                appLogger.info(f"Success! Response: {' = '.join([x.prettyPrint() for x in varBind])}")

    except Exception as e:
        appLogger.error(f"Unexpected application error: {e}")

if __name__ == "__main__":
    test_snmp_v3_connection()
