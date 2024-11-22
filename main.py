import re
import time
import logging
import socket
import paramiko
from pydantic_settings import BaseSettings
from routeros_api import RouterOsApiPool, exceptions


# Configuration using pydantic settings
class Settings(BaseSettings):
    CHECK_INTERVAL: int = 60  # Time in seconds between connectivity checks

    # SSH configuration
    SSH_HOST: str = ""
    SSH_PORT: int = 22
    SSH_USER: str = ""
    SSH_PASSWORD: str = ""
    LIST_VIDS_COMMAND: str = "omcicli mib get 84"

    # Mikrotik API configuration
    MIKROTIK_HOST: str = ""
    MIKROTIK_USER: str = ""
    MIKROTIK_PASSWORD: str = ""
    MIKROTIK_PORT: int = 8728
    MIKROTIK_USE_SSL: bool = False
    MIKROTIK_SSL_VERIFY: bool = True
    MIKROTIK_SSL_VERIFY_HOSTNAME: bool = True
    MIKROTIK_PLAINTEXT_LOGIN: bool = True

    # Interface to update
    INTERFACE_NAME: str = "vlan35"

    # PPPoE Client interface name
    PPPOE_INTERFACE_NAME: str = "pppoe-wan"
    
    LOGGING_LEVEL: str = "INFO"


settings = Settings()

level = logging.getLevelName(settings.LOGGING_LEVEL)
logging.basicConfig(level=level)
logger = logging.getLogger(__name__)


def is_pppoe_connected():
    try:
        api_pool = RouterOsApiPool(
            settings.MIKROTIK_HOST,
            username=settings.MIKROTIK_USER,
            password=settings.MIKROTIK_PASSWORD,
            port=settings.MIKROTIK_PORT,
            use_ssl=settings.MIKROTIK_USE_SSL,
            ssl_verify=settings.MIKROTIK_SSL_VERIFY,
            ssl_verify_hostname=settings.MIKROTIK_SSL_VERIFY_HOSTNAME,
            plaintext_login=settings.MIKROTIK_PLAINTEXT_LOGIN
        )
        api = api_pool.get_api()
        interface_resource = api.get_resource("/interface")
        pppoe_interfaces = interface_resource.get(name=settings.PPPOE_INTERFACE_NAME)
        if not pppoe_interfaces:
            logger.error(f"PPPoE interface {settings.PPPOE_INTERFACE_NAME} not found.")
            api_pool.disconnect()
            return False
        pppoe_interface = pppoe_interfaces[0]
        # Check "running" flag
        is_running = pppoe_interface.get("running", "false") == "true"
        api_pool.disconnect()
        return is_running
    except exceptions.RouterOsApiConnectionError:
        logger.error("Failed to connect to Mikrotik API.", exc_info=True)
        return False
    except Exception:
        logger.error("Failed to check PPPoE interface status.", exc_info=True)
        return False


def get_vids_from_ssh():
    try:
        # Create an SSH client
        client = paramiko.SSHClient()
        # Automatically add untrusted hosts (security risk in production)
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Create a custom Transport object with old algorithms
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((settings.SSH_HOST, settings.SSH_PORT))
        transport = paramiko.Transport(sock)

        # Modify security options to include old algorithms
        security_options = transport.get_security_options()
        security_options.ciphers = ["3des-cbc"]
        security_options.kex = ["diffie-hellman-group1-sha1"]
        security_options.host_key = ["ssh-rsa"]

        # Authenticate
        transport.connect(username=settings.SSH_USER, password=settings.SSH_PASSWORD)

        # Open a session
        channel = transport.open_session()
        channel.get_pty()
        channel.invoke_shell()

        # Wait for the prompt
        buff = ""
        while not buff.endswith("# "):
            resp = channel.recv(9999)
            buff += resp.decode("utf-8")

        # Send command
        channel.send(f"{settings.LIST_VIDS_COMMAND}\n".encode())

        # Read command output
        buff = ""
        while True:
            resp = channel.recv(9999)
            buff += resp.decode("utf-8")
            if buff.endswith("# "):
                break

        # Close the connection
        channel.close()
        transport.close()

        # Parse VIDs
        vids = re.findall(r"VID (\d+)", buff)
        logger.info(f"Extracted VIDs: {vids}")
        return vids

    except Exception:
        logger.error("Failed to get VIDs via SSH.", exc_info=True)
        return []


def update_mikrotik_vlan(vids):
    try:
        api_pool = RouterOsApiPool(
            settings.MIKROTIK_HOST,
            username=settings.MIKROTIK_USER,
            password=settings.MIKROTIK_PASSWORD,
            port=settings.MIKROTIK_PORT,
            use_ssl=settings.MIKROTIK_USE_SSL,
            ssl_verify=settings.MIKROTIK_SSL_VERIFY,
            ssl_verify_hostname=settings.MIKROTIK_SSL_VERIFY_HOSTNAME,
            plaintext_login=settings.MIKROTIK_PLAINTEXT_LOGIN
        )
        api = api_pool.get_api()
        vlan_resource = api.get_resource("/interface/vlan")
        # Find the interface by name
        vlan_interfaces = vlan_resource.get(name=settings.INTERFACE_NAME)
        if not vlan_interfaces:
            logger.error(f"Interface {settings.INTERFACE_NAME} not found.")
            return
        interface_id = vlan_interfaces[0]["id"]

        for vid in vids:
            logger.info(f"Setting VLAN ID {vid} on interface {settings.INTERFACE_NAME}")
            vlan_resource.set(id=interface_id, **{"vlan-id": vid})
            logger.info(f"Updated {settings.INTERFACE_NAME} with VLAN ID {vid}")

            # Wait up to 60 seconds for PPPoE Client to connect
            start_time = time.time()
            while time.time() - start_time < 60:
                if is_pppoe_connected():
                    logger.info(f"PPPoE Client connected with VLAN ID {vid}")
                    api_pool.disconnect()
                    return  # Exit function as we have successfully connected
                else:
                    logger.info("Waiting for PPPoE Client to connect...")
                    time.sleep(5)  # Wait 5 seconds before checking again
            # If PPPoE did not connect within 60 seconds, try next VID
            logger.info(f"PPPoE Client did not connect with VLAN ID {vid}, trying next VID")
        # If none of the VIDs worked
        logger.error("None of the VIDs resulted in PPPoE Client connecting.")
        api_pool.disconnect()
    except exceptions.RouterOsApiConnectionError:
        logger.error("Failed to connect to Mikrotik API.", exc_info=True)
    except Exception:
        logger.error("Failed to update Mikrotik VLAN.", exc_info=True)


def main():
    while True:
        if is_pppoe_connected():
            logger.info(
                f"PPPoE Client {settings.PPPOE_INTERFACE_NAME} is connected. Checking again in {settings.CHECK_INTERVAL} seconds.")
        else:
            logger.info(
                f"PPPoE Client {settings.PPPOE_INTERFACE_NAME} is not connected. Proceeding to update VLAN IDs.")
            vids = get_vids_from_ssh()
            if vids:
                update_mikrotik_vlan(vids)
            else:
                logger.error("No VIDs extracted. Skipping Mikrotik update.")
        time.sleep(settings.CHECK_INTERVAL)


if __name__ == "__main__":
    main()
