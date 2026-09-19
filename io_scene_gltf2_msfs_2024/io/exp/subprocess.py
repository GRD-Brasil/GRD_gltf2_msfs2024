import os
import threading
import queue
import subprocess
from datetime import datetime
import secrets
from pathlib import Path

import bpy

import addon_utils
from . import pre_export
from . import progress_bar
from . import constants
from ..com import msfs_logs
from . import subprocess_cancel

MSFS2024_LOGGER : msfs_logs.Logger


class SubProcessReport:
    """
    Functions used to communicate from a subprocess to blender main instance.
    """

    tag_progress = "[SUBPROCESS][PROGRESS]"
    tag_progress_text = "[SUBPROCESS][PROGRESS_TEXT]"
    tag_other_logs = "[SUBPROCESS][OTHER_LOGS]"

    @staticmethod
    def report_progress(progress: int):
        print(f"\n{SubProcessReport.tag_progress} {progress}", flush=True)

    @staticmethod
    def report_progress_text(text: str = ""):
        print(f"\n{SubProcessReport.tag_progress_text} {text}", flush=True)

    @staticmethod
    def get_report_text(text: str):
        result = text.split(" ",1)
        if len(result)>1:
            return result[1]
        return ""


class MSFS2024_OT_SubProcessExport(bpy.types.Operator):
    """
    Export in another Blender process:
    Save a temp copy of blender scene in same folder.
    Open the scene in a subprocess and call multi_export_gltf operator.
    Temp copy of blender scene is deleted at the end of process. 
    """

    bl_idname = "msfs2024.subprocess_export"
    bl_label = "Export MSFS2024 GLTFs in another process"
    bl_options = {"INTERNAL"}

    export_mode: bpy.props.EnumProperty(
        items=constants.EXPORT_MODES_ENUM_ITEMS
    )  # type: ignore

    _subprocess : None | subprocess.Popen = None
    _queue: None | queue.SimpleQueue = None

    _progress: int = -1
    _progress_text: str = "Exporting..."
    _debug: bool = False
    _profiling: bool = False
    _timer: bpy.types.Timer | None = None
    _thread_finished: bool = False
    _thread: threading.Thread | None = None

    start_time: datetime | None = None

    blend_file_path: str | None = None

    def thread_target(self, scene_path: str, blender_exe_path: str, debug: bool = False):

        addon_name = "io_scene_gltf2_msfs_2024"
        user_script_folder = ""
        # Find user script folder containing msfs addons
        for mod in addon_utils.modules():
            if not mod.__name__ == addon_name:
                continue
            for script_path in bpy.utils.script_paths():
                script_path = Path(script_path)
                if Path(mod.__file__).is_relative_to(script_path):
                    user_script_folder = script_path.as_posix()
                    break

        env = os.environ.copy()
        env["BLENDER_USER_SCRIPTS"] = user_script_folder

        debug_script = ""
        if self._debug:
            # Wait to attach to vscode
            debug_script = (
                "\tbpy.ops.preferences.addon_enable(module='debugpy_launcher')\n" 
                "\tbpy.ops.debug.start_debugpy(wait_for_client=True)\n" #debug in process
                "\tprint('Waiting for attach')\n"
            )

        python_script = (
            "try: \n"
            "\timport bpy\n"
            "\timport traceback\n"
            "\timport os\n"
            # Addon is already loaded with --addons arg, but its not marked as enabled...
            # gltf hooks are not loaded if addon is not mark as enabled.
            f"{debug_script}"
            f"\tbpy.ops.preferences.addon_enable(module='{addon_name}')\n"
            f"\tbpy.ops.msfs2024.multi_export_gltf(export_mode='{self.export_mode}', called_in_subprocess=True, profiling={self._profiling})\n"
            "except:\n"
            "\texc = traceback.format_exc()\n"
            "\tprint(exc)\n"
            "finally:\n"
            "\tos._exit(1)\n" # force exit for old blender version 
            
        )

        self._queue.put((SubProcessReport.tag_progress,0))
        # Start a new blender process with only addon io_scene_gltf2_msfs_2024 enabled
        args = [
                blender_exe_path,
                scene_path,
                "--background",
                "--factory-startup",
                "--addons", addon_name,
                "--disable-autoexec",
                "-noaudio",
                "--python-expr",python_script,        
            ]
        if bpy.app.version >= (4, 2, 0):
            args.append("--offline-mode")
        if debug:
            args.append("--debug")
        self._subprocess = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env
        )

        logs = []
        try:
            # Read output from subprocess
            for out in iter(self._subprocess.stdout.readline, ''):
                if out.startswith(SubProcessReport.tag_progress):

                    progress = SubProcessReport.get_report_text(out)
                    self._queue.put((SubProcessReport.tag_progress,int(float(progress))))
                elif out.startswith(SubProcessReport.tag_progress_text):
                    progress_text = SubProcessReport.get_report_text(out)
                    self._queue.put((SubProcessReport.tag_progress_text,progress_text))
                elif out.strip():
                    logs.append(out)

            self._queue.put((SubProcessReport.tag_other_logs,logs))
            # Make sure progress is 100%
            self._queue.put((SubProcessReport.tag_progress,100))
        except:
            pass
        finally:
            self._thread_finished = True
            self._subprocess.stdout.close()  
            self._subprocess.kill()
            self._subprocess = None

    def request_cancel(self, context: bpy.types.Context):
        if self._subprocess:
            subprocess_cancel.send_cancel_request(self._subprocess)

    # Event handler
    def modal(self, context: bpy.types.Context, event: bpy.types.Event):

        if not event.type == "TIMER":
            return {"PASS_THROUGH"}

        global MSFS2024_LOGGER
        # Safely get results from thread queue
        while True:
            try:
                msg = self._queue.get_nowait()
            except queue.Empty:
                break

            tag = None
            value = None
            if isinstance(msg, tuple):  # (progress, text)
                tag, value = msg
            if tag == SubProcessReport.tag_progress_text :
                self._progress_text = value
            elif tag == SubProcessReport.tag_progress:
                self._progress = value 
            elif tag == SubProcessReport.tag_other_logs:
                MSFS2024_LOGGER.logs_from_strings(value)
                for _ in value:
                    print(_, flush=True)

        # Only set when changed in order to prevent ui stuttering
        if bpy.context.window_manager.msfs_progress_bar_text != self._progress_text:
            bpy.context.window_manager.msfs_progress_bar_text = self._progress_text
        if bpy.context.window_manager.msfs_progress_bar != self._progress:
            bpy.context.window_manager.msfs_progress_bar = self._progress

        # Check if user requested export cancel
        if context.window_manager.cancel_export_requested:
            self.request_cancel(context)
        # check if thread is alive or if _progress == 100, just to be sure
        # on blender 3.6 and inferior thread is always alive.. even when operation is done
        if not self._thread.is_alive() or self._thread_finished:
            self.stop(context)

            msfs_logs.process_logger_report(self, MSFS2024_LOGGER)
            # Force progress bar update, shouldn't be necessary but it seems to fail sometimes
            progress_bar.redraw_view3d(bpy.context)
            self._set_msfs_subprocess_exporting(False)
            context.window_manager.cancel_export_requested = False

            return {"FINISHED"}

        return {"PASS_THROUGH"}

    def create_blender_file_copy(self, context: bpy.types.Context) -> None | str:
        """Save a temporary copy of the blend file and store the path.
        Make sure the path doesn't exist first.
        All Export will be done using this copy so the user can continue working in this session.
        """

        current_scene = bpy.path.abspath(bpy.data.filepath)
        if not current_scene:
            self.report({"ERROR"}, "Save scene before export")
            return None
        blend_name = secrets.token_hex(6)
        directory = os.path.dirname(current_scene)
        blend_file = os.path.join(directory, blend_name)
        blend_file += ".blend"

        scene_preview = context.preferences.filepaths.file_preview_type

        while os.path.exists(blend_file):
            blend_name = secrets.token_hex(6)
            blend_file = os.path.join(directory, blend_name)
            blend_file += ".blend"

        print(f"Create blend file copy {blend_file}")
        failed = False
        try:
            # Disable file preview for faster save
            # File Preview enabled do a render, which can take some time when
            # viewport is in material or render mode
            context.preferences.filepaths.file_preview_type = "NONE"
            bpy.ops.wm.save_as_mainfile(
                filepath=blend_file, copy=True, compress=False, relative_remap=False
            )
            if not os.path.exists(blend_file):
                self.report({"ERROR"}, "Blend file copy failed")
                failed = True
        except RuntimeError:

            self.report({"ERROR"}, "Blend file copy failed")
            failed = True

        # Restore original save settings
        context.preferences.filepaths.file_preview_type = scene_preview

        if failed:
            return None
        return blend_file

    def _set_msfs_subprocess_exporting(self, state: bool):
        bpy.context.window_manager.msfs_subprocess_exporting = state

    def execute(self, context: bpy.types.Context):

        context.window_manager.cancel_export_requested = False

        global MSFS2024_LOGGER
        MSFS2024_LOGGER = msfs_logs.get_logger()
        MSFS2024_LOGGER.clear_logs()

        if not pre_export.pre_export_check(self.export_mode, self):
            return {"CANCELLED"}
        
        self.blend_file_path = self.create_blender_file_copy(context)
        if not self.blend_file_path:
            return {"CANCELLED"}

        if self._progress != -1:
            self.report({"INFO"}, "Export already in progress!")
            return {"CANCELLED"}

        self.start_time = datetime.now()
        context.window_manager.msfs_progress_bar = 0
        context.window_manager.msfs_progress_bar_text = "Starting Export..."

        self._progress = 0

        # Create a thread which will launch a background instance of blender running a script that does all the work.
        self._queue = queue.SimpleQueue()
        blend_exec = bpy.path.abspath(bpy.app.binary_path)
        self._thread = threading.Thread(
            target=self.thread_target, 
            args=(self.blend_file_path, blend_exec, self._debug), 
            daemon=True
        )

        # Periodically check if the export has finished
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.5, window=context.window)
        wm.modal_handler_add(self)
        self._set_msfs_subprocess_exporting(True)
        self._thread.start()

        return {"RUNNING_MODAL"}

    def stop(self, context: bpy.types.Context):

        if self._timer:
            wm = context.window_manager
            wm.event_timer_remove(self._timer)
            self._timer = None

        if self.blend_file_path and os.path.exists(self.blend_file_path):

            try:
                os.remove(self.blend_file_path)
            except OSError as err:
                print("Temporary file removal failed")
        try:
            if self._thread:
                # Timeout at 0 for blender 3.6 and inferior
                self._thread.join(timeout=0)
        except:
            pass

        context.window_manager.msfs_progress_bar = -1


