from functools import lru_cache
from typing import Dict, Any

from fastapi import FastAPI, Request, Form, status, BackgroundTasks
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr
import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

class EmailConfig(BaseModel):
    sender_email: str = os.getenv("HOST_EMAIL")
    receiver_email: str = os.getenv("HOST_EMAIL")
    password: str = os.getenv("HOST_PASSWORD")
    smtp_server: str = 'mail1.netim.hosting'  # Update to Netim SMTP server
    port: int = 465  # SSL port for Netim

@lru_cache()
def get_email_config() -> EmailConfig:
    return EmailConfig()

def create_html_content(data: Dict[str, Any]) -> str:
    return f"""
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background-color: #2c5282;
                color: white;
                padding: 20px;
                border-radius: 5px 5px 0 0;
                margin-bottom: 20px;
            }}
            .content {{
                background-color: #f8f9fa;
                padding: 20px;
                border-radius: 0 0 5px 5px;
                border: 1px solid #e9ecef;
            }}
            .field {{
                margin-bottom: 15px;
                border-bottom: 1px solid #e9ecef;
                padding-bottom: 10px;
            }}
            .label {{
                font-weight: bold;
                color: #2c5282;
            }}
            .value {{
                color: #4a5568;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h2>Contact Form Submission</h2>
        </div>
        <div class="content">
            {''.join(f'<div class="field"><span class="label">{k.title()}:</span> <span class="value">{v}</span></div>' for k, v in data.items())}
        </div>
    </body>
    </html>
    """

def send_email(config: EmailConfig, subject: str, content: str):
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"NovoAgro LLP <{config.sender_email}>"
    message["To"] = config.receiver_email
    message.set_content(content, subtype='html')

    try:
        with smtplib.SMTP_SSL(config.smtp_server, config.port) as server:
            server.login(config.sender_email, config.password)
            server.send_message(message)
    except smtplib.SMTPAuthenticationError as e:
        print(f"SMTP Authentication Error: {e.smtp_code} - {e.smtp_error.decode()}")
        raise
    except Exception as e:
        print(f"Error sending email: {e}")
        raise

@app.get("/")
@app.get("/about")
@app.get("/contact")
@app.get("/services")
@app.get("/sustainability")  # Add this line
async def render_page(request: Request):
    template = request.url.path.strip("/") or "index"
    return templates.TemplateResponse(f"{template}.html", {"request": request})

@app.post("/sendmail")
async def contact(
    background_tasks: BackgroundTasks,
    name: str = Form(...),
    email: EmailStr = Form(...),
    phone: str = Form(...),
    subject: str = Form(...),
    message: str = Form(...)
):
    config = get_email_config()
    content = create_html_content({
        "name": name,
        "email": email,
        "phone": phone,
        "subject": subject,
        "message": message
    })
    background_tasks.add_task(send_email, config, f"Contact Form: {subject}", content)
    return RedirectResponse(url="/contact", status_code=status.HTTP_302_FOUND)

@app.middleware("http")
async def add_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.update({
        "X-XSS-Protection": "1; mode=block",
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "public, max-age=1200" if response.status_code == 200 else "no-store"
    })
    return response

@app.middleware("http")
async def fix_mime_type(request: Request, call_next):
    response = await call_next(request)
    content_types = {".ttf": "font/ttf", ".woff": "font/woff", ".woff2": "font/woff2"}
    ext = os.path.splitext(request.url.path)[1]
    if ext in content_types:
        response.headers["Content-Type"] = content_types[ext]
    return response