# ============================================================================
#  DUCK THE DAY 🐣
# ============================================================================
from fasthtml.common import *
import ffmpeg
import tempfile
from pathlib import Path

styles = Link(rel="stylesheet", href="/static/css/output.css", type="text/css")

app, rt = fast_app(
    pico=False,
    surreal=False,
    live=True,
    hdrs=(styles,),
    htmlkw=dict(lang="en", dir="ltr", data_theme="dark"),
    bodykw=dict(cls="min-h-screen bg-base-100")
)

@rt("/")
def get():
    return Div(
        Div(
            H1("Voice Recorder", cls="text-2xl font-bold mb-4"),
            Div(
                Button("🎤 Start Recording", id="startBtn", cls="btn btn-primary mr-2"),
                Button("⏹ Stop Recording", id="stopBtn", cls="btn btn-error", disabled=True),
                cls="mb-4"
            ),
            Audio(id="playback", controls=True, cls="w-full"),
            cls="container mx-auto p-4"
        ),
        Script("""
            let mediaRecorder, audioChunks = [];
            
            // OPFS save function
            async function saveToOPFS(blob) {
                const root = await navigator.storage.getDirectory();
                const fileHandle = await root.getFileHandle(
                    `recording_${Date.now()}.flac`, 
                    {create: true}
                );
                const writable = await fileHandle.createWritable();
                await writable.write(blob);
                await writable.close();
                return fileHandle;
            }

            document.getElementById('startBtn').onclick = async () => {
                const stream = await navigator.mediaDevices.getUserMedia({
                    audio: { sampleRate: 16000, channelCount: 1 }
                });
                
                mediaRecorder = new MediaRecorder(stream);
                audioChunks = [];

                mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
                
                mediaRecorder.onstop = async () => {
                    const webmBlob = new Blob(audioChunks, {type: 'audio/webm'});
                    
                    // Send to Python server for processing
                    const formData = new FormData();
                    formData.append('file', webmBlob, 'recording.webm');
                    
                    const response = await fetch('/process_audio', {
                        method: 'POST',
                        body: formData
                    });
                    
                    // Store FLAC in OPFS
                    const flacBlob = await response.blob();
                    const fileHandle = await saveToOPFS(flacBlob);
                    
                    // Update playback
                    const file = await fileHandle.getFile();
                    document.getElementById('playback').src = URL.createObjectURL(file);
                };

                mediaRecorder.start();
                document.getElementById('stopBtn').disabled = false;
                document.getElementById('startBtn').disabled = true;
            };

            document.getElementById('stopBtn').onclick = () => {
                mediaRecorder.stop();
                document.getElementById('stopBtn').disabled = true;
                document.getElementById('startBtn').disabled = false;
            };
        """),
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