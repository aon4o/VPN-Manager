from gi.repository import Gtk


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
