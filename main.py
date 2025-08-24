from fastapi import FastAPI, File, UploadFile, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from transformers import AutoProcessor, AutoModelForVision2Seq
import torch
from PIL import Image
import io
import base64
import uvicorn

app = FastAPI(title="Image Caption Web UI")

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

model_path = "blip-image-captioning-large"
processor = AutoProcessor.from_pretrained(model_path, use_fast=True)
model = AutoModelForVision2Seq.from_pretrained(model_path)
device = "cuda" if torch.cuda.is_available() else "cpu"
model.to(device)


def generate_caption_from_pil(image: Image.Image) -> str:
    inputs = processor(images=image, return_tensors="pt").to(device)
    pixel_values = inputs.pixel_values
    generated_ids = model.generate(pixel_values=pixel_values, max_length=50)
    caption = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
    return caption


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        "index.html", {"request": request, "caption": "", "image_data": ""}
    )


@app.post("/caption", response_class=HTMLResponse)
async def caption(request: Request, file: UploadFile = File(...)):
    try:
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        caption_text = generate_caption_from_pil(image)

        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        img_data = f"data:image/png;base64,{img_str}"

        return templates.TemplateResponse(
            "index.html",
            {"request": request, "caption": caption_text, "image_data": img_data},
        )
    except Exception as e:
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "caption": f"Error: {str(e)}", "image_data": ""},
        )


if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)
