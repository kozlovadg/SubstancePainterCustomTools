import sys
import os
import re
import importlib
import substance_painter_plugins
import substance_painter.ui
import substance_painter.logging
import substance_painter.project
import _substance_painter.feature
from PySide2 import QtCore, QtGui, QtWidgets

LAUNCH_AT_START_KEY = "launch_at_start"

_pattern = re.compile(r"(?P<head>.*_v)(?P<version>\d{4})(?P<tail>\.spp)", re.U)

if _substance_painter.feature.is_enabled(
    _substance_painter.feature.RunTimeFeature.DebugMode
):
    PLUGINS_BLACKLIST = set()
else:
    PLUGINS_BLACKLIST = set(["sp_automation",])

translate = QtCore.QCoreApplication.translate


def get_settings(plugin_name):
    settings = QtCore.QSettings()
    settings.beginGroup("python_plugins/{}".format(plugin_name))
    return settings


def plugin_manager(name):
    @QtCore.Slot()
    def manage_plugin(start):
        get_settings(name).setValue(LAUNCH_AT_START_KEY, start)
        if start:
            try:
                module = sys.modules.get(name, None)
                if module:
                    # Reload plugin in case of restart to take potential
                    # changes into account.
                    substance_painter_plugins.reload_plugin(module)
                else:
                    module = importlib.import_module(name)
                    substance_painter_plugins.start_plugin(module)
            except Exception as exc:
                substance_painter.logging.error(
                    "Failed to start plugin {}".format(name)
                )
                substance_painter.logging.error(repr(exc))
        else:
            try:
                module = sys.modules[name]
                substance_painter_plugins.close_plugin(module)
            except Exception as exc:
                substance_painter.logging.error(
                    "Failed to stop plugin {}".format(name)
                )
                substance_painter.logging.error(repr(exc))

    return manage_plugin


def up_version(match):
    version_string = match.group("version")
    version_int = int(version_string)
    new_version_int = version_int + 1
    new_version_string = str(new_version_int).zfill(3)
    return "{}{}{}".format(
        match.group("head"), new_version_string, match.group("tail")
    )


@QtCore.Slot()
def scene_increment():
    try:

        current_file_path = substance_painter.project.file_path()
        new_file_path = _pattern.sub(up_version, current_file_path)

        if os.path.isfile(new_file_path):
            error_dialog = QtWidgets.QErrorMessage()
            error_dialog.showMessage(
                "File {} already exists.".format(
                    new_file_path
                )
            )
            error_dialog.exec_()
            substance_painter.logging.error("Could not Increment Scene")
        else:
            substance_painter.project.save()
            substance_painter.project.save_as(new_file_path)
    except:
        substance_painter.logging.error("Failed Scene Increment")


class PluginsMenu:
    def __init__(self):
        self._menu = QtWidgets.QMenu(
            translate("sp_plugins_ui", "Custom Tab")
        )
        self._insert_pos = self._menu.addSeparator()
        self._plugin_actions = dict()
        scene_increment_action = self._menu.addAction(
            translate("sp_plugins_ui", "Save +1")
        )
        scene_increment_action.triggered.connect(scene_increment)
        substance_painter.ui.add_menu(self._menu)

    def remove_menu(self):
        substance_painter.ui.delete_ui_element(self._menu)
        self._menu = None
        self._insert_pos = None


PLUGINS_MENU = None


def start_plugin():
    global PLUGINS_MENU
    PLUGINS_MENU = PluginsMenu()


def close_plugin():
    global PLUGINS_MENU
    PLUGINS_MENU.remove_menu()
    PLUGINS_MENU = None


if __name__ == "__main__":
    start_plugin()
