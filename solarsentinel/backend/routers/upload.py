from fastapi import APIRouter, File, UploadFile
import uuid
import os
import shutil
from typing import List
import cv2

router = APIRouter()

BASE_DIR = "/tmp/solarsentinel"

def extract_frames(video_path: str, output_dir: str, num_frames: int = 10) -> List[str]:
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"Total frames: {total_frames}")
    if total_frames == 0:
        return []

    step = max(1, total_frames // num_frames)
    extracted_paths = []
    
    for i in range(num_frames):
        frame_id = i * step
        if frame_id >= total_frames:
            break
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_id)
        ret, frame = cap.read()
        if ret:
            frame_path = os.path.join(output_dir, f"frame_{i}.jpg")
            cv2.imwrite(frame_path, frame)
            extracted_paths.append(frame_path)

    cap.release()
    return extracted_paths

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    session_id = str(uuid.uuid4())
    session_dir = os.path.join(BASE_DIR, session_id)
    frames_dir = os.path.join(session_dir, "frames")
    os.makedirs(frames_dir, exist_ok=True)
    
    file_type = file.content_type
    file_path = os.path.join(session_dir, file.filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    frame_paths = []
    
    if "video" in file_type:
        frame_paths = extract_frames(file_path, frames_dir)
    elif "image" in file_type:
        # Just use the image itself as a single frame
        frame_path = os.path.join(frames_dir, "frame_0.jpg")
        shutil.copy(file_path, frame_path)
        frame_paths = [frame_path]
        
    return {
        "session_id": session_id,
        "frame_paths": frame_paths,
        "file_type": file_type
    }
