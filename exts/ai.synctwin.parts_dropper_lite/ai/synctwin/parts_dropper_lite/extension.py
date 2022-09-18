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
        return f"({v[0]:.2f} / {v[1]:.2f} / {v[2]:.2f})"
        
    
    def on_startup(self, ext_id):
        self._window = ui.Window("SyncTwin Parts Dropper Lite", width=300, height=500)
        self._dropper = PartDropper()
        
        self._app = omni.kit.app.get_app_interface()

        with self._window.frame:
            with ui.VStack():
                ui.Button("create scene", height=30,
                            clicked_fn=lambda: self.on_create_scene_clicked())
                ui.Button(
                            "select container", 
                            height=30,
                            tooltip="select container USD path...",
                            clicked_fn=lambda: self.select_container()
                        )
                ui.Button(
                            "select part",
                            height=30,
                            tooltip="select part USD path...",
                            clicked_fn=lambda: self.select_part()
                        )                        
                ui.Label("Container:")
                with ui.HStack():
                    self._container_label = ui.Label("-", height=30)                                        
                    self._container_size_label = ui.Label("", height=30)                        

                ui.Label("Part:")
                with ui.HStack():
                    self._part_label = ui.Label("-", height=30)                                    
                    self._part_size_label = ui.Label("", height=30)                        

                ui.Label("Target Count:")                
                
                field = ui.IntField(height=30) 
                self._targetCountModel = field.model
                
                with ui.HStack():
                    ui.Label("Parts Dropped:")
                    self._parts_dropped_label = ui.Label("0")
                self._parts_button = ui.Button("drop parts", 
                    clicked_fn=lambda: self.on_parts_button_clicked(), enabled=False, height=50)

        # timeline event subscription (play/stop etc)
        self._timeline = omni.timeline.get_timeline_interface()
        timeline_stream = self._timeline.get_timeline_event_stream()
        self._timeline_event_sub = timeline_stream.create_subscription_to_pop(self._on_timeline_event)                

         # setup app update subscription for frame events
        self._app = omni.kit.app.get_app_interface()
        self._app_update_sub = self._app.get_update_event_stream().create_subscription_to_pop(
            self._on_app_update_event, name="part_dropper._on_app_update_event"
        )   
        # setup open close subscription 
        self._usd_context = omni.usd.get_context()
        self._sub_stage_event = self._usd_context.get_stage_event_stream().create_subscription_to_pop(
                self._on_stage_event
            )     
        self.set_dropper_stage_from_context()
        self.refresh()        
                    
    def on_shutdown(self):
        print("[ai.synctwin.parts_dropper_lite] MyExtension shutdown")
        self._timeline_event_sub = None


    def refresh(self):
        if self._dropper.has_container():
            self._container_label.text = os.path.split(self._dropper.container_path)[1]
            self._container_size_label.text = self._vec_to_str(self._dropper.container_size)
        else:
            self._container_label.text = "-" 
            self._container_size_label.text = ""

        if self._dropper.has_part():
            self._part_label.text = os.path.split(self._dropper.part_path)[1]
            self._part_size_label.text = self._vec_to_str(self._dropper.part_size)
        else:
            self._part_label.text = "-" 
            self._part_size_label.text = ""


        self._parts_button.enabled = self._dropper.has_part() and self._dropper.has_container()
        partsbut_text = "drop"
        if self._dropper.is_dropping:
            partsbut_text = "stop"
        self._parts_button.text = partsbut_text
        self._targetCountModel.set_value(self._dropper.target_part_count)
        self.refresh_parts_label()
        

    def on_container_file_selected(self, dialog, dirname: str, filename: str):        
        print(f"selected {filename}")
        self._dropper.set_container_usd(f"{dirname}/{filename}")
        dialog.hide()
        self.refresh()

    
    
    def select_container(self):
        dialog = FilePickerDialog(
            "select container geometry",
            allow_multi_selection=False,
            apply_button_label="select file",
            click_apply_handler=lambda filename, dirname: self.on_container_file_selected(dialog, dirname, filename),
            file_extension_options=DEFAULT_FILE_EXTENSION_TYPES
        )
        dialog.show()


        
       

    def on_part_file_selected(self, dialog, dirname: str, filename: str):        
        print(f"selected {filename}")        
        self._dropper.set_part_usd(f"{dirname}/{filename}")        
        dialog.hide()    
        self.refresh()

    def select_part(self):
        dialog = FilePickerDialog(
            "select part geometry",
            allow_multi_selection=False,
            apply_button_label="select file",
            click_apply_handler=lambda filename, dirname: self.on_part_file_selected(dialog, dirname, filename),
            file_extension_options = DEFAULT_FILE_EXTENSION_TYPES
        )
        dialog.show()
    
    
    def on_create_scene_clicked(self):
        self._usd_context.new_stage()
        self._dropper.create_ground_plane()

    def on_parts_button_clicked(self):
        if self._dropper.is_dropping:
            self._timeline.stop()
            self._dropper.stop_dropping()
        else:
            self._timeline.play()
            self._dropper.set_target_count(self._targetCountModel.get_value_as_int())
            self._dropper.start_dropping()
    
    def refresh_parts_label(self):
        self._parts_dropped_label.text = str(self._dropper.part_count)

    def _on_timeline_event(self, e):
        """ Event handler for timeline events"""
        #print("timeline event")
        if e.type == int(omni.timeline.TimelineEventType.PLAY):
            print("PLAY")
        elif e.type == int(omni.timeline.TimelineEventType.STOP):
            self._dropper.clear()
        #elif e.type == int(omni.timeline.TimelineEventType.FRAME):


    def _on_app_update_event(self, evt):
        """ Event handler app update events occuring every frame"""        
        result = self._dropper.update(self._app.get_time_since_start_ms())
        if result==PartDropper.UpdateResult.PART_DROPPED:
            self.refresh_parts_label()
        elif result == PartDropper.UpdateResult.TARGET_PARTS_REACHED:
            self.refresh()
        elif result == PartDropper.UpdateResult.PART_MISSED:
            self.refresh()
        

    def clear(self):
        self._dropper.clear()
        self.refresh()

    def set_dropper_stage_from_context(self):
        self._dropper.set_stage(self._usd_context.get_stage())

    def _on_stage_event(self, event):
        
        if event.type == int(omni.usd.StageEventType.SELECTION_CHANGED):
            # not used 
            pass

        elif event.type == int(omni.usd.StageEventType.CLOSED):
            print("CLOSED.")
            self.clear()

        elif event.type == int(omni.usd.StageEventType.OPENED):
            print("OPENED.")
            self.set_dropper_stage_from_context()
        else:
            print(f"STATE  {event.type}")
