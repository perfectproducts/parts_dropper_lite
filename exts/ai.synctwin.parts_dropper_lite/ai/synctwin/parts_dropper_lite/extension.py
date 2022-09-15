import omni.ext
from omni.kit.window.file_exporter.extension import DEFAULT_FILE_EXTENSION_TYPES
import omni.ui as ui
import omni.usd as usd 
from omni.kit.window.filepicker import FilePickerDialog
from omni.kit.widget.filebrowser import FileBrowserItem
from .part_dropper import PartDropper
import omni.physx
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
        self._container_button.enabled = self._dropper.can_create_container()
        if self._dropper.can_create_container():
            self.create_container()
        

    def on_container_file_selected(self, dialog, dirname: str, filename: str):        
        print(f"selected {filename}")
        self.set_container_usd(f"{dirname}/{filename}")
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


    def set_part_usd(self, path):
        self._dropper.set_part_usd(path)        
        self._part_label.text = os.path.split(path)[1]
        self._part_size_label.text = f"Size: {self._vec_to_str(self._dropper.part_size)}"
        self._parts_button.enabled = self._dropper.can_create_parts()
        if self._dropper.can_create_parts():
            self.create_parts()
       

    def on_part_file_selected(self, dialog, dirname: str, filename: str):        
        print(f"selected {filename}")
        self.set_part_usd(f"{dirname}/{filename}")

        dialog.hide()    

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
        self._window = ui.Window("SyncTwin Parts Dropper Lite", width=300, height=400)
        self._dropper = PartDropper()
        self._physx = omni.physx.get_physx_interface()
        self._app = omni.kit.app.get_app_interface()
        self._drop_interval_ms = 500
        #self._physx_cooking = omni.physx.get_physx_cooking_interface()
        #self._physx_authoring = omni.physx.get_physx_authoring_interface()

        self._is_dropping = False 
        with self._window.frame:
            with ui.VStack():
                ui.Button("create scene", clicked_fn=lambda: self.create_scene())
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
                self._container_button = ui.Button("create container", clicked_fn=lambda: self.create_container(), enabled=False)

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
                self._parts_button = ui.Button("create parts", clicked_fn=lambda: self.create_parts(), enabled=False)

        # timeline 
        self._timeline = omni.timeline.get_timeline_interface()
        timeline_stream = self._timeline.get_timeline_event_stream()
        self._timeline_event_sub = timeline_stream.create_subscription_to_pop(self._on_timeline_event)                

         # setup app update subscription for frame events
        self._app = omni.kit.app.get_app_interface()
        self._app_update_sub = self._app.get_update_event_stream().create_subscription_to_pop(
            self._on_app_update_event, name="part_dropper._on_app_update_event"
        )                
                    
    def on_shutdown(self):
        print("[ai.synctwin.parts_dropper_lite] MyExtension shutdown")
        self._timeline_event_sub = None

    def create_scene(self):
        context = omni.usd.get_context()
        context.new_stage()
        stage = context.get_stage()
        self._dropper.create_ground_plane(stage)

    def create_container(self):
        context = omni.usd.get_context()
        stage = context.get_stage()
        self._dropper.create_container(stage)

    def create_parts(self):
        if self._is_dropping:
            self._is_dropping = False
            self._timeline.stop()
            return 
        context = omni.usd.get_context()
        stage = context.get_stage()
        self._last_drop_time_ms = self._app.get_time_since_start_ms()
        self._dropper.add_part(stage)
        print("create parts")
        self._timeline.play()
        self._is_dropping= True          

        
    def _on_timeline_event(self, e):
        """ Event handler for timeline events"""
        print("timeline event")
        if e.type == int(omni.timeline.TimelineEventType.PLAY):
            print("PLAY")

    def _on_app_update_event(self, evt):
        """ Event handler app update events occuring every frame"""
        #print("app event")
        if not self._is_dropping:
            return 
        now_ms = self._app.get_time_since_start_ms()
        elapsed_ms = now_ms - self._last_drop_time_ms
        #print("elapsed: {elapsed_s}")
        if elapsed_ms > self._drop_interval_ms:
            context = omni.usd.get_context()
            stage = context.get_stage()
            self._dropper.add_part(stage)
            self._last_drop_time_s = now_ms
    