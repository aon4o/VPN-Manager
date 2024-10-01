import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
import sqlite3
import os
import tempfile
import subprocess
import threading
import pyotp
from pyzbar.pyzbar import decode
from PIL import Image

DATABASE = 'vpn_configs.db'

class VPNApp(Gtk.Window):
    def __init__(self):
        super().__init__(title="VPN Manager")
        self.set_border_width(10)
        self.set_default_size(600, 400)

        # Initialize database
        self.init_db()

        # Main layout
        vbox = Gtk.VBox(spacing=6)
        self.add(vbox)

        # Status label
        self.status_label = Gtk.Label(label="Status: Checking...")
        vbox.pack_start(self.status_label, False, False, 0)

        # VPN List
        self.store = Gtk.ListStore(int, str)  # id, name
        self.treeview = Gtk.TreeView(model=self.store)
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Connection Name", renderer, text=1)
        self.treeview.append_column(column)

        # Action buttons
        connect_button = Gtk.Button(label="Connect")
        connect_button.connect("clicked", self.on_connect_clicked)
        disconnect_button = Gtk.Button(label="Disconnect")
        disconnect_button.connect("clicked", self.on_disconnect_clicked)
        delete_button = Gtk.Button(label="Delete")
        delete_button.connect("clicked", self.on_delete_clicked)
        new_button = Gtk.Button(label="New")
        new_button.connect("clicked", self.on_new_clicked)

        button_box = Gtk.HBox(spacing=6)
        button_box.pack_start(connect_button, True, True, 0)
        button_box.pack_start(disconnect_button, True, True, 0)
        button_box.pack_start(delete_button, True, True, 0)
        button_box.pack_start(new_button, True, True, 0)

        # Add to layout
        vbox.pack_start(self.treeview, True, True, 0)
        vbox.pack_start(button_box, False, False, 0)

        # Load VPN configurations
        self.load_configs()

        # Update status
        self.update_status()

        # Set up a timer to periodically update the status
        GLib.timeout_add_seconds(5, self.update_status)

    def init_db(self):
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS vpn_configs
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      name TEXT,
                      username TEXT,
                      password TEXT,
                      qr_code_path TEXT,
                      ovpn_config_path TEXT)''')
        conn.commit()
        conn.close()

    def load_configs(self):
        self.store.clear()
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("SELECT id, name FROM vpn_configs")
        for row in c.fetchall():
            self.store.append(row)
        conn.close()

    def on_new_clicked(self, widget):
        dialog = NewConfigDialog(self)
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            data = dialog.get_data()
            conn = sqlite3.connect(DATABASE)
            c = conn.cursor()
            c.execute("INSERT INTO vpn_configs (name, username, password, qr_code_path, ovpn_config_path) VALUES (?, ?, ?, ?, ?)",
                      (data['name'], data['username'], data['password'], data['qr_code_path'], data['ovpn_config_path']))
            conn.commit()
            conn.close()
            self.load_configs()

        dialog.destroy()

    def on_delete_clicked(self, widget):
        selection = self.treeview.get_selection()
        model, treeiter = selection.get_selected()
        if treeiter is not None:
            vpn_id = model[treeiter][0]
            conn = sqlite3.connect(DATABASE)
            c = conn.cursor()
            c.execute("DELETE FROM vpn_configs WHERE id = ?", (vpn_id,))
            conn.commit()
            conn.close()
            self.load_configs()

    def on_connect_clicked(self, widget):
        if self.is_connected():
            self.show_message("Already Connected", "VPN is already connected.")
            return

        selection = self.treeview.get_selection()
        model, treeiter = selection.get_selected()
        if treeiter is None:
            self.show_message("No Selection", "Please select a VPN configuration.")
            return

        vpn_id = model[treeiter][0]

        # Get VPN configuration
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("SELECT name, username, password, qr_code_path, ovpn_config_path FROM vpn_configs WHERE id = ?", (vpn_id,))
        vpn = c.fetchone()
        conn.close()

        if vpn is None:
            self.show_message("Error", "VPN configuration not found.")
            return

        name, username, password, qr_code_path, ovpn_config_path = vpn

        # Generate OTP
        try:
            secret = self.read_qr_code(qr_code_path)
            totp = pyotp.TOTP(secret)
            otp = totp.now()
        except Exception as e:
            self.show_message("Error", f"Failed to generate OTP: {e}")
            return

        # Create auth file
        auth_file = tempfile.NamedTemporaryFile(delete=False)
        auth_file.write(f"{username}\n{password}\n".encode())
        auth_file.close()
        os.chmod(auth_file.name, 0o600)

        # Generate expect script
        expect_script = self.generate_expect_script(ovpn_config_path, auth_file.name, otp)

        # Start VPN connection in a new thread
        threading.Thread(target=self.connect_vpn, args=(expect_script, auth_file.name)).start()

    def on_disconnect_clicked(self, widget):
        if not self.is_connected():
            self.show_message("Not Connected", "VPN is not connected.")
            return
        threading.Thread(target=self.disconnect_vpn).start()

    def connect_vpn(self, expect_script_path, auth_file_path):
        try:
            process = subprocess.Popen(['expect', expect_script_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()

            if process.returncode == 0:
                # Wait a bit and check connection
                threading.Event().wait(10)
                if self.is_connected():
                    GLib.idle_add(self.update_status)
                    GLib.idle_add(self.show_message, "Connected", "VPN connection established successfully.")
                else:
                    GLib.idle_add(self.show_message, "Connection Failed", "VPN connection failed to establish.")
            else:
                error_message = stderr.decode() or "Unknown error occurred."
                GLib.idle_add(self.show_message, "Connection Error", f"VPN connection error: {error_message}")

        except Exception as e:
            GLib.idle_add(self.show_message, "Error", f"Error during VPN connection: {e}")
        finally:
            os.unlink(auth_file_path)
            os.unlink(expect_script_path)
            GLib.idle_add(self.update_status)

    def disconnect_vpn(self):
        pid_file = '/tmp/vpn_manager.pid'
        if not os.path.exists(pid_file):
            GLib.idle_add(self.show_message, "Disconnect Error", "PID file not found.")
            return
        with open(pid_file, 'r') as f:
            pid = f.read().strip()
        try:
            process = subprocess.Popen(['pkexec', 'kill', pid], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            if process.returncode == 0:
                # Wait a bit and check if disconnected
                threading.Event().wait(5)
                if not self.is_connected():
                    GLib.idle_add(self.update_status)
                    GLib.idle_add(self.show_message, "Disconnected", "VPN disconnected successfully.")
                else:
                    GLib.idle_add(self.show_message, "Disconnect Failed", "VPN failed to disconnect.")
            else:
                error_message = stderr.decode() or "Unknown error occurred."
                GLib.idle_add(self.show_message, "Disconnect Error", f"VPN disconnect error: {error_message}")
        except Exception as e:
            GLib.idle_add(self.show_message, "Error", f"Error during VPN disconnect: {e}")
        finally:
            if os.path.exists(pid_file):
                os.unlink(pid_file)
            GLib.idle_add(self.update_status)

    def read_qr_code(self, qr_code_path):
        data = decode(Image.open(qr_code_path))
        if not data:
            raise Exception("QR code could not be decoded.")
        qr_data = data[0].data.decode()
        # Extract secret from QR code data
        if 'secret=' in qr_data:
            import urllib.parse
            parsed = urllib.parse.urlparse(qr_data)
            params = urllib.parse.parse_qs(parsed.query)
            secret = params.get('secret', [None])[0]
            if secret:
                return secret
        raise Exception("Secret key not found in QR code.")

    def generate_expect_script(self, ovpn_config_path, auth_file_path, otp):
        pid_file = '/tmp/vpn_manager.pid'
        script_content = f"""
#!/usr/bin/expect -f
set timeout -1

spawn pkexec /bin/sh -c "openvpn --writepid '{pid_file}' --config '{ovpn_config_path}' --auth-user-pass '{auth_file_path}'"

expect {{
    "CHALLENGE:" {{
        send "{otp}\\r"
        exp_continue
    }}
    eof {{
        exit 0
    }}
    timeout {{
        exit 1
    }}
}}
"""
        script_file = tempfile.NamedTemporaryFile(delete=False)
        script_file.write(script_content.encode())
        script_file.close()
        os.chmod(script_file.name, 0o700)
        return script_file.name

    def is_connected(self):
        try:
            output = subprocess.check_output(['ip', 'addr', 'show', 'dev', 'tun0'], stderr=subprocess.STDOUT)
            return True
        except subprocess.CalledProcessError:
            return False

    def update_status(self):
        if self.is_connected():
            self.status_label.set_text("Status: Connected")
        else:
            self.status_label.set_text("Status: Disconnected")
        # Return True to keep the timer running
        return True

    def show_message(self, title, message):
        dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK, title)
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

class NewConfigDialog(Gtk.Dialog):
    def __init__(self, parent):
        Gtk.Dialog.__init__(self, "New VPN Configuration", parent, 0,
                            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                             Gtk.STOCK_OK, Gtk.ResponseType.OK))

        self.set_default_size(400, 300)

        box = self.get_content_area()

        grid = Gtk.Grid(column_spacing=10, row_spacing=10, margin=10)
        box.add(grid)

        name_label = Gtk.Label(label="Display Name:")
        self.name_entry = Gtk.Entry()

        username_label = Gtk.Label(label="Username:")
        self.username_entry = Gtk.Entry()

        password_label = Gtk.Label(label="Password:")
        self.password_entry = Gtk.Entry()
        self.password_entry.set_visibility(False)

        qr_code_label = Gtk.Label(label="QR Code (.png):")
        self.qr_code_button = Gtk.FileChooserButton(title="Select QR Code File", action=Gtk.FileChooserAction.OPEN)
        self.qr_code_button.set_filter(self.get_image_filter())

        ovpn_label = Gtk.Label(label=".ovpn Config File:")
        self.ovpn_button = Gtk.FileChooserButton(title="Select .ovpn Config File", action=Gtk.FileChooserAction.OPEN)
        self.ovpn_button.set_filter(self.get_ovpn_filter())

        grid.attach(name_label, 0, 0, 1, 1)
        grid.attach(self.name_entry, 1, 0, 1, 1)
        grid.attach(username_label, 0, 1, 1, 1)
        grid.attach(self.username_entry, 1, 1, 1, 1)
        grid.attach(password_label, 0, 2, 1, 1)
        grid.attach(self.password_entry, 1, 2, 1, 1)
        grid.attach(qr_code_label, 0, 3, 1, 1)
        grid.attach(self.qr_code_button, 1, 3, 1, 1)
        grid.attach(ovpn_label, 0, 4, 1, 1)
        grid.attach(self.ovpn_button, 1, 4, 1, 1)

        self.show_all()

    def get_image_filter(self):
        image_filter = Gtk.FileFilter()
        image_filter.set_name("PNG Images")
        image_filter.add_mime_type("image/png")
        return image_filter

    def get_ovpn_filter(self):
        ovpn_filter = Gtk.FileFilter()
        ovpn_filter.set_name("OpenVPN Config Files")
        ovpn_filter.add_pattern("*.ovpn")
        return ovpn_filter

    def get_data(self):
        return {
            'name': self.name_entry.get_text(),
            'username': self.username_entry.get_text(),
            'password': self.password_entry.get_text(),
            'qr_code_path': self.qr_code_button.get_filename(),
            'ovpn_config_path': self.ovpn_button.get_filename()
        }

def main():
    app = VPNApp()
    app.connect("destroy", Gtk.main_quit)
    app.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()