def draw_cancel_button(context: bpy.types.Context, layout: bpy.types.UILayout):
    row = layout.row(align=True)
    row.alert = True
    text = "Cancel Export"
    if context.window_manager.cancel_export_requested:
        text = "Cancelling ..."
        row.enabled = False
    row.operator(MSFS2024_OT_CancelSubProcessExport.bl_idname, text=text, icon="CANCEL")


class MSFS2024_OT_CancelSubProcessExport(bpy.types.Operator):
    bl_idname = "msfs2024.cancel_subprocess_export"
    bl_label = "Cancel SubProcess export"
    bl_options = {"INTERNAL"}

    def execute(self, context: bpy.types.Context):
        context.window_manager.cancel_export_requested = True
        return {"CANCELLED"}

def is_msfs_subprocess_exporting() -> bool:
    return bpy.context.window_manager.msfs_subprocess_exporting


def register():
    bpy.types.WindowManager.msfs_subprocess_exporting = bpy.props.BoolProperty(  # type: ignore
        name="MSFS Export",
        description="Indicates whether a MSFS subprocess export is currently in progress",
        default=False,
    )

    bpy.types.WindowManager.cancel_export_requested = bpy.props.BoolProperty(  # type: ignore
        default=False, description="Export cancel flag"
    )


def unregister():
    try:
        del bpy.types.WindowManager.msfs_subprocess_exporting  # type: ignore
        del bpy.types.WindowManager.cancel_export_requested  # type: ignore
    except:
        pass
