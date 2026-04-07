# Serial Modem

A Hayes-compatible WiFi modem for the Lilka ESP32-S3 handheld device. This firmware transforms your Lilka into a vintage WiFi modem, allowing classic computers to connect to the internet via WiFi using familiar AT commands through an RS232 serial connection.

Lilka connects to the computer via an RS232–TTL converter (MAX3232/SP3232EEN) to the TX and RX pins of the expansion port.

## Main features
- AT commands – compatibility with the Hayes command set (ATDT for dialing, ATH for hang up, AT$SB for changing speed, etc.)
- TCP/Telnet connections – connect to BBS and other services using hostname:port instead of a phone number
- PPP Dial-Up Networking – support for the PPP protocol to connect to the internet. Dial number: 777
- File transfer – upload and download files to the SD card using YMODEM/XMODEM protocols
- Web interface – manage modem settings, change speed, speed dial, SD card file manager, etc.
- Display – shows modem status on the Lilka screen, allows changing modem settings through the built-in menu

Supported speeds range from 300 to 115200 bps. Stable operation: 9600 bps by default (optimal for PPP and regular connections), 19200 bps is recommended for file transfer via YMODEM. Higher speeds may cause errors.