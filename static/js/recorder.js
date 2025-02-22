import Dexie from 'https://unpkg.com/dexie@4.0.11/dist/dexie.mjs';

const db = new Dexie("VoiceRecorderDB");
db.version(1).stores({
    recordings: `
        ++name,
        title,
        date,
        time,
        size,
        duration
    `
});

class RecordingManager {
    constructor() {
        this.audioElement = document.getElementById('playback');
        this.autoplayCheckbox = document.getElementById('autoplay');
        this.tbody = document.getElementById('recordings-list');
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.db = db;
        this.initTable();
        this.bindEvents();

        // Create template without dynamic values
        this.rowTemplate = document.createElement('template');
        this.rowTemplate.innerHTML = `
            <tr class="hover">
                <td class="w-8 p-2">
                    <input 
                        type="radio" 
                        name="selected-recording" 
                        class="radio radio-primary hidden"
                    >
                </td>
                <td class="w-1/3 p-2">
                    <div class="flex items-center gap-2 group/title">
                        <span class="title-display"></span>
                        <button class="edit-btn btn btn-circle btn-xs opacity-0 group-hover/title:opacity-100">
                            <svg class="w-4 h-4" data-icon>
                                <use href="#icons.edit"/>
                            </svg>
                        </button>
                    </div>
                    <input 
                        type="text" 
                        class="editable-title input input-ghost w-full px-2 py-1 hidden"
                    >
                </td>
                <td class="w-1/6 p-2"></td>
                <td class="w-1/6 p-2"></td>
                <td class="w-1/6 p-2 text-right"></td>
                <td class="w-1/6 p-2 text-right"></td>
                <td class="w-12 p-2">
                    <button class="delete-btn btn btn-ghost btn-xs opacity-60 hover:opacity-100">
                        <svg 
                            class="inline-block w-4 h-4 text-error" 
                            data-icon
                        >
                            <use href="#icons.delete"/>
                        </svg>
                    </button>
                </td>
            </tr>
        `;

        // Track user interaction
        this.userInteracted = false;
        document.addEventListener('click', () => {
            this.userInteracted = true;
        }, { once: true });

        this.deleteModal = document.getElementById('delete-modal');
        this.deleteConfirm = document.getElementById('delete-confirm');
        this.deleteCancel = document.getElementById('delete-cancel');
        this.recordingToDelete = null;

        this.deleteConfirm.addEventListener('click', async (e) => {
            e.preventDefault();
            if (this.recordingToDelete) {
                await this.deleteRecording(this.recordingToDelete);
                this.deleteModal.close();
                this.recordingToDelete = null;
            }
        });

        this.deleteCancel.addEventListener('click', (e) => {
            e.preventDefault();
            this.deleteModal.close();
            this.recordingToDelete = null;
        });
    }

    async initTable() {
        const root = await navigator.storage.getDirectory();
        this.updateTable(await this.getRecordings(root));
    }

