"""
Imagine360 RunPod Serverless Handler
Converts perspective video to 360° equirectangular panoramic video.

NOTE: Unlike PanoWan and DiT360, Imagine360 requires a VIDEO INPUT
(not just a text prompt). The input video should be a standard
perspective/rectilinear video that will be converted to a 360° panorama.
"""

import runpod
import subprocess
import os
import base64
import tempfile
import urllib.request


def handler(event):
    """
    Handler function for RunPod serverless.

    Input:
        - video_url (str): URL to download the input perspective video
        - video_base64 (str): OR base64-encoded input video
        - prompt (str): Optional text description to guide generation
        - seed (int): Random seed (default: -1 for random)
        - num_inference_steps (int): Denoising steps (default: 50)

    Returns:
        - video_base64 (str): Base64-encoded panoramic MP4 video
        - OR error message
    """
    try:
        job_input = event["input"]
        prompt = job_input.get("prompt", "")
        seed = job_input.get("seed", -1)
        num_steps = job_input.get("num_inference_steps", 50)

        # Get input video
        work_dir = f"/tmp/imagine360_{event['id']}"
        os.makedirs(work_dir, exist_ok=True)
        input_video_path = os.path.join(work_dir, "input.mp4")

        if "video_url" in job_input:
            urllib.request.urlretrieve(job_input["video_url"], input_video_path)
        elif "video_base64" in job_input:
            video_bytes = base64.b64decode(job_input["video_base64"])
            with open(input_video_path, "wb") as f:
                f.write(video_bytes)
        else:
            return {"error": "Must provide either 'video_url' or 'video_base64' input"}

        output_dir = os.path.join(work_dir, "output")
        os.makedirs(output_dir, exist_ok=True)

        # Run Imagine360 inference
        cmd = [
            "python", "inference_dual_p2e.py",
            "--config", "configs/prompt-dual.yaml",
        ]

        env = {
            **os.environ,
            "INPUT_VIDEO": input_video_path,
            "OUTPUT_DIR": output_dir,
            "SEED": str(seed),
            "NUM_STEPS": str(num_steps),
        }
        if prompt:
            env["PROMPT"] = prompt

        result = subprocess.run(
            cmd,
            cwd="/app/Imagine360",
            capture_output=True,
            text=True,
            timeout=1200,  # 20 min timeout (video processing is slow)
            env=env
        )

        if result.returncode != 0:
            return {"error": f"Generation failed: {result.stderr[-500:]}"}

        # Find output video
        output_files = []
        for root, dirs, files in os.walk(output_dir):
            for f in files:
                if f.endswith(('.mp4', '.avi', '.mov', '.gif')):
                    output_files.append(os.path.join(root, f))

        if not output_files:
            return {"error": "No output video found", "stdout": result.stdout[-500:]}

        output_path = output_files[0]

        # Read and encode the video
        with open(output_path, "rb") as f:
            video_bytes = f.read()

        video_base64 = base64.b64encode(video_bytes).decode("utf-8")

        # Cleanup
        import shutil
        shutil.rmtree(work_dir, ignore_errors=True)

        return {
            "video_base64": video_base64,
            "prompt": prompt,
            "format": "mp4",
            "resolution": "512x1024"
        }

    except subprocess.TimeoutExpired:
        return {"error": "Generation timed out after 20 minutes"}
    except Exception as e:
        return {"error": str(e)}


runpod.serverless.start({"handler": handler})
