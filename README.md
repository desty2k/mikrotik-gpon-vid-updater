# mikrotik-gpon-vid-updater

Internet Service Providers (ISPs) like Orange may occasionally change the VLAN ID (VID) used for 
internet transmission without prior notice. Such unexpected changes can disrupt your internet connectivity, 
leaving your services offline if you rely on a static configuration and lack a backup connection. 
Manually updating the VLAN ID on your MikroTik router every time this happens can be inconvenient and time-consuming.

It periodically checks PPPoE interface status, and if it detects a connection failure, 
it verifies the current VID offered by your ISP and updates the VLAN ID on your MikroTik router accordingly. 
This ensures continuous internet connectivity without manual intervention, 
keeping your services online even when the ISP changes the VID.

Service has been tested with `ODI DFP-34X-2C2`. You can find more information using custom GPON sticks [here](https://github.com/Anime4000/RTL960x).

## Running

To run the container using `docker run`, execute the following command, replacing the environment variable values as needed:

```shell
docker run -d \
  --name mikrotik-gpon-vid-updater \
  -e SSH_HOST=your_ssh_host \
  -e SSH_USER=your_ssh_user \
  -e SSH_PASSWORD=your_ssh_password \
  -e MIKROTIK_HOST=your_mikrotik_host \
  -e MIKROTIK_USER=your_mikrotik_user \
  -e MIKROTIK_PASSWORD=your_mikrotik_password \
  -e INTERFACE_NAME=your_interface_name \
  -e PPPOE_INTERFACE_NAME=your_pppoe_interface_name \
  ghcr.io/desty2k/mikrotik-gpon-vid-updater
```

You can also use `compose` file. Create a `compose.yml` file with the following content, adjusting the environment variables as needed:

```yaml
services:
  mikrotik-gpon-vid-updater:
    image: ghcr.io/desty2k/mikrotik-gpon-vid-updater
    container_name: mikrotik-gpon-vid-updater
    environment:
      SSH_HOST: your_ssh_host
      SSH_USER: your_ssh_user
      SSH_PASSWORD: your_ssh_password
      MIKROTIK_HOST: your_mikrotik_host
      MIKROTIK_USER: your_mikrotik_user
      MIKROTIK_PASSWORD: your_mikrotik_password
      INTERFACE_NAME: your_interface_name
      PPPOE_INTERFACE_NAME: your_pppoe_interface_name
```

## Configuration

The application is configured using environment variables. Below is a table of all configuration options:

| Environment Variable             | Description                                                                         | Required |
|----------------------------------|-------------------------------------------------------------------------------------|----------|
| **CHECK_INTERVAL**               | Time in seconds between connectivity checks. Default is `60`.                       | No       |
| **SSH_HOST**                     | Hostname or IP address of the device to SSH into (e.g., the ONT).                   | **Yes**  |
| **SSH_PORT**                     | SSH port number. Default is `22`.                                                   | No       |
| **SSH_USER**                     | SSH username for the device.                                                        | **Yes**  |
| **SSH_PASSWORD**                 | SSH password for the device.                                                        | **Yes**  |
| **LIST_VIDS_COMMAND**            | Command to list the VIDs. Default is `"omcicli mib get 84"`.                        | No       |
| **MIKROTIK_HOST**                | Hostname or IP address of the MikroTik router.                                      | **Yes**  |
| **MIKROTIK_USER**                | Username for the MikroTik API access.                                               | **Yes**  |
| **MIKROTIK_PASSWORD**            | Password for the MikroTik API access.                                               | **Yes**  |
| **MIKROTIK_PORT**                | API port number for the MikroTik router. Default is `8728`.                         | No       |
| **MIKROTIK_USE_SSL**             | Whether to use SSL for MikroTik API connection. Default is `False`.                 | No       |
| **MIKROTIK_SSL_VERIFY**          | Verify SSL certificate for MikroTik API connection. Default is `True`.              | No       |
| **MIKROTIK_SSL_VERIFY_HOSTNAME** | Verify SSL hostname for MikroTik API connection. Default is `True`.                 | No       |
| **MIKROTIK_PLAINTEXT_LOGIN**     | Use plaintext login for MikroTik API. Default is `True`.                            | No       |
| **INTERFACE_NAME**               | Name of the VLAN interface to update on the MikroTik router (e.g., `vlan35`).       | **Yes**  |
| **PPPOE_INTERFACE_NAME**         | Name of the PPPoE client interface on the MikroTik router (e.g., `pppoe-wan`).      | **Yes**  |
| **LOGGING_LEVEL**                | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`). Default is `INFO`. | No       |

## Example

Here is an example of the application running:

```text
INFO:__main__:PPPoE Client pppoe-wan is connected. Checking again in 60 seconds.
INFO:__main__:PPPoE Client pppoe-wan is connected. Checking again in 60 seconds.
INFO:__main__:PPPoE Client pppoe-wan is not connected. Proceeding to update VLAN IDs.
INFO:paramiko.transport:Connected (version 2.0, client dropbear_0.48)
INFO:paramiko.transport:Authentication (password) successful!
INFO:__main__:Extracted VIDs: ['1303']
INFO:__main__:Setting VLAN ID 1303 on interface vlan35
INFO:__main__:Updated vlan35 with VLAN ID 1303
INFO:__main__:Waiting for PPPoE Client to connect...
INFO:__main__:PPPoE Client connected with VLAN ID 1303
```

Service will check every 60 seconds if PPPoE interface is connected. 
If not, it will extract VID from the ONT and try each one until PPPoE interface becomes connected.

## License

This project is licensed under the [MIT License](LICENSE).

## Contributing

Contributions are welcome! Please open an issue or submit a pull request if you have suggestions or improvements.
