# ============================================================================
#  DUCK THE DAY 🐣
# ============================================================================
from fasthtml.common import *
import ffmpeg
import tempfile
from pathlib import Path
from ft_icon import Icon, Size, Style, IconSpriteMiddleware
from icon_types import IconType

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

@rt("/")
def get():
    return Div(
        Div(
            H1("Voice Recorder", cls="text-2xl font-bold mb-4"),            
            Div(
                Button("🎤 Start Recording", id="startBtn", 
                      cls="btn btn-primary mr-2"),
                Button("⏹ Stop Recording", id="stopBtn", 
                      cls="btn btn-error", disabled=True),
                Label(
                    Input(type="checkbox", id="autoplay", checked=True, cls="toggle toggle-primary"),
                    Span("Auto-play", cls="ml-2"),
                    cls="flex items-center gap-2"
                ),
                cls="mb-4 flex items-center gap-4"
            ),
            Div(
                Table(
                    Thead(Tr(
                        Th("", cls="w-8 radio-col"),
                        Th(
                            Span("Title", cls="mr-2"),
                            Icon.edit(cls="inline-block w-4 h-4"),
                            cls="w-1/3 flex items-center"
                        ),
                        Th("Date", cls="w-1/6"),
                        Th("Time", cls="w-1/6"),
                        Th("Duration", cls="w-1/6 text-right"),
                        Th("Size", cls="w-1/6 text-right"),
                        cls="bg-base-200"
                    )),
                    Tbody(
                        Tr(Td("Loading recordings...", colspan=6, cls="text-center"),
                          id="recordings-list"),
                        cls="[&>tr]:contents"
                    ),
                    cls="table table-fixed w-full"
                ),
                cls="overflow-x-auto bg-base-100 p-4 rounded-box shadow-lg"
            ),
            Audio(id="playback", controls=True, cls="w-full mt-4"),
            cls="container mx-auto p-4"
        ),
        Script(src="/static/js/recorder.js", type="module"),
        cls="min-h-screen bg-base-100"
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