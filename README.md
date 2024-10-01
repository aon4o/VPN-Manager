# VPN Manager

A simple VPN Manager application with OTP capabilities for Debian based linux distros.

## Installation

1. Clone the repository
2. Run the following command to install the required dependencies:
```bash
sudo apt-get install openvpn pipenv
```
3. Enter the virtual environment:
```bash
pipenv shell
```
4. Run the following command to install the required python packages:
```bash
pipenv install --dev
```
5. Run the following command to start the application:
```bash
python3 main.py
```

## Building an Executable

```shell
pyinstaller --onefile main.py
```