    async getRecordings(root) {
        const recordings = [];
        for await (const [name, handle] of root.entries()) {
            if (name.startsWith('recording_')) {
                const file = await handle.getFile();
                const timestamp = parseInt(name.split('_')[1]);
                const date = new Date(timestamp);
                
                // Get metadata from Dexie
                const meta = await this.db.recordings.get(name) || {};
                
                recordings.push({
                    name,
                    handle,
                    date: meta.date || date.toLocaleDateString(),
                    time: meta.time || date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}),
                    title: meta.title || `Recording at ${date.toLocaleTimeString()}`,
                    size: file.size,
                    duration: meta.duration || Math.round(file.size / 16000 / 2)
                });
            }
        }
        return recordings.sort((a, b) => 
            new Date(b.date + ' ' + b.time) - new Date(a.date + ' ' + a.time)
        );
    }

    updateTable(recordings) {
        this.tbody.innerHTML = '';
        
        recordings.forEach(rec => {
            const row = this.rowTemplate.content.cloneNode(true);
            const tr = row.querySelector('tr');
            tr.dataset.name = rec.name;
            
            const cells = tr.querySelectorAll('td');
            
            // Radio
            cells[0].querySelector('input').checked = 
                this.audioElement.src.includes(rec.name);
            
            // Title (editable)
            const titleDisplay = cells[1].querySelector('.title-display');
            const editButton = cells[1].querySelector('.edit-btn');
            const titleInput = cells[1].querySelector('.editable-title');

            titleDisplay.textContent = rec.title;
            titleInput.value = rec.title;

            editButton.addEventListener('click', () => {
                titleDisplay.classList.add('hidden');
                editButton.classList.add('hidden');
                titleInput.classList.remove('hidden');
                titleInput.focus();
            });

            titleInput.addEventListener('blur', () => {
                titleDisplay.textContent = titleInput.value;
                titleDisplay.classList.remove('hidden');
                editButton.classList.remove('hidden');
                titleInput.classList.add('hidden');
                this.saveRecordingTitle(rec.name, titleInput.value);
            });
            
            // Date
            cells[2].textContent = rec.date;
            
            // Time
            cells[3].textContent = rec.time;
            
            // Duration
            cells[4].textContent = `${rec.duration}s`;
            
            // Size
            cells[5].textContent = `${(rec.size/1024).toFixed(1)}KB`;

            // Click handler
            tr.addEventListener('click', (e) => {
                // Get all radio inputs first
                const radios = document.querySelectorAll('input[name="selected-recording"]');
                
                // Uncheck all and remove highlights
                radios.forEach(radio => {
                    radio.checked = false;
                    radio.closest('tr').classList.remove('bg-primary/20');
                });
                
                // Check current and add highlight
                const currentRadio = tr.querySelector('input');
                currentRadio.checked = true;
                tr.classList.add('bg-primary/20');
                
                this.loadAudio(rec.name);
            });

            const deleteButton = cells[6].querySelector('.delete-btn');
            deleteButton.addEventListener('click', (e) => {
                e.stopPropagation();
                this.recordingToDelete = rec.name;
                this.deleteModal.showModal();
            });

            this.tbody.appendChild(row);
        });

        // Auto-select newest recording
        if (recordings.length > 0 && !this.audioElement.src) {
            const firstRow = this.tbody.firstElementChild;
            firstRow.classList.add('bg-primary/20');
            firstRow.querySelector('input').checked = true;
            this.loadAudio(recordings[0].name);
        }
    }

    async saveToOPFS(blob) {
        const fileName = `recording_${Date.now()}.flac`;
        try {
            const root = await navigator.storage.getDirectory();
            const fileHandle = await root.getFileHandle(fileName, { create: true });
            const writable = await fileHandle.createWritable();
            await writable.write(blob);
            await writable.close();

            const file = await fileHandle.getFile();
            const rec = {
                name: fileName,
                size: file.size,
                duration: Math.round(file.size / 16000 / 2),
                date: new Date().toLocaleDateString(),
                time: new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}),
                title: `Recording at ${new Date().toLocaleTimeString()}`
            };
            
            await this.saveRecordingMetadata(rec);
            
            // Refresh and select new recording
            await this.initTable();
            this.selectRecording(fileName);
            return rec;
        } catch (error) {
            console.error('Error saving to OPFS:', error);
            throw error;
        }
    }

    selectRecording(name) {
        const row = Array.from(this.tbody.children).find(tr => 
            tr.dataset.name === name
        );
        if (row) {
            row.classList.add('bg-primary/20');
            row.querySelector('input').checked = true;
            this.loadAudio(name);
        }
    }

    bindEvents() {
        const startBtn = document.getElementById('startBtn');
        const stopBtn = document.getElementById('stopBtn');

        startBtn.addEventListener('click', async () => {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: { sampleRate: 16000, channelCount: 1 }
            });
            
            this.mediaRecorder = new MediaRecorder(stream);
            this.audioChunks = [];

            this.mediaRecorder.ondataavailable = e => this.audioChunks.push(e.data);
            
            this.mediaRecorder.onstop = async () => {
                const webmBlob = new Blob(this.audioChunks, {type: 'audio/webm'});
                const formData = new FormData();
                formData.append('file', webmBlob, 'recording.webm');
                
                const response = await fetch('/process_audio', {
                    method: 'POST',
                    body: formData
                });
                
                const flacBlob = await response.blob();
                await this.saveToOPFS(flacBlob);
            };

            this.mediaRecorder.start();
            stopBtn.disabled = false;
            startBtn.disabled = true;
        });

        stopBtn.addEventListener('click', () => {
            this.mediaRecorder.stop();
            stopBtn.disabled = true;
            startBtn.disabled = false;
        });
    }

    async loadAudio(name) {
        const root = await navigator.storage.getDirectory();
        const handle = await root.getFileHandle(name);
        const file = await handle.getFile();
        this.audioElement.src = URL.createObjectURL(file);
        
        // Only autoplay if user has interacted before
        if (this.autoplayCheckbox.checked && this.userInteracted) {
            await this.audioElement.play();
        }
    }

    async saveRecordingTitle(name, newTitle) {
        await this.db.recordings.update(name, {
            title: newTitle,
            updated: new Date().toISOString()
        });
    }

    async saveRecordingMetadata(rec) {
        await this.db.recordings.put({
            name: rec.name,
            title: rec.title,
            date: rec.date,
            time: rec.time,
            size: rec.size,
            duration: rec.duration,
            created: new Date().toISOString()
        });
    }

    async deleteRecording(filename) {
        try {            
            const root = await navigator.storage.getDirectory();
            
            // Delete file from OPFS
            try {
                await root.removeEntry(filename);
            } catch (error) {
                console.log('File not found in OPFS, continuing');
            }

            // Delete metadata from Dexie
            await this.db.recordings.where('name').equals(filename).delete();

            // Remove UI row
            const row = document.querySelector(`tr[data-name="${filename}"]`);
            if (row) row.remove();

            console.log('Successfully deleted:', filename);
            
        } catch (error) {
            console.error('Delete error:', error);
            alert('Failed to delete recording');
        }
    }
}

document.addEventListener('DOMContentLoaded', () => new RecordingManager());