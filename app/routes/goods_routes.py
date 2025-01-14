from bson import ObjectId
from fastapi import APIRouter, Request, Form, UploadFile, HTTPException
from fastapi.responses import RedirectResponse

from app.config.templates import templates
from app.models.Goods import Goods
from app.service.GoodsService import GoodsService

router = APIRouter()

@router.get("")
async def list_goods(request: Request):
    try:
        goods = await GoodsService.all_goods()
        return templates.TemplateResponse("goods/goods.html", {"request": request, "goods": goods})
    except HTTPException as e:
        return templates.TemplateResponse(
            "post.html", {"request": request, "message": e.detail}
        )

@router.get("/detail/{goods_id}")
async def goods_detail(request: Request, goods_id: str):
    """상품 상세 페이지"""
    try:
        if not ObjectId.is_valid(goods_id):
            raise HTTPException(status_code=400, detail="유효하지 않은 상품 ID입니다.")
        goods = await GoodsService.get_goods_by_id(goods_id)  # 새로운 서비스 메서드 활용
        if not goods:
            return RedirectResponse("/goods", status_code=302)
        return templates.TemplateResponse("goods/goods_detail.html", {"request": request, "goods": goods})
    except HTTPException as e:
        return {"message": e.detail}


@router.get("/add")
async def add_goods_form(request: Request):
    """상품 등록 페이지"""
    return templates.TemplateResponse("goods/goods_add.html", {"request": request})


@router.post("/add")
async def add_goods(
        name: str = Form(...),
        description: str = Form(...),
        price: float = Form(...),
        stock: int = Form(...),
        discount_rate: float = Form(...),
        category: str = Form(None),
        sku: str = Form(None),
        image: UploadFile = None
):
    """상품 등록 요청 처리"""
    try:
        # 이미지 업로드 처리
        image_url = await GoodsService.save_image(image) if image else None

        # Goods 객체 생성 및 등록
        goods = Goods(
            name=name,
            description=description,
            price=price,
            stock=stock,
            discount_rate=discount_rate,
            category=category,
            sku=sku,
            image_url=f"/static/images/goods/{image_url}" if image_url else None
        )
        result = await GoodsService.add_goods(goods)
        if result:
            return RedirectResponse("/goods", status_code=302)
        return {"message": "상품 등록 실패"}
    except HTTPException as e:
        return {"message": e.detail}


@router.post("/purchase/{goods_id}")
async def purchase_goods(goods_id: str, quantity: int = Form(...), user_id: str = Form(...)):
    """상품 구매 요청 처리"""
    try:
        success = await GoodsService.purchase_goods(user_id, goods_id, quantity)
        if success:
            return RedirectResponse("/goods", status_code=302)
        return {"message": "구매 실패: 재고 부족 또는 잘못된 요청"}
    except HTTPException as e:
        return {"message": e.detail}
