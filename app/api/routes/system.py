import asyncio
import sys
import logging
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/v1/system", tags=["system"])
logger = logging.getLogger(__name__)

@router.post("/update-core")
async def update_core_packages():
    """Update core packages like yt-dlp."""
    try:
        # Run pip install -U yt-dlp
        process = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "pip", "install", "-U", "yt-dlp",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        output = stdout.decode('utf-8')
        err_output = stderr.decode('utf-8')
        
        if process.returncode != 0:
            logger.error(f"Failed to update yt-dlp. Exit code: {process.returncode}, Stderr: {err_output}")
            raise HTTPException(status_code=500, detail=f"Update failed:\n{err_output}")
            
        logger.info(f"Successfully updated core packages: {output}")
        return {"status": "success", "message": "Core packages successfully updated.", "details": output}
        
    except Exception as e:
        logger.error(f"Error updating packages: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/open-logs")
async def open_logs():
    """Open the app.log file in the system's default text editor."""
    import os
    import sys
    import subprocess
    
    log_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "logs", "app.log"))
    
    try:
        if sys.platform == "win32":
            os.startfile(log_file)
        elif sys.platform == "darwin":
            subprocess.run(["open", log_file])
        else:
            subprocess.run(["xdg-open", log_file])
        return {"status": "success", "opened": log_file}
    except Exception as e:
        logger.error(f"Failed to open logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))
