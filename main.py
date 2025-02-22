# ============================================================================
#  DUCK THE DAY 🐣
# ============================================================================
from fasthtml.common import *
import ffmpeg
import tempfile
from pathlib import Path
from ft_icon import Icon, Size, Style, IconSpriteMiddleware
from icon_types import IconType
from dataclasses import dataclass, field
from typing import List, Tuple

Icon: IconType

styles = Link(rel="stylesheet", href="/static/css/output.css", type="text/css")
recorder_script = Script(src="/static/js/recorder.js", type="module")

app, rt = fast_app(
    pico=False,
    surreal=False,
    live=True,
    hdrs=(styles, recorder_script),
    htmlkw=dict(lang="en", dir="ltr", data_theme="dark"),
    bodykw=dict(cls="min-h-screen bg-base-100"),
    middleware=[IconSpriteMiddleware]
)

@dataclass
class DeleteModal:
    def __ft__(self) -> Dialog:
        return Dialog(
            Div(
                H3("Delete Recording", cls="text-lg font-bold"),
                P("Are you sure you want to permanently delete this recording?", cls="py-4"),
                Div(
                    Button("Cancel", id="delete-cancel", cls="btn"),
                    Button("Delete", id="delete-confirm", cls="btn btn-error"),
                    cls="modal-action"
                ),
                cls="modal-box"
            ),
            Form(
                Button("Close", type="submit"),
                method="dialog",
                cls="modal-backdrop"
            ),
            id="delete-modal",
            cls="modal"
        )

@dataclass
class RecordingsTable:
    columns: List[Tuple[str, str]] = field(default_factory=lambda: [
        ("", "w-8 radio-col"),
        ("Title", "w-1/3 flex items-center"),
        ("Date", "w-1/6"),
        ("Time", "w-1/6"),
        ("Duration", "w-1/6 text-right"),
        ("Size", "w-1/6 text-right"),
        ("", "w-12")
    ])
    
    def __ft__(self) -> Table:
        return Table(
            Thead(Tr(*[
                Th(
                    Span(col[0], cls="mr-2") if i == 1 else col[0],
                    Icon.edit(cls="inline-block w-4 h-4") if i == 1 else None,
                    Icon.delete(cls="inline-block w-4 h-4") if i == 6 else None,
                    cls=col[1],
                ) for i, col in enumerate(self.columns)
            ], cls="bg-base-200")),
            Tbody(
                Tr(Td("Loading recordings...", colspan=6, cls="text-center"),
                id="recordings-list"),
                cls="[&>tr]:contents"
            ),
            cls="table table-fixed w-full"
        )

@rt("/")
def get():
    return Div(
        Div(
            HeaderSection(),
            RecordingsSection(),
            Audio(id="playback", controls=True, cls="w-full mt-4"),
            cls="container mx-auto p-4"
        ),
        DeleteModal(),
        cls="min-h-screen bg-base-100"
    )

@dataclass
class HeaderSection:
    def __ft__(self) -> Div:
        return Div(
            H1("Voice Recorder", cls="text-2xl font-bold mb-4"),
            ControlButtons(),
            cls="mb-4 flex items-center gap-4"
        )

@dataclass
class ControlButtons:
    def __ft__(self) -> Div:
        return Div(
            Button("🎤 Start Recording", id="startBtn", cls="btn btn-primary mr-2"),
            Button("⏹ Stop Recording", id="stopBtn", cls="btn btn-error", disabled=True),
            Label(
                Input(type="checkbox", id="autoplay", checked=True, cls="toggle toggle-primary"),
                Span("Auto-play", cls="ml-2"),
                cls="flex items-center gap-2"
            ),
            cls="flex items-center gap-4"
        )

@dataclass
class RecordingsSection:
    def __ft__(self) -> Div:
        return Div(
            Div(
                RecordingsTable(),
                cls="overflow-x-auto bg-base-100 p-4 rounded-box shadow-lg"
            ),
            cls="mb-4"
        )

@rt("/process_audio", methods="POST")
async def process_audio(file: File):
    # Save uploaded webm to temp file
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as webm_temp:
        webm_temp.write(await file.read())
        webm_path = webm_temp.name

    # Process with FFmpeg
    flac_path = Path(webm_path).with_suffix(".flac")
    (
        ffmpeg
        .input(webm_path)
        .output(str(flac_path),
               ar=16000,
               ac=1,
               acodec='flac')
        .overwrite_output()
        .run()
    )
    
    # Return processed FLAC
    return FileResponse(
        flac_path,
        media_type="audio/flac",
        headers={"Content-Disposition": f"attachment; filename={flac_path.name}"}
    )

if __name__ == "__main__":      
    serve(port=5001)