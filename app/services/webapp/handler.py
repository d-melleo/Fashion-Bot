from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import httpx
from app.config.settings import settings
import os

router = APIRouter()

FAKESTORE_API = f"{settings.FAKE_STORE_API_URL}/products"

# Setup templates
template_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=template_dir)

@router.get("/webapp", response_class=HTMLResponse)
async def home(request: Request):
    async with httpx.AsyncClient() as client:
        resp = await client.get(FAKESTORE_API)
        products = resp.json()
    return templates.TemplateResponse("home.html", {"request": request, "products": products, "title": "Fashion Store"})

@router.get("/webapp/product/{product_id}", response_class=HTMLResponse)
async def product_detail(request: Request, product_id: int):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{FAKESTORE_API}/{product_id}")
        product = resp.json()
    return templates.TemplateResponse("product_detail.html", {"request": request, "product": product, "title": product['title']})

@router.get("/webapp/cart", response_class=HTMLResponse)
async def cart(request: Request):
    return templates.TemplateResponse("cart.html", {"request": request, "title": "Your Cart"})

@router.get("/webapp/checkout", response_class=HTMLResponse)
async def checkout(request: Request):
    return templates.TemplateResponse("checkout.html", {"request": request, "title": "Checkout Complete"})