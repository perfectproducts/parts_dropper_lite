import omni.ext
from omni.kit.window.file_exporter.extension import DEFAULT_FILE_EXTENSION_TYPES
import omni.ui as ui
import omni.usd as usd 
from omni.kit.window.filepicker import FilePickerDialog
from omni.kit.widget.filebrowser import FileBrowserItem
from .part_dropper import PartDropper
import os 

# Any class derived from `omni.ext.IExt` in top level module (defined in `python.modules` of `extension.toml`) will be
# instantiated when extension gets enabled and `on_startup(ext_id)` will be called. Later when extension gets disabled
# on_shutdown() is called.

class PartsDropperLite(omni.ext.IExt):
    DEFAULT_FILE_EXTENSION_TYPES = [
    ("*.usd*", usd.readable_usd_file_exts_str()),
    ("*", "All files"),
    ]

    def _vec_to_str(self, v):
        return f"x={v[0]:.2f} y={v[1]:.2f} z={v[2]:.2f}"

    def set_container_usd(self, path):
        self._dropper.set_container_usd(path)
        self._container_label.text = os.path.split(path)[1]
        self._container_size_label.text = f"Size: {self._vec_to_str(self._dropper.container_size)}"

    def on_container_file_selected(self, dialog, dirname: str, filename: str):        
        print(f"selected {filename}")
        self.set_container_usd(f"{dirname}/{filename}")
        dialog.hide()

    def on_part_file_selected(self, dialog, dirname: str, filename: str):        
        print(f"selected {filename}")
        self._dropper.set_part_usd(f"{dirname}/{filename}")

        dialog.hide()
    
    def select_container(self):
        dialog = FilePickerDialog(
            "select container geometry",
            allow_multi_selection=False,
            apply_button_label="select file",
            click_apply_handler=lambda filename, dirname: self.on_container_file_selected(dialog, dirname, filename),
            file_extension_options=DEFAULT_FILE_EXTENSION_TYPES
        )
        dialog.show()
        
    def select_part(self):
        dialog = FilePickerDialog(
            "select part geometry",
            allow_multi_selection=False,
            apply_button_label="select file",
            click_apply_handler=lambda filename, dirname: self.on_part_file_selected(dialog, dirname, filename),
            file_extension_options = DEFAULT_FILE_EXTENSION_TYPES
        )
        dialog.show()
    
    def on_startup(self, ext_id):
        self._window = ui.Window("SyncTwin Parts Dropper Lite", width=300, height=300)
        self._dropper = PartDropper()
        with self._window.frame:
            with ui.VStack():
                ui.Label("Container:")
                with ui.HStack():                    
                    self._container_label = ui.Label("[select container]", height=30)                    
                    ui.Button(
                            "...", 
                            height=30,
                            width=30,
                            tooltip="select container USD...",
                            clicked_fn=lambda: self.select_container()
                        )
                self._container_size_label = ui.Label("[container size]", height=30)                        
                ui.Label("Part:")
                with ui.HStack():                    
                    self._part_label = ui.Label("[select part]", height=30)
                    
                    ui.Button(
                            "...",
                            height=30,
                            width=30,
                            tooltip="select part USD...",
                            clicked_fn=lambda: self.select_part()
                        )                        
                self._part_size_label = ui.Label("[part size]", height=30)                        
                ui.Label("Count:")
                self._countModel = ui.IntField().model
                self._countModel.set_value(10)

                

                ui.Button("create scene", clicked_fn=lambda: self.create_scene())
    
    def on_shutdown(self):
        print("[ai.synctwin.parts_dropper_lite] MyExtension shutdown")

    def create_scene(self):
        context = omni.usd.get_context()
        context.new_stage()
        stage = context.get_stage()
        self._dropper.create_ground_plane(stage)
