import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from src.vpn_app import VPNApp


def main():
    app = VPNApp()
    app.connect("destroy", Gtk.main_quit)
    app.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()
