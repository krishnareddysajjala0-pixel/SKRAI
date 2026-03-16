from fastapi import FastAPI, Request, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import asyncio
import uuid
from utility.script.script_generator import generate_script
from utility.audio.audio_generator import generate_audio
from utility.captions.timed_captions_generator import generate_timed_captions
from utility.video.background_video_generator import generate_video_url
from utility.render.render_engine import get_output_media
from utility.video.video_search_query_generator import getVideoSearchQueriesTimed, merge_empty_intervals
from utility.config import get_config

app = FastAPI()

# Setup templates
templates = Jinja2Templates(directory="templates")

# In-memory status tracking (simplified for demo)
jobs = {}

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "jobs": jobs})

async def run_video_generation(job_id: str, topic: str):
    try:
        jobs[job_id]["status"] = "Generating Script..."
        SAMPLE_FILE_NAME = f"{job_id}_audio.wav"
        VIDEO_SERVER = "pexel"
        
        config = get_config()
        orientation_landscape = config.get_video_orientation()

        # 1. Script
        script = generate_script(topic)
        jobs[job_id]["status"] = "Generating Audio..."
        
        # 2. Audio
        await generate_audio(script, SAMPLE_FILE_NAME)
        jobs[job_id]["status"] = "Generating Captions..."
        
        # 3. Captions
        timed_captions = generate_timed_captions(SAMPLE_FILE_NAME)
        
        # 4. Search Terms
        search_terms = getVideoSearchQueriesTimed(script, timed_captions)
        jobs[job_id]["status"] = "Fetching B-Roll..."
        
        # 5. Video URLs
        background_video_urls = None
        if search_terms is not None:
            background_video_urls = generate_video_url(search_terms, VIDEO_SERVER, orientation_landscape=orientation_landscape)
            background_video_urls = merge_empty_intervals(background_video_urls)
        
        # 6. Render
        jobs[job_id]["status"] = "Rendering Video..."
        if background_video_urls is not None:
            video_output = get_output_media(SAMPLE_FILE_NAME, timed_captions, background_video_urls, VIDEO_SERVER)
            # Rename output to a stable name for the job
            final_video = f"{job_id}_video.mp4"
            if os.path.exists("rendered_video.mp4"):
                os.rename("rendered_video.mp4", final_video)
            
            jobs[job_id]["status"] = "Completed"
            jobs[job_id]["video_url"] = f"/download/{final_video}"
        else:
            jobs[job_id]["status"] = "Failed (No background video)"
            
    except Exception as e:
        jobs[job_id]["status"] = f"Error: {str(e)}"

@app.post("/generate")
async def generate(background_tasks: BackgroundTasks, topic: str = Form(...)):
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {"topic": topic, "status": "Queued", "video_url": None}
    background_tasks.add_task(run_video_generation, job_id, topic)
    return {"job_id": job_id, "message": "Generation started in background"}

@app.get("/status/{job_id}")
async def get_status(job_id: str):
    return jobs.get(job_id, {"status": "Not Found"})

@app.get("/download/{filename}")
async def download(filename: str):
    if os.path.exists(filename):
        return FileResponse(filename)
    return {"error": "File not found"}

if __name__ == "__main__":
    import uvicorn
    # Use PORT environment variable for Render
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
